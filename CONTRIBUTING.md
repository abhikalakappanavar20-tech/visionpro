# Contributing to VeriVision Pro

Thank you for your interest in contributing to VeriVision Pro! This document provides guidelines and instructions for contributing to the project.

## 🤝 How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates.

**Bug Report Template:**
```markdown
### Bug Description
A clear and concise description of what the bug is.

### To Reproduce
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

### Expected Behavior
A clear description of what you expected to happen.

### Screenshots
If applicable, add screenshots to help explain your problem.

### Environment
- OS: [e.g. Windows 11, macOS 14, Ubuntu 22.04]
- Python Version: [e.g. 3.12.0]
- Browser: [e.g. Chrome 120, Firefox 121]
- Django Version: [e.g. 5.0.1]

### Additional Context
Add any other context about the problem here.
```

### Suggesting Enhancements

**Enhancement Template:**
```markdown
### Feature Description
A clear and concise description of the feature you'd like to see added.

### Problem Statement
What problem does this feature solve? What value does it add?

### Proposed Solution
A detailed description of how you envision this feature working.

### Alternatives Considered
A clear description of any alternative solutions or features you've considered.

### Additional Context
Add any other context or screenshots about the feature request here.
```

### Pull Request Process

1. **Fork the Repository**
   ```bash
   git clone https://github.com/yourusername/VeriVisionPro.git
   cd VeriVisionPro
   ```

2. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make Your Changes**
   - Write clean, documented code
   - Follow PEP 8 style guidelines
   - Add tests for new features
   - Update documentation

4. **Test Your Changes**
   ```bash
   # Run tests
   python manage.py test

   # Check code style
   flake8
   ```

5. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "Add: Brief description of changes"
   ```

   **Commit Message Format:**
   ```
   <type>(<scope>): <subject>

   <body>

   <footer>
   ```

   **Types:**
   - `feat`: New feature
   - `fix`: Bug fix
   - `docs`: Documentation changes
   - `style`: Code style changes (formatting, etc.)
   - `refactor`: Code refactoring
   - `test`: Adding or updating tests
   - `chore`: Maintenance tasks

   **Example:**
   ```
   feat(analyzers): Add deep learning model integration

   - Integrated FaceNet model for face detection
   - Added model loading and prediction methods
   - Updated documentation

   Closes #123
   ```

6. **Push and Create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

   Then create a pull request on GitHub.

## 📝 Code Style Guidelines

### Python Code Style

Follow **PEP 8** guidelines:

```python
# Good
def analyze_image(image_path: str) -> dict:
    """Analyze image for deepfake detection.
    
    Args:
        image_path: Path to image file
        
    Returns:
        dict with analysis results
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    # Implementation here
    return result

# Bad
def analyze(imagePath):  # Missing type hints and docstring
    if not os.path.exists(imagePath):  # Poor variable naming
        return False
    return True
```

### Django Best Practices

1. **Use Django's built-in features**
   ```python
   # Good
   from django.shortcuts import get_object_or_404
   scan = get_object_or_404(MediaScan, id=scan_id)
   
   # Bad
   try:
       scan = MediaScan.objects.get(id=scan_id)
   except MediaScan.DoesNotExist:
       raise Http404()
   ```

2. **Use queryset methods efficiently**
   ```python
   # Good
   recent_scans = MediaScan.objects.select_related('user').order_by('-created_at')[:10]
   
   # Bad (N+1 query problem)
   recent_scans = MediaScan.objects.all()[:10]
   for scan in recent_scans:
       print(scan.user.username)
   ```

3. **Use Django's form validation**
   ```python
   # Good
   class MediaUploadForm(forms.ModelForm):
       class Meta:
           model = MediaScan
           fields = ['file', 'url']
       
       def clean_file(self):
           file = self.cleaned_data.get('file')
           if file:
               # Validate file
               if file.size > MAX_UPLOAD_SIZE:
                   raise forms.ValidationError("File too large")
           return file
   ```

### JavaScript Code Style

```javascript
// Good
function analyzeCapture() {
    if (!capturedBlob) {
        showStatus('No capture to analyze', 'error');
        return;
    }
    
    loadingOverlay.classList.add('active');
    
    fetch('/scan/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        updateUI(data);
    })
    .catch(error => {
        console.error('Analysis failed:', error);
    });
}

// Bad (inconsistent style)
function analyze(){
if(!blob){
alert("error")
}
fetch('/scan/',{
method:'POST',
body:data
})
}
```

## 🧪 Testing Guidelines

### Writing Tests

```python
from django.test import TestCase
from core.models import MediaScan
from core.analyzers import ImageForensicsAnalyzer

class ImageAnalysisTest(TestCase):
    """Test image analysis functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = ImageForensicsAnalyzer()
    
    def test_ela_analysis(self):
        """Test ELA analysis returns valid score"""
        result = self.analyzer.analyze('test_image.jpg')
        
        self.assertIn('score', result)
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 100)
    
    def test_invalid_image(self):
        """Test handling of invalid image"""
        with self.assertRaises(FileNotFoundError):
            self.analyzer.analyze('nonexistent.jpg')
```

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific app
python manage.py test core

# Run specific test class
python manage.py test core.tests.test_models

# Run with verbosity
python manage.py test --verbosity=2

# Run coverage report
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML report
```

## 📚 Documentation Guidelines

### Code Documentation

Use **docstrings** for all modules, classes, and functions:

```python
def detect_manipulation(image_path: str, threshold: float = 0.5) -> bool:
    """Detect if an image has been manipulated.
    
    This function uses Error Level Analysis (ELA) to detect
    regions of an image that may have been edited or modified.
    
    Args:
        image_path (str): Path to the image file to analyze
        threshold (float, optional): Confidence threshold for detection.
            Defaults to 0.5. Higher values = more conservative.
    
    Returns:
        bool: True if manipulation detected, False otherwise
    
    Raises:
        FileNotFoundError: If image_path doesn't exist
        ValueError: If image is invalid or corrupted
        
    Example:
        >>> detect_manipulation('photo.jpg', threshold=0.7)
        True
        
        >>> detect_manipulation('real_photo.jpg')
        False
    
    Note:
        This function requires PIL/Pillow and OpenCV to be installed.
        Minimum image resolution is 256x256 pixels.
    """
    pass
```

### README Documentation

Keep README.md up to date with:
- Installation instructions
- Feature descriptions
- Usage examples
- API documentation
- Troubleshooting tips

## 🔒 Security Guidelines

### Handling User Data

```python
# Good - Validate and sanitize input
def scan_url(request):
    url = request.POST.get('url', '')
    
    # Validate URL
    try:
        URLValidator()(url)
    except ValidationError:
        return JsonResponse({'error': 'Invalid URL'}, status=400)
    
    # Sanitize URL
    url = sanitize_url(url)
    
    # Process...
    
# Bad - No validation
def scan_url(request):
    url = request.POST['url']
    # Directly use user input - DANGEROUS!
    result = process_url(url)
```

### File Upload Security

```python
# Good - Validate file uploads
class MediaUploadForm(forms.ModelForm):
    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        if file:
            # Check file size
            if file.size > settings.MAX_UPLOAD_SIZE:
                raise forms.ValidationError("File too large")
            
            # Check file extension
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in settings.ALLOWED_EXTENSIONS:
                raise forms.ValidationError("Invalid file type")
            
            # Validate file content
            if not is_valid_file(file):
                raise forms.ValidationError("Corrupted or invalid file")
        
        return file

# Bad - No validation
def upload(request):
    file = request.FILES['file']
    # Save without any checks - DANGEROUS!
    with open(f'uploads/{file.name}', 'wb') as f:
        f.write(file.read())
```

## 🎨 UI/UX Guidelines

### Responsive Design

Ensure all new features work on:
- Desktop (1920x1080 and above)
- Tablet (768x1024)
- Mobile (320x568 and above)

### Accessibility

- Use semantic HTML
- Add ARIA labels where needed
- Ensure keyboard navigation works
- Provide alt text for images
- Use sufficient color contrast

### User Feedback

```python
# Good - Provide clear feedback
messages.success(request, 'Analysis completed successfully!')
messages.error(request, 'Analysis failed: Invalid file format')
messages.warning(request, 'File size exceeds limit')

# Bad - No user feedback
result = process_file(file)
return JsonResponse(result)
```

## 📋 Project Structure

```
VeriVisionPro/
├── VeriVision/           # Django project settings
├── core/                 # Main application
│   ├── analyzers/        # Analysis modules
│   │   ├── __init__.py
│   │   ├── base_analyzer.py
│   │   ├── image_forensics.py
│   │   ├── video_forensics.py
│   │   ├── audio_forensics.py
│   │   ├── forensic_pipeline.py
│   │   ├── ml_adapter.py
│   │   └── source_detector.py
│   ├── management/       # Django management commands
│   ├── migrations/       # Database migrations
│   ├── templates/core/   # HTML templates
│   ├── static/           # CSS, JS, images
│   ├── tests/            # Test files
│   ├── models.py         # Database models
│   ├── views.py          # View functions
│   ├── forms.py          # Form classes
│   └── urls.py           # URL configuration
├── media/                # User uploaded files
├── requirements.txt      # Dependencies
├── README.md            # This file
└── manage.py            # Django management script
```

## 🚀 Release Process

### Version Numbering

We use **Semantic Versioning** (MAJOR.MINOR.PATCH):

- **MAJOR**: Incompatible API changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

Example: `2.1.3`

### Release Checklist

- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version number updated
- [ ] Git tag created
- [ ] Release published on GitHub

## 💬 Getting Help

### Communication Channels

- **GitHub Discussions**: Ask questions and discuss ideas
- **GitHub Issues**: Report bugs and request features
- **Discord Server**: Chat with other contributors

### Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [OpenCV Documentation](https://docs.opencv.org/)
- [PyTorch Documentation](https://pytorch.org/docs/stable/)

## 🌟 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Invited to join the core team (for significant contributions)

## 📜 Code of Conduct

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone.

### Our Standards

- Use welcoming and inclusive language
- Respect differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

### Unacceptable Behavior

- Harassment, insulting or derogatory comments
- Personal or political attacks
- Public or private harassment
- Publishing private information without permission
- Any other unethical or unprofessional conduct

## 🔖 License

By contributing, you agree that your contributions will be licensed under the **MIT License**.

---

**Thank you for contributing to VeriVision Pro! 🙏**
