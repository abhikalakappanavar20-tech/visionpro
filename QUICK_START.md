# Quick Start Guide - VeriVision Pro

## 🚀 Get Started in 5 Minutes

### Step 1: Install Dependencies (2 minutes)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### Step 2: Setup Database (1 minute)

```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 3: Create Account (1 minute)

```bash
# Option A: Create superuser (admin access)
python manage.py createsuperuser

# Option B: Register through web interface
# Open http://127.0.0.1:8000/register in browser
```

### Step 4: Run Server (30 seconds)

```bash
python manage.py runserver
```

### Step 5: Start Detecting! (30 seconds)

Open browser: `http://127.0.0.1:8000`

## 📸 How to Use

### Analyze an Image
1. Click **Upload** in menu
2. Select image file
3. Click **Analyze**
4. View results with heatmap!

### Use Webcam
1. Click **Webcam** in menu
2. Allow camera access
3. Click **Start Camera**
4. Capture photo or record video
5. Click **Analyze**

### Scan Social Media URL
1. Copy post URL (Twitter, Facebook, Instagram)
2. Paste in **Quick URL Scan** box
3. Click **Analyze URL**
4. Get instant results!

## 🎯 Understanding Results

| Result | Meaning | Action |
|--------|---------|--------|
| 🟢 **Real** | Content appears authentic | Safe to use |
| 🟡 **Suspicious** | Some editing detected | Verify source |
| 🟠 **Manipulated** | Probably edited | Use with caution |
| 🔴 **Fake** | Likely AI-generated | Do not trust |

## 🆘 Quick Help

### Webcam not working?
- Use Chrome or Firefox browser
- Allow camera permissions
- Try HTTPS instead of HTTP

### Upload failed?
- Check file size (< 5GB)
- Verify file format (JPG, PNG, MP4, WEBM)
- Ensure you're logged in

### Analysis too slow?
- Large files take longer
- Videos need more processing time
- Be patient, accuracy matters!

## 📞 Need More Help?

- Full Documentation: [README.md](README.md)
- Report Issues: GitHub Issues
- Email: support@verivision.example.com

---

**Happy Deepfake Detection! 🛡️**
