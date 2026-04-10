"""
Forms for VeriVision
"""
from django import forms
from django.core.validators import URLValidator
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import MediaScan, ReportedContent


class MediaUploadForm(forms.ModelForm):
    """Form for uploading media files"""

    ACCEPTED_FILE_TYPES = [
        '.jpg', '.jpeg', '.png', '.gif', '.webp',  # Images
        '.mp4', '.avi', '.mov', '.mkv', '.webm',  # Videos (webcam uses .webm)
        '.wav', '.mp3', '.m4a', '.flac'  # Audio
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
            'placeholder': 'your@email.com'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

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

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


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
