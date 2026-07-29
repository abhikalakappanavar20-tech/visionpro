"""
Views for VeriVision
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Count, Q, Avg
from django.core.paginator import Paginator
from datetime import timedelta
import os
import json
import logging

logger = logging.getLogger(__name__)

from .models import MediaScan, ReportedContent, ForensicAnalysisResult, UserSecurityProfile
from .forms import (
    MediaUploadForm,
    ReportForm,
    URLScanForm,
    CustomUserCreationForm,
    UserProfileForm,
    UserPasswordChangeForm,
    EmailOrUsernameAuthenticationForm,
    PasswordResetUsernameForm,
    PasswordResetSecurityForm
)
from .services import DeepfakeAnalyzer, ThreatLevelCalculator


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def home(request):
    """Landing page"""
    recent_scans = MediaScan.objects.order_by('-created_at')[:5]

    context = {
        'recent_scans': recent_scans,
        'total_scans': MediaScan.objects.count(),
    }
    return render(request, 'core/home.html', context)


@login_required
def webcam(request):
    """Webcam capture page"""
    context = {
        'total_scans': MediaScan.objects.count(),
    }
    return render(request, 'core/webcam.html', context)


@login_required
def scan(request):
    """Main scanning page - requires authentication"""
    if request.method == 'POST':
        form = MediaUploadForm(request.POST, request.FILES)

        if form.is_valid():
            # Initialize analyzer
            analyzer = DeepfakeAnalyzer()

            # Determine input type
            file = form.cleaned_data.get('file')
            url = form.cleaned_data.get('url')

            try:
                if file:
                    # Determine file type
                    ext = os.path.splitext(file.name)[1].lower()
                    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                        file_type = 'image'
                    elif ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
                        file_type = 'video'
                    elif ext in ['.wav', '.mp3', '.m4a', '.flac', '.mpeg', '.mpg', '.ogg', '.aac', '.opus']:
                        file_type = 'audio'
                    else:
                        file_type = 'image'

                    # Detect source (webcam, upload, or url). Read from POST because the form does not include a source field.
                    source = request.POST.get('source', 'upload')
                    if 'webcam-capture' in file.name or 'webcam-recording' in file.name:
                        source = 'webcam'

                    # Use ForensicPipeline for actual analysis
                    from .analyzers import ForensicPipeline
                    import tempfile

                    # Save uploaded file to temp location for analysis
                    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
                        for chunk in file.chunks():
                            tmp_file.write(chunk)
                        tmp_path = tmp_file.name

                    try:
                        # Run analysis using ForensicPipeline with timeout handling
                        pipeline = ForensicPipeline()

                        if file_type == 'image':
                            result = pipeline.analyze_image(tmp_path, source=source)
                        elif file_type == 'video':
                            result = pipeline.analyze_video(tmp_path, source=source)
                        elif file_type == 'audio':
                            result = pipeline.analyze_audio(tmp_path, source=source)
                        else:
                            # Fallback for unknown types
                            result = pipeline.analyze_image(tmp_path, source=source)

                    except Exception as analysis_error:
                        # Handle analysis errors gracefully
                        logger.error(f"Analysis error: {str(analysis_error)}")

                        # Create a fallback result for display
                        result = {
                            'scan_result': 'suspicious',  # Default to suspicious on error instead of fake
                            'confidence_score': 50.0,
                            'trust_score': 50.0,
                            'forensic_details': {
                                'error': str(analysis_error),
                                'message': 'Analysis encountered an error. Returning cautious suspicious result.'
                            },
                            'heatmap_data': {'hotspots': [], 'total_hotspots': 0, 'intensity_level': 'unknown'},
                            'processing_time': 0,
                            'manipulation_indicators': ['Analysis error occurred']
                        }

                        messages.warning(request, f'Analysis completed with warnings: {str(analysis_error)}')

                    finally:
                        # Clean up temp file
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)

                    # Create database record
                    scan = MediaScan(
                        file_type=file_type,
                        original_filename=file.name,
                        scan_result=result['scan_result'],
                        confidence_score=result['confidence_score'],
                        trust_score=result['trust_score'],
                        forensic_match=result.get('forensic_match', False),
                        heatmap_data=result.get('heatmap_data', {}),
                        analysis_details=result.get('forensic_details', result.get('analysis_details', {})),
                        processing_time=result.get('processing_time', 0),
                        ip_address=get_client_ip(request),
                        user=request.user if request.user.is_authenticated else None
                    )
                    # Try to save file, fallback to filename-only if filesystem is read-only
                    try:
                        scan.file = file
                        scan.save()
                    except (OSError, PermissionError):
                        scan.file = None
                        scan.save()

                    # Save detailed forensic analysis results if available
                    # Only save detailed results for images (video/audio have their own structure)
                    if file_type == 'image' and (result.get('manipulation_indicators') or result.get('source_detection')):
                        try:
                            from .analyzers import ForensicPipeline
                            pipeline = ForensicPipeline()
                            pipeline.save_forensic_results(scan, result)
                        except Exception as forensic_error:
                            print(f"Warning: Could not save detailed forensic results: {forensic_error}")

                    # Add legacy forensic data if present
                    if result.get('forensic_data'):
                        scan.forensic_first_seen = timezone.now().strftime('%Y-%m-%d')
                        scan.forensic_usage_count = result['forensic_data']['usage_count']
                        scan.forensic_context = result['forensic_data']['context']
                        scan.save()

                elif url:
                    # Analyze URL
                    result = analyzer.analyze_url(url)

                    # Create database record
                    scan = MediaScan.objects.create(
                        file_type='url',
                        url=url,
                        scan_result=result['scan_result'],
                        confidence_score=result['confidence_score'],
                        trust_score=result['trust_score'],
                        forensic_match=result['forensic_match'],
                        heatmap_data=result['heatmap_data'],
                        analysis_details=result['analysis_details'],
                        processing_time=result['processing_time'],
                        ip_address=get_client_ip(request),
                        user=request.user if request.user.is_authenticated else None
                    )

                    # Add forensic data if present
                    if result.get('forensic_data'):
                        scan.forensic_first_seen = timezone.now().strftime('%Y-%m-%d')
                        scan.forensic_usage_count = result['forensic_data']['usage_count']
                        scan.forensic_context = result['forensic_data']['context']
                        scan.save()

                messages.success(request, 'Analysis completed successfully!')
                return redirect('result', scan_id=scan.id)

            except Exception as e:
                messages.error(request, f'Analysis failed: {str(e)}')

        else:
            messages.error(request, 'Invalid form submission. Please check your input.')

    else:
        form = MediaUploadForm()

    context = {
        'form': form,
        'url_form': URLScanForm(),
    }
    return render(request, 'core/scan.html', context)


@login_required
def scan_url(request):
    """Handle quick URL scan from landing page - requires authentication"""
    if request.method == 'POST':
        form = URLScanForm(request.POST)

        if form.is_valid():
            url = form.cleaned_data['url']

            # Initialize analyzer
            analyzer = DeepfakeAnalyzer()

            try:
                # Run analysis
                result = analyzer.analyze_url(url)

                # Create database record
                scan = MediaScan.objects.create(
                    file_type='url',
                    url=url,
                    scan_result=result['scan_result'],
                    confidence_score=result['confidence_score'],
                    trust_score=result['trust_score'],
                    forensic_match=result['forensic_match'],
                    heatmap_data=result['heatmap_data'],
                    analysis_details=result['analysis_details'],
                    processing_time=result['processing_time'],
                    ip_address=get_client_ip(request),
                    user=request.user if request.user.is_authenticated else None
                )

                # Add forensic data if present
                if result.get('forensic_data'):
                    scan.forensic_first_seen = timezone.now().strftime('%Y-%m-%d')
                    scan.forensic_usage_count = result['forensic_data']['usage_count']
                    scan.forensic_context = result['forensic_data']['context']
                    scan.save()

                messages.success(request, 'URL analysis completed!')
                return redirect('result', scan_id=scan.id)

            except Exception as e:
                messages.error(request, f'Analysis failed: {str(e)}')

    return redirect('scan')


@login_required
def result(request, scan_id):
    """Display scan results with XAI visualization - requires authentication"""
    scan = get_object_or_404(MediaScan, id=scan_id)

    # Calculate threat level
    threat_level = ThreatLevelCalculator.calculate(
        scan.scan_result,
        scan.confidence_score,
        scan.trust_score,
        scan.forensic_match
    )

    # Prepare heatmap data for JavaScript
    heatmap_json = json.dumps(scan.heatmap_data)

    # Get forensic analysis if available
    forensic_analysis = None
    try:
        forensic_analysis = scan.forensic_analysis
    except:
        pass  # No forensic analysis available (old scans or different type)

    # Check if this has been reported
    has_report = ReportedContent.objects.filter(
        Q(scan=scan) | Q(url_or_file_name=scan.url or scan.original_filename)
    ).exists()

    context = {
        'scan': scan,
        'heatmap_data': heatmap_json,
        'threat_level': threat_level,
        'has_report': has_report,
        'forensic_analysis': forensic_analysis,
    }
    return render(request, 'core/result.html', context)


@login_required
def dashboard(request):
    """Analytics dashboard - requires authentication"""
    # Get statistics
    total_scans = MediaScan.objects.count()

    # Last 30 days stats
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_scans = MediaScan.objects.filter(created_at__gte=thirty_days_ago)

    # Result distribution
    result_counts = dict(
        MediaScan.objects.values('scan_result').annotate(
            count=Count('id')
        ).values_list('scan_result', 'count')
    )

    # File type distribution
    type_counts = dict(
        MediaScan.objects.values('file_type').annotate(
            count=Count('id')
        ).values_list('file_type', 'count')
    )

    # Time series data (last 30 days)
    time_series = []
    for i in range(30):
        date = timezone.now() - timedelta(days=29-i)
        date_str = date.strftime('%Y-%m-%d')
        count = MediaScan.objects.filter(
            created_at__date=date.date()
        ).count()
        time_series.append({'date': date_str, 'count': count})

    # Average scores
    avg_confidence = MediaScan.objects.aggregate(
        avg=Avg('confidence_score')
    )['avg'] or 0

    avg_trust = MediaScan.objects.aggregate(
        avg=Avg('trust_score')
    )['avg'] or 0

    # Forensic match rate
    forensic_rate = (MediaScan.objects.filter(forensic_match=True).count() / total_scans * 100) if total_scans > 0 else 0

    # Pending reports
    pending_reports = ReportedContent.objects.filter(status='pending').count()

    context = {
        'total_scans': total_scans,
        'recent_scans': recent_scans.count(),
        'result_counts': result_counts,
        'type_counts': type_counts,
        'time_series': time_series,
        'avg_confidence': round(avg_confidence, 2),
        'avg_trust': round(avg_trust, 2),
        'forensic_rate': round(forensic_rate, 2),
        'pending_reports': pending_reports,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def report_content(request, scan_id=None):
    """Report suspicious content - requires authentication"""
    scan = None
    if scan_id:
        scan = get_object_or_404(MediaScan, id=scan_id)

    if request.method == 'POST':
        form = ReportForm(request.POST)

        if form.is_valid():
            report = form.save(commit=False)

            if scan:
                report.scan = scan

            # Auto-detect file type if not provided
            if not report.file_type:
                if scan:
                    report.file_type = scan.file_type
                else:
                    report.file_type = 'image'

            report.save()
            messages.success(request, 'Thank you for your report! It will be reviewed shortly.')
            return redirect('home')

    else:
        initial_data = {}
        if scan:
            initial_data['url_or_file_name'] = scan.url or scan.original_filename or f"Scan #{scan.id}"
            initial_data['file_type'] = scan.file_type

        form = ReportForm(initial=initial_data)

    context = {
        'form': form,
        'scan': scan,
    }
    return render(request, 'core/report.html', context)


@login_required
def history(request):
    """View scan history - requires authentication"""
    # Admins can view all scans or filter by user via ?user_id=<id>
    if request.user.is_staff:
        scans = MediaScan.objects.all().order_by('-created_at')
        user_id = request.GET.get('user_id')
        if user_id:
            scans = scans.filter(user__id=user_id)
    else:
        # Regular users only see their own scans
        scans = MediaScan.objects.filter(user=request.user).order_by('-created_at')

    # Filter by result if provided
    result_filter = request.GET.get('result')
    if result_filter:
        scans = scans.filter(scan_result=result_filter)

    # Filter by type if provided
    type_filter = request.GET.get('type')
    if type_filter:
        scans = scans.filter(file_type=type_filter)

    # Pagination
    paginator = Paginator(scans, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'result_filter': result_filter,
        'type_filter': type_filter,
    }
    return render(request, 'core/history.html', context)

@login_required
def delete_scan(request, scan_id):

    scan = get_object_or_404(MediaScan, id=scan_id)

    # Security check
    if scan.user != request.user:
        messages.error(request, "You are not allowed to delete this scan.")
        return redirect('dashboard')

    # Delete uploaded file
    if scan.file:
        if os.path.isfile(scan.file.path):
            os.remove(scan.file.path)

    # Delete database record
    scan.delete()

    messages.success(request, "Scan deleted successfully.")

    return redirect('dashboard')


def api_stats(request):
    """API endpoint for dashboard stats"""
    data = {
        'total_scans': MediaScan.objects.count(),
        'fake_count': MediaScan.objects.filter(scan_result='fake').count(),
        'real_count': MediaScan.objects.filter(scan_result='real').count(),
        'manipulated_count': MediaScan.objects.filter(scan_result='manipulated').count(),
        'suspicious_count': MediaScan.objects.filter(scan_result='suspicious').count(),
    }

    return JsonResponse(data)


# ========== Authentication Views ==========

def register(request):
    """User registration page"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                username = form.cleaned_data.get('username')
                password = form.cleaned_data.get('password1')
                user = authenticate(username=username, password=password)
                login(request, user)
                messages.success(request, f'Welcome to VeriVision, {username}!')
                return redirect('home')
            except Exception as e:
                messages.error(request, f'Error creating account: {str(e)}')
        else:
            # Form is invalid - errors will be displayed in template
            pass
    else:
        form = CustomUserCreationForm()

    return render(request, 'core/register.html', {'form': form})


def user_login(request):
    """User login page"""
    if request.method == 'POST':
        form = EmailOrUsernameAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                # Honor ?next= when present; otherwise staff land in the admin
                # panel and regular users on the home page.
                next_page = request.POST.get('next') or request.GET.get('next')
                if next_page:
                    return redirect(next_page)
                if user.is_staff:
                    return redirect('admin_panel_dashboard')
                return redirect('home')
            else:
                messages.error(request, 'Invalid username or password.')
        # Form is invalid - fall through to render with errors
        # Don't add duplicate error message here since form will show field errors
    else:
        form = EmailOrUsernameAuthenticationForm()

    return render(request, 'core/login.html', {'form': form})


def password_reset_request(request):
    """Start password recovery by asking for username."""
    if request.method == 'POST':
        form = PasswordResetUsernameForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            try:
                user = User.objects.get(username__iexact=username)
                if not hasattr(user, 'security_profile'):
                    messages.error(request, 'No recovery question is set for this account.')
                else:
                    return redirect('password_reset_question', username=user.username)
            except User.DoesNotExist:
                messages.error(request, 'No account found with that username.')
    else:
        form = PasswordResetUsernameForm()

    return render(request, 'core/password_reset_username.html', {'form': form})


def password_reset_question(request, username):
    """Verify the user's recovery answer and allow password reset."""
    user = get_object_or_404(User, username__iexact=username)
    profile = getattr(user, 'security_profile', None)
    if profile is None:
        messages.error(request, 'This account does not have a recovery question configured.')
        return redirect('password_reset')

    if request.method == 'POST':
        form = PasswordResetSecurityForm(user=user, data=request.POST)
        if form.is_valid():
            answer = form.cleaned_data['security_answer']
            if not profile.check_security_answer(answer):
                form.add_error('security_answer', 'The security answer does not match.')
            else:
                new_password = form.cleaned_data['new_password1']
                user.set_password(new_password)
                user.save()
                messages.success(request, 'Your password has been reset successfully. Please log in with the new password.')
                return redirect('login')
    else:
        form = PasswordResetSecurityForm(user=user)

    context = {
        'form': form,
        'security_question': profile.get_security_question_display(),
        'username': user.username,
    }
    return render(request, 'core/password_reset_security.html', context)


def password_reset_complete(request):
    """Confirmation page after password reset is complete."""
    return render(request, 'core/password_reset_complete.html')


def user_logout(request):
    """User logout"""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('home')


@login_required
def profile(request):
    """User profile page"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)

    # Get user's scan history
    user_scans = MediaScan.objects.filter(user=request.user).order_by('-created_at')[:10]

    context = {
        'form': form,
        'user_scans': user_scans,
        'total_scans': user_scans.count()
    }
    return render(request, 'core/profile.html', context)


@login_required
def change_password(request):
    """Allow a logged in user to securely change their password."""
    if request.method == 'POST':
        form = UserPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been updated successfully.')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the highlighted errors and try again.')
    else:
        form = UserPasswordChangeForm(user=request.user)

    return render(request, 'core/change_password.html', {'form': form})


# ========== Admin Panel Views ==========
# Uses the same login as regular users. Access is gated by is_staff.
# Non-staff users hitting these URLs get redirected to login then bounced
# back here (where they'll see a 403 if they're authenticated-but-not-staff).

def _staff_required(view_func):
    """Decorator: must be logged in AND have is_staff=True."""
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/login/?next={request.path}")
        if not request.user.is_staff:
            return render(request, 'core/admin_panel/forbidden.html', status=403)
        return view_func(request, *args, **kwargs)
    return wrapped


@_staff_required
def admin_panel_dashboard(request):
    """Admin overview: high-level system stats + analytics charts."""
    total_users = User.objects.count()
    staff_users = User.objects.filter(is_staff=True).count()
    active_users_30d = User.objects.filter(last_login__gte=timezone.now() - timedelta(days=30)).count()

    total_scans = MediaScan.objects.count()
    fake_scans = MediaScan.objects.filter(scan_result='fake').count()
    real_scans = MediaScan.objects.filter(scan_result='real').count()
    suspicious_scans = MediaScan.objects.filter(scan_result='suspicious').count()

    pending_reports = ReportedContent.objects.filter(status='pending').count()
    total_reports = ReportedContent.objects.count()

    # Analytics: averages
    avg_confidence = MediaScan.objects.aggregate(avg=Avg('confidence_score'))['avg'] or 0
    avg_trust = MediaScan.objects.aggregate(avg=Avg('trust_score'))['avg'] or 0
    avg_processing = MediaScan.objects.aggregate(avg=Avg('processing_time'))['avg'] or 0

    # Analytics: time series — scans per day for the last 30 days
    time_series_labels = []
    time_series_counts = []
    time_series_fake = []
    for i in range(30):
        d = (timezone.now() - timedelta(days=29 - i)).date()
        time_series_labels.append(d.strftime('%b %d'))
        time_series_counts.append(MediaScan.objects.filter(created_at__date=d).count())
        time_series_fake.append(MediaScan.objects.filter(created_at__date=d, scan_result='fake').count())

    # Analytics: file-type distribution
    type_counts = dict(
        MediaScan.objects.values('file_type').annotate(c=Count('id')).values_list('file_type', 'c')
    )
    file_type_labels = ['Image', 'Video', 'Audio', 'URL']
    file_type_values = [
        type_counts.get('image', 0),
        type_counts.get('video', 0),
        type_counts.get('audio', 0),
        type_counts.get('url', 0),
    ]

    recent_scans = MediaScan.objects.order_by('-created_at')[:8]
    recent_reports = ReportedContent.objects.order_by('-created_at')[:5]

    context = {
        'active_section': 'dashboard',
        'total_users': total_users,
        'staff_users': staff_users,
        'active_users_30d': active_users_30d,
        'total_scans': total_scans,
        'fake_scans': fake_scans,
        'real_scans': real_scans,
        'suspicious_scans': suspicious_scans,
        'pending_reports': pending_reports,
        'total_reports': total_reports,
        'avg_confidence': round(avg_confidence, 2),
        'avg_trust': round(avg_trust, 2),
        'avg_processing': round(avg_processing, 2),
        # JSON-serialized for safe embedding in <script>
        'chart_time_labels': json.dumps(time_series_labels),
        'chart_time_total': json.dumps(time_series_counts),
        'chart_time_fake': json.dumps(time_series_fake),
        'chart_result_values': json.dumps([real_scans, suspicious_scans, fake_scans]),
        'chart_type_labels': json.dumps(file_type_labels),
        'chart_type_values': json.dumps(file_type_values),
        'recent_scans': recent_scans,
        'recent_reports': recent_reports,
    }
    return render(request, 'core/admin_panel/dashboard.html', context)


@_staff_required
def admin_panel_users(request):
    """List all users with management actions."""
    q = request.GET.get('q', '').strip()
    users = User.objects.all().order_by('-date_joined')
    if q:
        users = users.filter(Q(username__icontains=q) | Q(email__icontains=q))

    paginator = Paginator(users, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'active_section': 'users',
        'page_obj': page_obj,
        'q': q,
    }
    return render(request, 'core/admin_panel/users.html', context)


@_staff_required
def admin_panel_user_detail(request, user_id):
    """View a single user's profile and their scan history."""
    target = get_object_or_404(User, id=user_id)
    user_scans = target.scans.order_by('-created_at')[:50]

    context = {
        'active_section': 'users',
        'target_user': target,
        'user_scans': user_scans,
    }
    return render(request, 'core/admin_panel/user_detail.html', context)


@_staff_required
def admin_panel_user_action(request, user_id):
    """Toggle staff/active or delete a user. POST-only."""
    if request.method != 'POST':
        return redirect('admin_panel_users')

    target = get_object_or_404(User, id=user_id)
    action = request.POST.get('action')

    if target.id == request.user.id and action in ('toggle_staff', 'toggle_active', 'delete'):
        messages.error(request, "You cannot modify your own admin account from here.")
        return redirect('admin_panel_users')

    if action == 'toggle_staff':
        target.is_staff = not target.is_staff
        target.save()
        messages.success(request, f"{target.username} staff status: {'ON' if target.is_staff else 'OFF'}.")
    elif action == 'toggle_active':
        target.is_active = not target.is_active
        target.save()
        messages.success(request, f"{target.username} is now {'active' if target.is_active else 'disabled'}.")
    elif action == 'delete':
        username = target.username
        target.delete()
        messages.success(request, f"User '{username}' deleted.")
        return redirect('admin_panel_users')
    else:
        messages.error(request, "Unknown action.")

    return redirect('admin_panel_user_detail', user_id=target.id)


@_staff_required
def admin_panel_scans(request):
    """View all scans across all users with filtering."""
    scans = MediaScan.objects.all().order_by('-created_at')

    result_filter = request.GET.get('result', '').strip()
    type_filter = request.GET.get('type', '').strip()
    q = request.GET.get('q', '').strip()

    if result_filter:
        scans = scans.filter(scan_result=result_filter)
    if type_filter:
        scans = scans.filter(file_type=type_filter)
    if q:
        scans = scans.filter(Q(original_filename__icontains=q) | Q(url__icontains=q))

    paginator = Paginator(scans, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'active_section': 'scans',
        'page_obj': page_obj,
        'result_filter': result_filter,
        'type_filter': type_filter,
        'q': q,
    }
    return render(request, 'core/admin_panel/scans.html', context)


@_staff_required
def admin_panel_scan_delete(request, scan_id):
    """Delete a scan record. POST-only."""
    if request.method != 'POST':
        return redirect('admin_panel_scans')
    scan = get_object_or_404(MediaScan, id=scan_id)
    scan.delete()
    messages.success(request, f"Scan #{scan_id} deleted.")
    return redirect('admin_panel_scans')


@_staff_required
def admin_panel_reports(request):
    """Manage user-submitted reports."""
    reports = ReportedContent.objects.all().order_by('-created_at')

    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        reports = reports.filter(status=status_filter)

    paginator = Paginator(reports, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'active_section': 'reports',
        'page_obj': page_obj,
        'status_filter': status_filter,
        'status_choices': ReportedContent.STATUS_CHOICES,
    }
    return render(request, 'core/admin_panel/reports.html', context)


@_staff_required
def admin_panel_report_action(request, report_id):
    """Update the status of a report. POST-only."""
    if request.method != 'POST':
        return redirect('admin_panel_reports')
    report = get_object_or_404(ReportedContent, id=report_id)
    new_status = request.POST.get('status')
    notes = request.POST.get('moderator_notes', '').strip()

    valid_statuses = {choice[0] for choice in ReportedContent.STATUS_CHOICES}
    if new_status in valid_statuses:
        report.status = new_status
        if notes:
            report.moderator_notes = notes
        report.save()
        messages.success(request, f"Report #{report.id} updated to '{new_status}'.")
    else:
        messages.error(request, "Invalid status.")
    return redirect('admin_panel_reports')


