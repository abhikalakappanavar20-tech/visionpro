# VeriVision Pro — System Diagrams

Project: AI-powered deepfake & manipulated-media detection platform (Django)
Modalities supported: Image, Video, Audio, Social-Media URL

All diagrams below use **Mermaid** syntax. They render natively in GitHub, VS Code (with the Mermaid preview extension), and most modern Markdown viewers.

---

## 1. Data Flow Diagram — Level 0 (Context Diagram)

Shows the system as a single process and the external entities that interact with it.

```mermaid
flowchart LR
    User([End User])
    Moderator([Moderator / Admin])
    SocialMedia[(Social Media<br/>Platforms)]
    ForensicDB[(Forensic<br/>Reference DB)]

    System(((VeriVision Pro<br/>Deepfake Detection<br/>System)))

    User -- "Uploads media / URL" --> System
    System -- "Scan Result + XAI Heatmap<br/>+ Trust Score" --> User

    User -- "Reports suspicious content" --> System
    System -- "Report confirmation" --> User

    Moderator -- "Reviews reports<br/>updates AI signatures" --> System
    System -- "Pending reports / Analytics" --> Moderator

    System -- "Fetch media from URL" --> SocialMedia
    SocialMedia -- "Media stream" --> System

    System -- "Hash lookup" --> ForensicDB
    ForensicDB -- "Known-manipulation match" --> System
```

---

## 2. Data Flow Diagram — Level 1

Expands the single process into the main sub-processes (upload, forensic pipeline, source detection, persistence, reporting, analytics).

```mermaid
flowchart TB
    User([End User])
    Moderator([Moderator])

    subgraph VeriVision["VeriVision Pro"]
        P1[1.0<br/>Authenticate &<br/>Accept Upload]
        P2[2.0<br/>File-Type Router<br/>image/video/audio/url]
        P3[3.0<br/>Forensic Pipeline<br/>ELA · Noise · EXIF · Compression]
        P4[4.0<br/>AI Source Detector<br/>Midjourney / DALL-E / etc.]
        P5[5.0<br/>Trust & Threat<br/>Score Calculator]
        P6[6.0<br/>Generate XAI<br/>Heatmap]
        P7[7.0<br/>Persist Scan<br/>Result]
        P8[8.0<br/>Report<br/>Handler]
        P9[9.0<br/>Analytics<br/>Dashboard]
    end

    DS1[(D1: MediaScan)]
    DS2[(D2: ForensicAnalysisResult)]
    DS3[(D3: AIGeneratorSignature)]
    DS4[(D4: ForensicDatabase)]
    DS5[(D5: ReportedContent)]

    User -- "credentials + file/url" --> P1
    P1 -- "validated payload" --> P2
    P2 -- "image/video/audio buffer" --> P3
    P3 -- "metrics" --> P4
    P4 -- "signature query" --> DS3
    DS3 -- "known patterns" --> P4
    P3 -- "content hash" --> DS4
    DS4 -- "match record" --> P3

    P3 -- "forensic metrics" --> P5
    P4 -- "source confidence" --> P5
    P5 -- "trust + threat" --> P6
    P6 -- "heatmap JSON" --> P7

    P7 -- "scan row" --> DS1
    P7 -- "forensic row" --> DS2
    P7 -- "scan_id + result" --> User

    User -- "report submission" --> P8
    P8 -- "report row" --> DS5
    Moderator -- "review action" --> P8
    P8 -- "status update" --> DS5

    Moderator -- "dashboard request" --> P9
    DS1 -- "aggregate stats" --> P9
    DS5 -- "pending count" --> P9
    P9 -- "charts / KPIs" --> Moderator
```

---

## 3. Entity Relationship Diagram (ERD)

Reflects the Django models in [core/models.py](core/models.py).

```mermaid
erDiagram
    USER ||--o{ MEDIASCAN : "initiates"
    MEDIASCAN ||--o| FORENSIC_ANALYSIS_RESULT : "has detailed"
    MEDIASCAN ||--o{ REPORTED_CONTENT : "may be reported in"
    AI_GENERATOR_SIGNATURE ||--o{ FORENSIC_ANALYSIS_RESULT : "matched against"
    FORENSIC_DATABASE ||--o{ MEDIASCAN : "matches by hash"

    USER {
        int id PK
        string username
        string email
        string password_hash
        datetime date_joined
    }

    MEDIASCAN {
        int id PK
        file file
        string file_type "image|video|audio|url"
        url url
        string original_filename
        string scan_result "real|suspicious|fake"
        float confidence_score
        int trust_score
        bool forensic_match
        date forensic_first_seen
        int forensic_usage_count
        text forensic_context
        json heatmap_data
        json analysis_details
        float processing_time
        datetime created_at
        ip ip_address
    }

    FORENSIC_ANALYSIS_RESULT {
        int id PK
        int scan_id FK
        float ela_score
        json ela_heatmap_data
        bool has_exif
        json exif_data
        string metadata_consistency
        string software_detected
        float noise_uniformity
        json noise_pattern_anomalies
        bool compression_artifacts_detected
        bool double_compression
        string compression_quality_estimate
        float color_histogram_score
        json color_anomalies
        json detected_sources
        string primary_source
        float source_confidence
        json manipulation_indicators
        datetime analysis_timestamp
    }

    AI_GENERATOR_SIGNATURE {
        int id PK
        string name
        string generator_type
        json typical_resolutions
        json noise_pattern
        json color_signature
        text compression_artifacts
        float ela_threshold_min
        float ela_threshold_max
        json metadata_patterns
        json key_indicators
        bool is_active
    }

    FORENSIC_DATABASE {
        int id PK
        string content_hash UK
        string content_type
        date first_seen
        int usage_count
        text context
        string known_campaigns
        string threat_level
    }

    REPORTED_CONTENT {
        int id PK
        int scan_id FK
        string url_or_file_name
        string file_type
        text reason
        email reporter_email
        text additional_info
        string status
        text moderator_notes
        datetime created_at
        datetime updated_at
    }
```

---

## 4. Class Diagram

Captures the analyzer hierarchy plus the core domain models. Mirrors [core/analyzers/](core/analyzers/) and [core/models.py](core/models.py).

```mermaid
classDiagram
    class BaseAnalyzer {
        <<abstract>>
        +str name
        +analyze(file_path) dict
        +preprocess(file_path)
        +calculate_confidence(metrics) float
    }

    class ImageForensicsAnalyzer {
        +run_ela(image) float
        +analyze_noise(image) dict
        +extract_exif(image) dict
        +detect_compression(image) dict
        +color_histogram(image) dict
        +analyze(file_path) dict
    }

    class VideoForensicsAnalyzer {
        +extract_frames(video) list
        +temporal_consistency(frames) float
        +motion_analysis(frames) dict
        +analyze(file_path) dict
    }

    class AudioForensicsAnalyzer {
        +spectral_analysis(audio) dict
        +voice_characteristics(audio) dict
        +analyze(file_path) dict
    }

    class SpectralAnalyzer {
        +compute_fft(signal) array
        +detect_anomalies(spectrum) list
    }

    class SourceDetector {
        +load_signatures()
        +match_signature(metrics) dict
        +rank_sources(matches) list
    }

    class MLModelAdapter {
        +load_model(path)
        +predict(input) dict
    }

    class EnsembleAnalyzer {
        +combine(results) dict
        +weighted_vote(results) str
    }

    class ForensicPipeline {
        -ImageForensicsAnalyzer image_analyzer
        -VideoForensicsAnalyzer video_analyzer
        -AudioForensicsAnalyzer audio_analyzer
        -SourceDetector source_detector
        +analyze_image(path, source) dict
        +analyze_video(path, source) dict
        +analyze_audio(path, source) dict
        +save_forensic_results(scan, result)
    }

    class DeepfakeAnalyzer {
        +analyze_url(url) dict
    }

    class ThreatLevelCalculator {
        +calculate(result, conf, trust, match) str
    }

    class MediaScan {
        +int id
        +FileField file
        +str file_type
        +str scan_result
        +float confidence_score
        +int trust_score
        +bool forensic_match
        +json heatmap_data
        +json analysis_details
    }

    class ForensicAnalysisResult {
        +int id
        +MediaScan scan
        +float ela_score
        +bool has_exif
        +float noise_uniformity
        +json detected_sources
        +str primary_source
    }

    class AIGeneratorSignature {
        +str name
        +str generator_type
        +json noise_pattern
        +float ela_threshold_min
        +float ela_threshold_max
    }

    class ReportedContent {
        +int id
        +MediaScan scan
        +str reason
        +str status
        +str reporter_email
    }

    class ForensicDatabase {
        +str content_hash
        +str content_type
        +int usage_count
        +str threat_level
    }

    BaseAnalyzer <|-- ImageForensicsAnalyzer
    BaseAnalyzer <|-- VideoForensicsAnalyzer
    BaseAnalyzer <|-- AudioForensicsAnalyzer
    BaseAnalyzer <|-- SpectralAnalyzer

    ForensicPipeline o-- ImageForensicsAnalyzer
    ForensicPipeline o-- VideoForensicsAnalyzer
    ForensicPipeline o-- AudioForensicsAnalyzer
    ForensicPipeline o-- SourceDetector
    SourceDetector ..> AIGeneratorSignature : queries
    EnsembleAnalyzer o-- MLModelAdapter

    ForensicPipeline ..> MediaScan : creates
    ForensicPipeline ..> ForensicAnalysisResult : creates
    MediaScan "1" --o "0..1" ForensicAnalysisResult
    MediaScan "1" --o "0..*" ReportedContent
    ForensicDatabase ..> MediaScan : enriches
    DeepfakeAnalyzer ..> MediaScan : creates
    ThreatLevelCalculator ..> MediaScan : scores
```

---

## 5. Flow Chart — Media Scan Workflow

End-to-end flow when a user submits media for analysis (image/video/audio/URL).

```mermaid
flowchart TD
    Start([User opens /scan]) --> Auth{Authenticated?}
    Auth -- No --> Login[Redirect to /login]
    Login --> Auth
    Auth -- Yes --> Upload[Upload file or paste URL]
    Upload --> Validate{Form valid?}
    Validate -- No --> Err1[Show validation errors]
    Err1 --> Upload
    Validate -- Yes --> Route{Input type?}

    Route -- URL --> AnalyzeURL[DeepfakeAnalyzer.analyze_url]
    Route -- File --> Ext{Extension?}
    Ext -- jpg/png/webp --> Img[ForensicPipeline.analyze_image]
    Ext -- mp4/mov/webm --> Vid[ForensicPipeline.analyze_video]
    Ext -- wav/mp3/flac --> Aud[ForensicPipeline.analyze_audio]

    Img --> ELA[Run ELA · Noise · EXIF · Compression · Color]
    ELA --> Source[SourceDetector matches AI signatures]
    Source --> Hash[Hash lookup in ForensicDatabase]
    Vid --> Frames[Extract frames + temporal analysis] --> Hash
    Aud --> Spec[Spectral + voice analysis] --> Hash
    AnalyzeURL --> Hash

    Hash --> Score[Compute confidence + trust]
    Score --> Heat[Generate XAI heatmap]
    Heat --> Decide{scan_result?}
    Decide -- real --> Save
    Decide -- suspicious --> Save
    Decide -- fake --> Save
    Save[Persist MediaScan + ForensicAnalysisResult] --> Redirect[Redirect to /result/<id>]
    Redirect --> Display[Render verdict + heatmap + threat level]
    Display --> Choice{User action?}
    Choice -- View dashboard --> Dash[/dashboard]
    Choice -- Report content --> Report[/report/<id>]
    Choice -- Done --> End([End])
    Dash --> End
    Report --> End
```

---

## 6. Use Case Diagram

Actors: **Guest**, **Authenticated User**, **Moderator/Admin**, and the **Forensic Pipeline** (system actor).

```mermaid
flowchart LR
    Guest((Guest))
    UserA((Authenticated<br/>User))
    Mod((Moderator /<br/>Admin))
    Pipeline((Forensic<br/>Pipeline))

    subgraph VeriVision[VeriVision Pro]
        UC1([Register Account])
        UC2([Login / Logout])
        UC3([View Landing Page])
        UC4([Upload Image/Video/Audio])
        UC5([Submit Social-Media URL])
        UC6([Capture from Webcam])
        UC7([View Scan Result + Heatmap])
        UC8([View Scan History])
        UC9([Report Suspicious Content])
        UC10([Edit Profile])
        UC11([View Analytics Dashboard])
        UC12([Review Reports])
        UC13([Manage AI Signatures])
        UC14([Run Forensic Analysis])
        UC15([Match Against Forensic DB])
        UC16([Compute Trust & Threat Score])
    end

    Guest --> UC1
    Guest --> UC2
    Guest --> UC3

    UserA --> UC2
    UserA --> UC4
    UserA --> UC5
    UserA --> UC6
    UserA --> UC7
    UserA --> UC8
    UserA --> UC9
    UserA --> UC10
    UserA --> UC11

    Mod --> UC11
    Mod --> UC12
    Mod --> UC13

    UC4 -. includes .-> UC14
    UC5 -. includes .-> UC14
    UC6 -. includes .-> UC14
    UC14 -. includes .-> UC15
    UC14 -. includes .-> UC16
    UC7 -. extends .-> UC9

    Pipeline --> UC14
    Pipeline --> UC15
    Pipeline --> UC16
```

---

## Legend

| Notation | Meaning |
|----------|---------|
| `(())` | External entity / actor |
| `((( )))` | System (Level-0 only) |
| `[ ]` | Process / activity |
| `[( )]` | Data store |
| `{ }` | Decision |
| `..>` | Dependency / uses |
| `<\|--` | Inheritance |
| `o--` | Aggregation / composition |
| `includes` / `extends` | UML use-case relations |

> Tip: open this file in VS Code with the **Markdown Preview Mermaid Support** extension, or push to GitHub — both render the diagrams inline.
