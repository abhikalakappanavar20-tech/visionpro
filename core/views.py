"""
Views for VeriVision
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from django.db.models import Count, Q, Avg
from django.core.paginator import Paginator
from datetime import timedelta
import os
import json

from .models import MediaScan, ReportedContent, ForensicAnalysisResult
from .forms import MediaUploadForm, ReportForm, URLScanForm, CustomUserCreationForm, UserProfileForm
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
                    elif ext in ['.wav', '.mp3', '.m4a', '.flac']:
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
                    scan = MediaScan.objects.create(
                        file=file,
                        file_type=file_type,
                        original_filename=file.name,
                        scan_result=result['scan_result'],
                        confidence_score=result['confidence_score'],
                        trust_score=result['trust_score'],
                        forensic_match=result.get('forensic_match', False),
                        heatmap_data=result.get('heatmap_data', {}),
                        analysis_details=result.get('forensic_details', result.get('analysis_details', {})),
                        processing_time=result.get('processing_time', 0),
                        ip_address=get_client_ip(request)
                    )

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
                        ip_address=get_client_ip(request)
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
                    ip_address=get_client_ip(request)
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
    scans = MediaScan.objects.all().order_by('-created_at')

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


def loading_scan(request):
    """Template for showing loading animation during scan"""
    return render(request, 'core/loading_scan.html')


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
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                # Redirect to next page if specified, otherwise home
                next_page = request.POST.get('next') or request.GET.get('next') or 'home'
                return redirect(next_page)
            else:
                messages.error(request, 'Invalid username or password.')
        # Form is invalid - fall through to render with errors
        # Don't add duplicate error message here since form will show field errors
    else:
        form = AuthenticationForm()

    return render(request, 'core/login.html', {'form': form})


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
    user_scans = MediaScan.objects.filter(
        ip_address=get_client_ip(request)
    ).order_by('-created_at')[:10]

    context = {
        'form': form,
        'user_scans': user_scans,
        'total_scans': user_scans.count()
    }
    return render(request, 'core/profile.html', context)
