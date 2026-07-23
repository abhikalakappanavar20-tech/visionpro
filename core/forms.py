"""
Forms for VeriVision
"""
from django import forms
from django.core.validators import URLValidator
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.contrib.auth import password_validation
from .models import MediaScan, ReportedContent, UserSecurityProfile


class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your username or email',
            'autofocus': True
        }),
        label='Username or Email'
    )

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        UserModel = get_user_model()

        if username and password and '@' in username:
            try:
                user = UserModel.objects.get(email__iexact=username)
                self.cleaned_data['username'] = user.get_username()
            except UserModel.DoesNotExist:
                pass

        return super().clean()


class MediaUploadForm(forms.ModelForm):
    """Form for uploading media files"""

    ACCEPTED_FILE_TYPES = [
        '.jpg', '.jpeg', '.png', '.gif', '.webp',  # Images
        '.mp4', '.avi', '.mov', '.mkv', '.webm',  # Videos (webcam uses .webm)
        '.wav', '.mp3', '.m4a', '.flac', '.mpeg', '.mpg', '.ogg', '.aac', '.opus'  # Audio
    ]

    file = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'file-input',
            'accept': ','.join(ACCEPTED_FILE_TYPES)
        }),
        help_text="Upload image, video, or audio file"
    )

    url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-input',
            'placeholder': 'https://twitter.com/user/status/...'
        }),
        help_text="Or enter a social media URL"
    )

    class Meta:
        model = MediaScan
        fields = ['file', 'url']

    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get('file')
        url = cleaned_data.get('url')

        if not file and not url:
            raise forms.ValidationError(
                "Please either upload a file or provide a URL."
            )

        if file and url:
            raise forms.ValidationError(
                "Please provide either a file or a URL, not both."
            )

        if file:
            # Check file extension
            import os
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in self.ACCEPTED_FILE_TYPES:
                raise forms.ValidationError(
                    f"Invalid file type. Accepted types: {', '.join(self.ACCEPTED_FILE_TYPES)}"
                )

            # Check file size (5GB max)
            if file.size > 5 *1024 * 1024 * 1024:
                raise forms.ValidationError(
                    "File size exceeds 5GB limit."
                )

        return cleaned_data


class ReportForm(forms.ModelForm):
    """Form for reporting suspicious content"""

    reporter_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'your@email.com'
        })
    )

    additional_info = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 4,
            'placeholder': 'Any additional information...'
        })
    )

    class Meta:
        model = ReportedContent
        fields = ['url_or_file_name', 'file_type', 'reason', 'reporter_email', 'additional_info']
        widgets = {
            'url_or_file_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'URL or filename of the content'
            }),
            'file_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 5,
                'placeholder': 'Why are you reporting this content?'
            })
        }


class URLScanForm(forms.Form):
    """Quick form for URL scanning"""

    url = forms.URLField(
        widget=forms.URLInput(attrs={
            'class': 'form-input',
            'placeholder': 'https://twitter.com/user/status/...',
            'id': 'url-input'
        }),
        help_text="Enter social media post URL to analyze"
    )


class CustomUserCreationForm(UserCreationForm):
    """Custom user registration form"""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'your@email.com',
            'autocomplete': 'email'
        }),
        help_text='Required. Enter a valid email address.'
    )
    security_question = forms.ChoiceField(
        choices=UserSecurityProfile.SECURITY_QUESTION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-input'
        }),
        label='Security Question',
        help_text='Choose a question to use for password recovery.'
    )
    security_answer = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Answer to security question',
            'autocomplete': 'new-password'
        }),
        label='Security Answer',
        help_text='This answer will be used to verify your identity during password recovery.'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'security_question', 'security_answer')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Choose a username'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Enter a password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Confirm password'
        })
        self.fields['security_question'].widget.attrs.update({
            'class': 'form-input'
        })
        self.fields['security_answer'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Answer to security question'
        })

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            profile = UserSecurityProfile(user=user)
            profile.security_question = self.cleaned_data['security_question']
            profile.set_security_answer(self.cleaned_data['security_answer'])
            profile.save()
        return user


class PasswordResetUsernameForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your username',
            'autocomplete': 'username'
        }),
        label='Username'
    )


class PasswordResetSecurityForm(forms.Form):
    security_answer = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your security answer',
            'autocomplete': 'off'
        }),
        label='Security Answer'
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'New password',
            'autocomplete': 'new-password'
        }),
        label='New Password'
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password'
        }),
        label='Confirm New Password'
    )

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')

        if password1 and password2 and password1 != password2:
            self.add_error('new_password2', 'The two password fields did not match.')

        if self.user and password1:
            try:
                password_validation.validate_password(password1, self.user)
            except forms.ValidationError as exc:
                self.add_error('new_password1', exc)

        return cleaned_data


class UserPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Current Password',
            'autocomplete': 'current-password'
        })
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'New Password',
            'autocomplete': 'new-password'
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Confirm New Password',
            'autocomplete': 'new-password'
        })
        self.fields['old_password'].label = 'Current Password'
        self.fields['new_password1'].label = 'New Password'
        self.fields['new_password2'].label = 'Confirm New Password'
        self.fields['new_password1'].help_text = password_validation.password_validators_help_text_html()


class UserProfileForm(forms.ModelForm):
    """Form for updating user profile"""

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'Email address'
            })
        }
