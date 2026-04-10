# AI Generation Detection

## Overview

VeriVisionPro now includes comprehensive **AI-generated content detection** across all media types:

- ✅ **Images** - AI art generators, image synthesis, face manipulation
- ✅ **Videos** - AI video generators, deepfakes, talking heads
- ✅ **Audio** - Voice cloning, synthetic speech, AI voice generators

---

## 🖼️ AI Image Generation Detection

### Supported AI Image Generators

**Popular AI Art Generators:**
- Midjourney v5
- Midjourney v6
- DALL-E 2
- DALL-E 3
- Stable Diffusion
- Stable Diffusion XL
- Adobe Firefly
- Leonardo.ai
- Ideogram

**Face Manipulation Tools:**
- DeepFaceLab
- Faceswap

### Detection Method

The system analyzes multiple forensic characteristics:

1. **Resolution Patterns** - AI generators have typical output resolutions
2. **Noise Distribution** - AI-generated images have unique noise patterns
3. **Color Signatures** - Each AI has characteristic color profiles
4. **ELA Values** - Error Level Analysis reveals manipulation
5. **Metadata Analysis** - Missing EXIF, software signatures

### Examples

| Generator | Typical Resolution | Key Indicators |
|-----------|-------------------|----------------|
| **Midjourney v6** | 1024x1024, 1920x1080 | Photorealistic, uniform noise |
| **DALL-E 3** | 1024x1024 | Vivid colors, smooth surfaces |
| **Stable Diffusion** | 512x512, 768x768 | High contrast, edge artifacts |
| **Adobe Firefly** | 1920x1080, 1080x1920 | Professional quality, balanced colors |
| **DeepFaceLab** | Variable | Face boundary artifacts, skin tone inconsistencies |

---

## 🎥 AI Video Generation Detection

### Supported AI Video Generators

**Video Generation Platforms:**
- Sora (OpenAI)
- Runway Gen-2/Gen-3
- Pika Labs

**AI Avatar/Talking Head:**
- HeyGen
- D-ID

**Deepfake Detection:**
- DeepVideo Labs
- Face manipulation tools

### Detection Method

Video analysis includes:

1. **Temporal Consistency** - AI-generated videos have unnatural consistency
2. **Face Tracking** - Detects face manipulation and anomalies
3. **Motion Patterns** - Identifies unnatural motion or frozen frames
4. **Resolution & FPS** - Each generator has typical output specs
5. **Duration Patterns** - Some platforms have default durations

### Examples

| Generator | Typical Resolution | Key Indicators |
|-----------|-------------------|----------------|
| **Sora** | 1920x1080, 1080x1920 | Photorealistic, high temporal consistency |
| **Runway Gen-3** | 1920x1080, 1024x1024 | Artistic styles, smooth motion |
| **HeyGen** | 1920x1080, 1280x720 | AI avatar, very high temporal consistency |
| **D-ID** | 1920x1080, 1080x1080 | Talking head, photo animation |
| **DeepVideo** | Variable | Face manipulation, temporal inconsistencies |

---

## 🎙️ AI Audio Generation Detection

### Supported AI Audio Generators

**Text-to-Speech:**
- ElevenLabs
- Murf.ai
- Play.ht

**Voice Cloning:**
- Resemble.ai
- Respeecher
- VALL-E

### Detection Method

Audio analysis examines:

1. **Pitch Consistency** - AI voices have extremely consistent pitch
2. **Spectral Features** - Synthetic audio has unique spectral patterns
3. **Zero Crossing Rate** - Different from human speech
4. **Voice Characteristics** - Controlled pitch range, steady rhythm
5. **Duration Patterns** - Some platforms have typical duration ranges

### Examples

| Generator | Duration Range | Key Indicators |
|-----------|----------------|----------------|
| **ElevenLabs** | 0.5-300 seconds | Very consistent pitch, low background noise |
| **Murf.ai** | 1-600 seconds | Professional quality, steady rhythm |
| **Play.ht** | 1-600 seconds | Natural-sounding, variable intonation |
| **Resemble.ai** | 0.5-300 seconds | Voice cloning, high fidelity |
| **VALL-E** | 1-300 seconds | Few-shot cloning, acoustic detail matching |

---

## 🔍 How Detection Works

### Image Detection Process

```
1. Analyze image with ImageForensicsAnalyzer
   ↓
2. Extract forensic features:
   - Resolution
   - Noise uniformity
   - Color saturation
   - ELA score
   - Metadata
   ↓
3. Match against AI generator signatures
   ↓
4. Calculate confidence score for each generator
   ↓
5. Return top matches with confidence > 10%
```

### Video Detection Process

```
1. Analyze video with VideoForensicsAnalyzer
   ↓
2. Extract forensic features:
   - Resolution & FPS
   - Duration
   - Temporal consistency
   - Face tracking data
   ↓
3. Match against AI video generator signatures
   ↓
4. Calculate confidence score for each generator
   ↓
5. Return top matches with confidence > 10%
```

### Audio Detection Process

```
1. Analyze audio with AudioForensicsAnalyzer
   ↓
2. Extract forensic features:
   - Duration
   - Spectral features
   - Voice characteristics
   - Pitch patterns
   ↓
3. Match against AI audio generator signatures
   ↓
4. Calculate confidence score for each generator
   ↓
5. Return top matches with confidence > 10%
```

---

## 📊 Confidence Scoring

### AI Detection Confidence Levels

| Confidence Range | Meaning |
|------------------|---------|
| **0-30%** | Not reported - too low, likely false positive |
| **30-45%** | Low confidence - possible AI, requires verification |
| **45-65%** | Medium confidence - multiple indicators match |
| **65-100%** | High confidence - definitive AI signatures |

### Impact on Overall Score

When AI generation is detected with high confidence (>25%), the overall confidence score is boosted:

- **Images**: Boosted to minimum 55%
- **Videos**: 15% boost
- **Audio**: 15% boost

This ensures that AI-generated content is correctly classified as **FAKE** (≥40% threshold).

---

## 🎯 Real vs Edited vs AI-Generated

The system now distinguishes between three categories:

### ✅ REAL (Score < 40%)
- Original camera photos/videos/audio
- No editing or manipulation
- Natural characteristics
- Normal compression artifacts

### ❌ FAKE - Edited (Score 40-70%)
- Real content that has been edited
- Filters applied
- Photoshop/GIMP editing
- Manual manipulation
- NOT AI-generated

### ❌ FAKE - AI-Generated (Score 70-100%)
- Completely AI-generated content
- AI art tools (Midjourney, DALL-E, etc.)
- Deepfakes
- Voice cloning
- Synthetic media
- No original real content

---

## 💡 Use Cases

### When AI Detection Helps

1. **Content Verification**
   - Verify if social media images are real or AI-generated
   - Check if news footage is authentic or deepfake
   - Determine if audio evidence is genuine

2. **Copyright Protection**
   - Detect AI-generated content that shouldn't have copyright
   - Identify human-created vs AI-created art
   - Verify content originality

3. **Fraud Prevention**
   - Detect deepfake videos used for scams
   - Identify AI-generated voice clones
   - Verify identity documents and media

4. **Academic Integrity**
   - Detect AI-generated images in student work
   - Verify originality of submitted content

---

## 🔧 Technical Details

### Signature Matching Algorithm

Each AI generator has a signature with multiple characteristics:

```python
signature = {
    'typical_resolutions': ['1024x1024', '2048x2048'],
    'noise_pattern': {
        'uniformity_range': (0.4, 0.6),
        'distribution': 'non-uniform',
        'characteristics': ['patchy', 'inconsistent']
    },
    'color_signature': {
        'saturation_range': (140, 180),
        'contrast_range': (50, 80),
        'characteristic': 'high_saturation'
    },
    'ela_threshold': (15, 35),
    'metadata_patterns': {
        'missing_exif': True
    }
}
```

The system matches forensic results against signatures and calculates a confidence score based on how many characteristics match.

### Confidence Threshold

- **Minimum confidence to report**: 30% (to avoid false positives on real photos)
- **High confidence threshold**: 45%
- **Boost threshold**: 35% (affects overall score)

---

## 🚀 Future Enhancements

Planned improvements:

1. **More AI Generators**
   - Add newer AI tools as they emerge
   - Community-contributed signatures

2. **Deep Learning Integration**
   - Train ML models on AI-generated content
   - Improve detection accuracy

3. **Real-time Detection**
   - Live video stream analysis
   - Real-time audio verification

4. **Browser Extension**
   - One-click AI detection while browsing
   - Social media integration

---

## 📝 Notes

- **False Positives**: Some real content may have characteristics similar to AI-generated content
- **False Negatives**: AI generators are improving and becoming harder to detect
- **Confidence Scores**: Always consider the confidence level when interpreting results
- **Human Review**: For critical applications, always verify with additional methods

---

## 🔗 Related Documentation

- [Binary Classification](BINARY_CLASSIFICATION.md) - How REAL/FAKE classification works
- [Architecture](ARCHITECTURE.md) - System architecture overview
- [README.md](README.md) - Main project documentation
