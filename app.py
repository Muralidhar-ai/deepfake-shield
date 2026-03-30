from flask import Flask, render_template, request, jsonify
import base64
import os
import traceback
import requests
import cv2

app = Flask(__name__)

# --- API Key Setup ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "your_groq_api_key_here")

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


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    image_data = file.read()
    base64_image = base64.b64encode(image_data).decode("utf-8")
    mime_type = file.content_type or "image/jpeg"

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

    return jsonify(result)


@app.route("/analyze-text", methods=["POST"])
def analyze_text():
    data = request.json
    if not data or "text" not in data:
        return jsonify({"error": "No text provided"}), 400

    text = data.get("text", "")

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
            "model": "llama-3.3-70b-versatile",  # Stronger model for better reasoning and text classification
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

    return jsonify(result)


@app.route("/analyze-video", methods=["POST"])
def analyze_video():
    if "video" not in request.files:
        return jsonify({"error": "No video uploaded"}), 400
    
    video_file = request.files["video"]
    
    import tempfile
    temp_dir = tempfile.gettempdir()
    temp_video_path = os.path.join(temp_dir, "temp_upload.mp4")
    video_file.save(temp_video_path)
    
    try:
        cap = cv2.VideoCapture(temp_video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            return jsonify({"error": "Failed to read video frames"}), 500
        
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

        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                continue
                
            _, buffer = cv2.imencode('.jpg', frame)
            base64_image = base64.b64encode(buffer).decode("utf-8")
            timestamp = round(idx / fps, 1)
            
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
                print(f"[DEBUG] Frame Error: {str(e)}")
                continue

        cap.release()
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)

        if len(frame_results_list) == 0:
            return jsonify({"error": "Could not analyze any frames."}), 500
        
        avg_conf = round(total_conf / len(frame_results_list), 1)
        final_verdict = "FAKE" if fake_frames > 0 else "REAL"
        risk_level = "HIGH" if final_verdict == "FAKE" else "LOW"
        frames_analyzed = len(frame_results_list)
        
        explanation = f"Analyzed {frames_analyzed} keyframes. Detected {fake_frames} anomalous frames. Overall verdict is {final_verdict}."
        
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
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        return jsonify({"error": f"Video analysis failed: {str(exc)}"}), 500


@app.route("/analyze-audio", methods=["POST"])
def analyze_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No audio uploaded"}), 400

    # Placeholder for actual audio analysis
    return jsonify({
        "verdict": "REAL",
        "confidence": "92",
        "risk": "LOW",
        "transcription": "This is a placeholder transcription of the audio.",
        "signals": "Natural breathing patterns detected.",
        "explanation": "This is a placeholder response for audio analysis. No AI generation signatures found."
    })


if __name__ == "__main__":
    app.run(debug=True)