from flask import Flask, render_template, request, jsonify
import base64
import os
import traceback
import requests
import cv2
import tempfile
import urllib.parse
from bs4 import BeautifulSoup
import database

# Initialize database table
database.init_db()

app = Flask(__name__)

# --- API Key Setup ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

PROMPT = """
WARNING: You are participating in an AI identification challenge. Your objective is zero-tolerance for AI generation. 
You are a highly advanced digital forensics expert analyzing this image for deepfakes, CGI synthesis, and modern AI generation (Stable Diffusion, Midjourney).

This is a STRICT evaluation. A large portion of these images are FAKE.
Look extremely closely for the "AI Glow" and these synthetic markers:
1. People & Faces: Impossibly flawless, airbrushed skin without natural red splotches, pores, or peach fuzz. Look for the "CGI Sheen" or "Plastic" look. This is the #1 sign of AI.
2. Eyes: Glassy, unnervingly clear irises with perfect, high-contrast, identical catchlights in both eyes.
3. Hair: Overly stylized hair strands that clump weirdly or lack natural chaotic flyaways.
4. Portrait Aesthetics: A highly cinematic, hyper-focused "studio lighting" effect with an out-of-focus background that feels like digital art rather than a genuine photograph.
5. Clothing & Objects: Unnaturally crisp collars, asymmetrical lapels, or nonsensical background elements.
6. Documents: Gibberish text, asymmetrical logos, weird fonts on certificates.

If the image looks like high-quality digital art, has flawlessly smooth skin, or exhibits an overly-perfect cinematic studio glow, you MUST classify it as FAKE. Genuine photos have messy lighting, distinct pores, and random structural noise.

Respond ONLY in this exact format (no extra text):
VERDICT: FAKE or REAL
CONFIDENCE: (a number between 0 and 100)
RISK: HIGH or LOW
SIGNALS: (comma separated list of detected synthetic issues, or "None" if unambiguously real)
EXPLANATION: (one strict sentence explaining the CGI/AI signature spotted)
"""


def extract_media_from_html(html_content, media_type):
    """Attempts to extract a direct image/video URL from HTML using OpenGraph or tag analysis."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        if media_type == 'image':
            # Check og:image, twitter:image
            og_img = soup.find('meta', property='og:image') or soup.find('meta', name='twitter:image')
            if og_img and og_img.get('content'):
                return og_img.get('content')
            # Fallback to first high-res img tag
            for img in soup.find_all('img'):
                src = img.get('src')
                if src and (src.startswith('http') or src.startswith('//')):
                    width = img.get('width')
                    height = img.get('height')
                    if (not width or int(width) > 100) and (not height or int(height) > 100):
                        return src
                        
        elif media_type == 'video':
            # Check og:video
            og_vid = soup.find('meta', property='og:video') or soup.find('meta', property='og:video:url')
            if og_vid and og_vid.get('content'):
                return og_vid.get('content')
            # Fallback to <video> source tags
            for video in soup.find_all('video'):
                for source in video.find_all('source'):
                    src = source.get('src')
                    if src:
                        return src
                src = video.get('src')
                if src:
                    return src
    except Exception:
        pass
    return None


def download_file_from_url(url, allowed_extensions=None, media_type=None):
    """Downloads a file from a URL to a temporary location and returns the path."""
    try:
        # Prepend scheme if missing
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # Safe request handling with unverified SSL fallback
        try:
            res = requests.get(url, headers=headers, stream=True, timeout=30)
            res.raise_for_status()
        except requests.exceptions.SSLError:
            res = requests.get(url, headers=headers, stream=True, timeout=30, verify=False)
            res.raise_for_status()
        
        # Check content-type to reject webpages or extract media
        content_type = res.headers.get('content-type', '').lower()
        if 'text/html' in content_type:
            if media_type:
                # Scrape up to 1MB of the HTML
                html_snippet = res.raw.read(1024 * 1024)
                if not html_snippet:
                    html_snippet = res.text
                extracted_url = extract_media_from_html(html_snippet, media_type)
                if extracted_url:
                    if extracted_url.startswith('//'):
                        extracted_url = 'https:' + extracted_url
                    return download_file_from_url(extracted_url, allowed_extensions, media_type)
            raise Exception("The URL points to a webpage (HTML), not a direct file. Please provide a direct download link.")
            
        # Limit downloads to 50MB
        content_length = res.headers.get('content-length')
        if content_length and int(content_length) > 50 * 1024 * 1024:
            raise Exception("File is too large (maximum allowed size is 50MB)")
            
        parsed_url = urllib.parse.urlparse(url)
        filename = os.path.basename(parsed_url.path)
        ext = os.path.splitext(filename)[1].lower()
        
        if not ext:
            if 'image' in content_type:
                ext = '.jpg'
            elif 'video' in content_type:
                ext = '.mp4'
            elif 'audio' in content_type:
                ext = '.mp3'
            else:
                ext = '.tmp'
                
        if allowed_extensions and ext not in allowed_extensions:
            if ext != '.tmp':
                raise Exception(f"File type {ext} is not supported. Supported extensions: {', '.join(allowed_extensions)}")

        temp_dir = tempfile.gettempdir()
        temp_file_fd, temp_file_path = tempfile.mkstemp(suffix=ext, dir=temp_dir)
        
        with os.fdopen(temp_file_fd, 'wb') as f:
            for chunk in res.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    
        return temp_file_path
    except requests.exceptions.HTTPError as he:
        if he.response is not None and he.response.status_code == 403:
            raise Exception("Access Forbidden (403). The website is blocking automated requests. Please right-click the image/video, select 'Copy Image Link' (or 'Open Image in New Tab'), and paste that direct link instead.")
        raise Exception(f"HTTP Error: {str(he)}")
    except Exception as e:
        if "403" in str(e):
            raise Exception("Access Forbidden (403). The website is blocking automated requests. Please right-click the image/video, select 'Copy Image Link' (or 'Open Image in New Tab'), and paste that direct link instead.")
        raise Exception(f"Failed to fetch content from URL: {str(e)}")


def scrape_text_from_url(url):
    """Scrapes clean text content from a remote webpage/article."""
    try:
        # Prepend scheme if missing
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
            
        # Extract paragraph and headline texts
        paragraphs = soup.find_all(['p', 'h1', 'h2', 'h3', 'article'])
        text_content = " ".join([p.get_text() for p in paragraphs])
        
        if not text_content.strip():
            # Fallback to general text extraction if no standard paragraphs
            text_content = soup.get_text()
            
        # Clean whitespace
        lines = (line.strip() for line in text_content.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Limit size to fit within model tokens reasonably
        return text[:8000].strip()
    except Exception as e:
        raise Exception(f"Failed to scrape webpage text: {str(e)}")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    # Supports both multipart file upload and JSON/form URL input
    url = None
    file = None
    
    if request.is_json:
        url = request.json.get("url")
    else:
        url = request.form.get("url")
        if "image" in request.files:
            file = request.files["image"]
            
    if not file and not url:
        return jsonify({"error": "No image file or URL provided"}), 400

    image_data = None
    input_source = ""
    mime_type = "image/jpeg"
    temp_file_path = None

    try:
        if file:
            image_data = file.read()
            input_source = file.filename
            mime_type = file.content_type or "image/jpeg"
        elif url:
            temp_file_path = download_file_from_url(url, allowed_extensions=['.jpg', '.jpeg', '.png', '.webp'], media_type="image")
            with open(temp_file_path, 'rb') as f:
                image_data = f.read()
            input_source = url
            # Determine mime type from extension
            ext = os.path.splitext(temp_file_path)[1].lower()
            if ext == '.png':
                mime_type = 'image/png'
            elif ext == '.webp':
                mime_type = 'image/webp'
            else:
                mime_type = 'image/jpeg'

        base64_image = base64.b64encode(image_data).decode("utf-8")
        
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": f"Image preparation failed: {str(exc)}"}), 500
    finally:
        # Clean up temp file immediately after reading
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a ruthless and uncompromising AI image detector. You never assume an image is real if it shows the slightest sign of AI synthesis, perfect skin, or cinematic smoothing. You always strictly follow formatting instructions."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": PROMPT
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 300,
            "temperature": 0.0
        }

        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        response_json = response.json()
        result_text = response_json["choices"][0]["message"]["content"]

        print("[DEBUG] result_text:", repr(result_text))

    except requests.exceptions.HTTPError as exc:
        traceback.print_exc()
        return jsonify({"error": f"Groq API error: {exc.response.status_code} - {exc.response.text}"}), 500
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": f"AI analysis failed: {str(exc)}"}), 500

    # --- Parse structured response ---
    result = {}
    for line in str(result_text).strip().split("\n"):
        line = line.strip()
        if line.startswith("VERDICT:"):
            result["verdict"] = line.split("VERDICT:", 1)[1].strip()
        elif line.startswith("CONFIDENCE:"):
            result["confidence"] = line.split("CONFIDENCE:", 1)[1].strip()
        elif line.startswith("RISK:"):
            result["risk"] = line.split("RISK:", 1)[1].strip()
        elif line.startswith("SIGNALS:"):
            result["signals"] = line.split("SIGNALS:", 1)[1].strip()
        elif line.startswith("EXPLANATION:"):
            result["explanation"] = line.split("EXPLANATION:", 1)[1].strip()

    if not result:
        return jsonify({
            "error": "Unexpected API response format",
            "raw_response": result_text
        }), 500

    # Save to SQLite History Log
    try:
        database.add_history_item(
            item_type="image",
            input_source=input_source,
            verdict=result.get("verdict", "UNKNOWN"),
            confidence=result.get("confidence", "0"),
            risk=result.get("risk", "LOW"),
            signals=result.get("signals", "None"),
            explanation=result.get("explanation", "")
        )
    except Exception as db_exc:
        print(f"[DATABASE ERROR] Failed to save history: {db_exc}")

    return jsonify(result)


@app.route("/analyze-text", methods=["POST"])
def analyze_text():
    data = request.json
    if not data:
        return jsonify({"error": "No payload provided"}), 400

    text = data.get("text", "")
    url = data.get("url", "")
    
    if not text and not url:
        return jsonify({"error": "No text or URL provided"}), 400

    input_source = "Pasted Text"
    if url:
        try:
            text = scrape_text_from_url(url)
            input_source = url
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    if len(text.strip()) < 50:
        return jsonify({"error": "Text content must be at least 50 characters to detect patterns properly."}), 400

    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        prompt_text = f"""
You are an expert AI text detector. Your task is to rigorously determine if the following text was generated by an AI model (like ChatGPT, Claude, Llama, etc.).

Look very closely for these specific AI signatures:
1. Vocabulary: Overuse of words like "delve", "tapestry", "multifaceted", "moreover", "crucial", "testament", "nuance".
2. Structure: Formulaic logic, symmetrical paragraph lengths, summarizing conclusions ("In conclusion", "Ultimately").
3. Tone: Forced objectivity, overly polite, lacking genuine human emotion, personal quirks, or varied pacing.
4. Hedging: "It's important to consider", "On the other hand", "While it is true that".
5. Lack of human imperfection: Complete absence of colloquialisms, disjointed thoughts, or natural human conversational flow.

Be highly critical. If the text sounds like a generic, polished corporate blog post or an perfectly structured informative essay, it is almost certainly FAKE (AI-generated). Human writing is typically messier, more direct, and less uniform.

Analyze the following text:
"{text}"

Respond ONLY in this exact format (no extra text):
VERDICT: FAKE or REAL
CONFIDENCE: (a number between 0 and 100)
RISK: LOW or MEDIUM or HIGH
SIGNALS: (comma separated list of detected issues, or "None" if real)
EXPLANATION: (one simple sentence explanation)
"""

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a strict and highly accurate AI text detection engine. You always catch AI-generated text and never miss the subtle signs."
                },
                {
                    "role": "user",
                    "content": prompt_text
                }
            ],
            "max_tokens": 300,
            "temperature": 0.0
        }

        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        response_json = response.json()
        result_text = response_json["choices"][0]["message"]["content"]

        print("[DEBUG] text result:", repr(result_text))

    except requests.exceptions.HTTPError as exc:
        traceback.print_exc()
        return jsonify({"error": f"Groq API error: {exc.response.status_code} - {exc.response.text}"}), 500
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": f"AI analysis failed: {str(exc)}"}), 500

    # --- Parse structured response ---
    result = {}
    for line in str(result_text).strip().split("\n"):
        line = line.strip()
        if line.startswith("VERDICT:"):
            result["verdict"] = line.split("VERDICT:", 1)[1].strip()
        elif line.startswith("CONFIDENCE:"):
            result["confidence"] = line.split("CONFIDENCE:", 1)[1].strip()
        elif line.startswith("RISK:"):
            result["risk"] = line.split("RISK:", 1)[1].strip()
        elif line.startswith("SIGNALS:"):
            result["signals"] = line.split("SIGNALS:", 1)[1].strip()
        elif line.startswith("EXPLANATION:"):
            result["explanation"] = line.split("EXPLANATION:", 1)[1].strip()

    if not result:
        return jsonify({
            "error": "Unexpected API response format",
            "raw_response": result_text
        }), 500

    # Save to SQLite History Log
    try:
        snippet = text[:250] + "..." if len(text) > 250 else text
        database.add_history_item(
            item_type="text",
            input_source=input_source,
            verdict=result.get("verdict", "UNKNOWN"),
            confidence=result.get("confidence", "0"),
            risk=result.get("risk", "LOW"),
            signals=result.get("signals", "None"),
            explanation=result.get("explanation", ""),
            details={"text_snippet": snippet}
        )
    except Exception as db_exc:
        print(f"[DATABASE ERROR] Failed to save history: {db_exc}")

    # Return scraped text back so frontend can show what was scanned
    if url:
        result["scraped_text"] = text

    return jsonify(result)


@app.route("/analyze-video", methods=["POST"])
def analyze_video():
    url = None
    file = None
    
    if request.is_json:
        url = request.json.get("url")
    else:
        url = request.form.get("url")
        if "video" in request.files:
            file = request.files["video"]
            
    if not file and not url:
        return jsonify({"error": "No video file or URL provided"}), 400
    
    temp_video_path = None
    input_source = ""
    
    try:
        if file:
            temp_dir = tempfile.gettempdir()
            temp_video_path = os.path.join(temp_dir, "temp_upload.mp4")
            file.save(temp_video_path)
            input_source = file.filename
        elif url:
            temp_video_path = download_file_from_url(url, allowed_extensions=['.mp4', '.avi', '.mov', '.mkv'], media_type="video")
            input_source = url
            
        cap = cv2.VideoCapture(temp_video_path)
        if not cap.isOpened():
            return jsonify({"error": "Failed to open video file. The file might be corrupted or in an unsupported format."}), 500

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Test decode at least the first frame
        ret, frame = cap.read()
        if not ret:
            cap.release()
            return jsonify({"error": "Failed to read video frames. No frames could be decoded. Check if the codec is supported on this machine."}), 500
            
        # Re-seek back to start (or re-open if seek fails)
        if not cap.set(cv2.CAP_PROP_POS_FRAMES, 0):
            cap.release()
            cap = cv2.VideoCapture(temp_video_path)

        # Count frames sequentially if metadata reports empty count
        if total_frames <= 0:
            count = 0
            while True:
                r = cap.grab()
                if not r:
                    break
                count += 1
            total_frames = count
            cap.release()
            cap = cv2.VideoCapture(temp_video_path)

        if total_frames <= 0:
            return jsonify({"error": "Failed to extract any frames. The video file has no readable frames."}), 500

        frames_to_extract = 4
        frame_indices = [int(i * total_frames / frames_to_extract) for i in range(frames_to_extract)]
        
        frame_results_list = []
        fake_frames = 0
        real_frames = 0
        total_conf = 0.0
        
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        # Read sequentially to be extremely robust against seek/keyframe indices issues in OpenCV
        frame_idx = 0
        
        while frame_idx < total_frames and len(frame_results_list) < 4:
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_idx in frame_indices:
                _, buffer = cv2.imencode('.jpg', frame)
                base64_image = base64.b64encode(buffer).decode("utf-8")
                timestamp = round(frame_idx / fps, 1)
                
                payload = {
                    "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a ruthless and uncompromising AI image detector. You never assume an image is real if it shows the slightest sign of AI synthesis, perfect skin, or cinematic smoothing. You always strictly follow formatting instructions."
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": PROMPT},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                            ]
                        }
                    ],
                    "max_tokens": 300,
                    "temperature": 0.0
                }
                
                try:
                    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
                    response.raise_for_status()
                    response_json = response.json()
                    result_text = response_json["choices"][0]["message"]["content"]
                    
                    r_verdict = "REAL"
                    r_conf = 50.0
                    for line in result_text.strip().split("\n"):
                        line = line.strip()
                        if line.startswith("VERDICT:"):
                            r_verdict = line.split("VERDICT:", 1)[1].strip()
                        elif line.startswith("CONFIDENCE:"):
                            try:
                                conf_str = line.split("CONFIDENCE:", 1)[1].strip()
                                r_conf = float(conf_str.replace('%', ''))
                            except:
                                pass
                    
                    frame_results_list.append({
                        "timestamp": timestamp,
                        "verdict": r_verdict,
                        "confidence": r_conf
                    })
                    
                    if "FAKE" in r_verdict.upper():
                        fake_frames += 1
                    else:
                        real_frames += 1
                    
                    total_conf += r_conf
                    
                except Exception as e:
                    print(f"[DEBUG] Frame Error at index {frame_idx}: {str(e)}")
                    # Append a placeholder failure response so the list is not empty
                    frame_results_list.append({
                        "timestamp": timestamp,
                        "verdict": "ERROR",
                        "confidence": 0.0
                    })
                    
            frame_idx += 1

        cap.release()
        
        if len(frame_results_list) == 0:
            return jsonify({"error": "Could not decode or analyze any keyframes successfully."}), 500
        
        avg_conf = round(total_conf / len(frame_results_list), 1)
        final_verdict = "FAKE" if fake_frames > 0 else "REAL"
        risk_level = "HIGH" if final_verdict == "FAKE" else "LOW"
        frames_analyzed = len(frame_results_list)
        
        explanation = f"Analyzed {frames_analyzed} keyframes. Detected {fake_frames} anomalous frames. Overall verdict is {final_verdict}."
        
        # Save to SQLite History Log
        try:
            details = {
                "fake_frames": fake_frames,
                "real_frames": real_frames,
                "total_frames_analyzed": frames_analyzed,
                "frame_results": frame_results_list
            }
            database.add_history_item(
                item_type="video",
                input_source=input_source,
                verdict=final_verdict,
                confidence=avg_conf,
                risk=risk_level,
                signals=f"{fake_frames} of {frames_analyzed} sample frames flagged",
                explanation=explanation,
                details=details
            )
        except Exception as db_exc:
            print(f"[DATABASE ERROR] Failed to save history: {db_exc}")

        return jsonify({
            "verdict": final_verdict,
            "confidence": avg_conf,
            "risk": risk_level,
            "fake_frames": fake_frames,
            "real_frames": real_frames,
            "total_frames_analyzed": frames_analyzed,
            "explanation": explanation,
            "frame_results": frame_results_list
        })

    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": f"Video analysis failed: {str(exc)}"}), 500
    finally:
        if temp_video_path and os.path.exists(temp_video_path):
            try:
                os.remove(temp_video_path)
            except Exception:
                pass


@app.route("/analyze-audio", methods=["POST"])
def analyze_audio():
    url = None
    file = None
    
    if request.is_json:
        url = request.json.get("url")
    else:
        url = request.form.get("url")
        if "audio" in request.files:
            file = request.files["audio"]
            
    if not file and not url:
        return jsonify({"error": "No audio file or URL provided"}), 400

    input_source = ""
    temp_audio_path = None
    
    try:
        if file:
            input_source = file.filename
        elif url:
            temp_audio_path = download_file_from_url(url, allowed_extensions=['.mp3', '.wav', '.m4a', '.mp4'], media_type="audio")
            input_source = url

        result = {
            "verdict": "REAL",
            "confidence": "92",
            "risk": "LOW",
            "transcription": "This is a placeholder transcription of the audio.",
            "signals": "Natural breathing patterns detected.",
            "explanation": f"This is a placeholder response for audio analysis. Analyzed source: {input_source}. No AI generation signatures found."
        }
        
        # Save to SQLite History Log
        try:
            database.add_history_item(
                item_type="audio",
                input_source=input_source,
                verdict=result.get("verdict"),
                confidence=result.get("confidence"),
                risk=result.get("risk"),
                signals=result.get("signals"),
                explanation=result.get("explanation"),
                details={"transcription": result.get("transcription")}
            )
        except Exception as db_exc:
            print(f"[DATABASE ERROR] Failed to save history: {db_exc}")

        return jsonify(result)
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": f"Audio analysis failed: {str(exc)}"}), 500
    finally:
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
            except Exception:
                pass


@app.route("/api/history", methods=["GET"])
def get_history():
    """Retrieves all past analyses from database."""
    try:
        items = database.get_history(limit=50)
        return jsonify(items)
    except Exception as exc:
        return jsonify({"error": f"Failed to retrieve history: {str(exc)}"}), 500


@app.route("/api/history/clear", methods=["POST"])
def clear_history():
    """Clears all records in the history database."""
    try:
        database.clear_history()
        return jsonify({"status": "success", "message": "History cleared successfully"})
    except Exception as exc:
        return jsonify({"error": f"Failed to clear history: {str(exc)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)