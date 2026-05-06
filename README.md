# 🛡️ DeepFake Shield

> **Multi-modal AI-powered deepfake detection web application**  
> Detects manipulated content across **Image · Video · Audio · Text** using LLaMA 4 Maverick via Groq API

---

## 📌 Overview

**DeepFake Shield** is a full-stack AI web application that detects deepfake and AI-generated content across multiple media types. Built with Flask and powered by **LLaMA 4 Maverick** through the **Groq API**, it provides fast, accurate analysis of images, videos, audio clips, and text — all from a single unified interface.

Originally developed for the **Google Solution Challenge 2026**, the project has since evolved into a production-ready multi-modal detection platform deployed on Render.

---

## ✨ Features

| Mode | Input | What it detects |
|------|-------|-----------------|
| 🖼️ **Image** | JPG, PNG, WEBP | Face swaps, GAN-generated faces, synthetic images |
| 🎬 **Video** | MP4, AVI, MOV | Frame-level deepfake manipulation, synthetic video |
| 🎵 **Audio** | MP3, WAV | Voice cloning, AI-generated speech |
| 📝 **Text** | Plain text | AI-generated content, LLM-written text |

- ⚡ **Fast inference** powered by Groq API (LLaMA 4 Maverick)
- 🌐 Clean, responsive web UI — works on mobile and desktop
- 🔒 Secure file upload with type and size validation
- 📊 Confidence score with detailed analysis explanation
- 🚀 Deployed and live on **Render**

---

## 🏗️ Architecture

```
deepfake-shield/
├── app.py                  # Flask app entry point
├── requirements.txt        # Python dependencies
├── .env                    # API keys (not committed)
│
├── routes/
│   ├── image_routes.py     # Image detection endpoint
│   ├── video_routes.py     # Video detection endpoint
│   ├── audio_routes.py     # Audio detection endpoint
│   └── text_routes.py      # Text detection endpoint
│
├── utils/
│   ├── groq_client.py      # Groq API wrapper
│   ├── file_handler.py     # Upload validation & processing
│   └── preprocessors.py    # Media preprocessing logic
│
├── templates/
│   ├── index.html          # Landing page
│   └── result.html         # Detection result page
│
└── static/
    ├── css/
    └── js/
```

---

## 🛠️ Tech Stack

- **Backend:** Python 3.10+, Flask
- **AI Model:** LLaMA 4 Maverick via [Groq API](https://groq.com)
- **Frontend:** HTML5, CSS3, JavaScript
- **Deployment:** Render
- **Version Control:** Git + GitHub

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Groq API key → [Get free key at console.groq.com](https://console.groq.com)
- Git

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/deepfake-shield.git
cd deepfake-shield

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Add your GROQ_API_KEY in .env

# 5. Run the application
python app.py
```

Open `http://localhost:5000` in your browser.

### Environment Variables

```env
GROQ_API_KEY=your_groq_api_key_here
FLASK_ENV=development
MAX_UPLOAD_SIZE_MB=10
```



## 🔌 API Reference

### POST `/detect/image`
Upload an image for deepfake detection.

```bash
curl -X POST http://localhost:5000/detect/image \
  -F "file=@sample.jpg"
```

**Response:**
```json
{
  "result": "DEEPFAKE DETECTED",
  "confidence": 0.94,
  "explanation": "Facial inconsistencies and unnatural skin texture detected...",
  "mode": "image"
}
```

### POST `/detect/text`
Submit text for AI-generation detection.

```bash
curl -X POST http://localhost:5000/detect/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Your text content here"}'
```

---

## 🧠 How It Works

1. **Upload** — User submits media via the web interface
2. **Preprocess** — File is validated, resized/sampled as needed
3. **Analyze** — Preprocessed content is sent to LLaMA 4 Maverick via Groq API with a carefully engineered detection prompt
4. **Result** — Model returns a verdict (Real / Deepfake), confidence score, and explanation
5. **Display** — Results shown on a clean result page with detailed reasoning

---

## 📦 Requirements

```
flask>=3.0.0
groq>=0.5.0
python-dotenv>=1.0.0
pillow>=10.0.0
moviepy>=1.0.3
pydub>=0.25.1
gunicorn>=21.0.0
```

---

## 🌐 Deployment

This project is deployed on **Render** using `gunicorn`.

**Render config (`render.yaml`):**
```yaml
services:
  - type: web
    name: deepfake-shield
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    envVars:
      - key: GROQ_API_KEY
        sync: false
```

---

## 🎯 Use Cases

- **Journalists** — Verify authenticity of media before publishing
- **Social media platforms** — Automated content moderation
- **Individuals** — Check if a video/image of them has been faked
- **Researchers** — Study deepfake detection techniques

---

## 🔭 Future Roadmap

- [ ] Real-time video stream detection
- [ ] Browser extension for instant verification
- [ ] REST API with authentication for third-party integrations
- [ ] Mobile app (React Native)
- [ ] Batch detection for multiple files

---

## 👨‍💻 Author

**Muralidhar** — AI & Data Science Student  
Paavai Engineering College (2024–2028)

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

- [Groq](https://groq.com) — For blazing fast LLM inference API
- [Meta AI](https://ai.meta.com) — For LLaMA 4 Maverick model
