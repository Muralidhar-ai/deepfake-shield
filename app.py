from flask import Flask, render_template, request, jsonify
import base64
import os
import warnings
import traceback

# suppress the deprecation warning from google.generativeai until upgrade
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")

app = Flask(__name__)

# use environment variable API key (required)
API_KEY = os.getenv("GENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("GENAI_API_KEY environment variable is required. Set it with: setx GENAI_API_KEY \"AIzaSyDtzKpLXL31QZZxhLLQn3QBWumGO6obUPo\"")

model_name = "gemini-1.5-flash"
use_new_genai = False
client = None
model = None

try:
    from google.genai import Client
    client = Client(api_key=API_KEY)
    use_new_genai = True
except ModuleNotFoundError:
    import google.generativeai as genai
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel(model_name)
except Exception:
    import google.generativeai as genai
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel(model_name)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"})

    file = request.files["image"]
    image_data = file.read()
    base64_image = base64.b64encode(image_data).decode("utf-8")
    mime_type = file.content_type

    prompt = """
    Analyze this image carefully for signs of AI generation or deepfake manipulation.

    Check for these signals:
    - Unnatural skin texture or smoothness
    - Eye anomalies (missing reflections, unnatural gaze)
    - Lighting inconsistencies on the face
    - Background blurring or warping artifacts
    - Facial symmetry issues
    - Unnatural teeth or hair patterns

    Respond ONLY in this exact format:
    VERDICT: REAL or FAKE
    CONFIDENCE: (a number between 0 and 100)
    RISK: LOW or MEDIUM or HIGH
    SIGNALS: (comma separated list of detected issues, or "None" if real)
    EXPLANATION: (one simple sentence explanation)
    """

    try:
        if use_new_genai:
            # google.genai expects structured content dicts, not raw text/image combination.
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image",
                        "image": {
                            "mime_type": mime_type,
                            "data": base64_image
                        }
                    }
                ]
            )
        else:
            # legacy google.generativeai supports this format directly.
            response = model.generate_content([
                prompt,
                {
                    "mime_type": mime_type,
                    "data": base64_image
                }
            ])

        # parse response text for both SDKs
        result_text = None

        # google.genai response: may include candidates or output
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and candidate.content is not None:
                result_text = candidate.content
            elif hasattr(candidate, 'text'):
                result_text = candidate.text

        # old google.generativeai response or fallback
        if result_text is None:
            result_text = getattr(response, 'text', None)
        if result_text is None:
            result_text = getattr(response, 'output', None)

        # last fallback
        if result_text is None:
            result_text = str(response)

        if isinstance(result_text, (list, tuple)):
            result_text = "\n".join(str(r) for r in result_text)

        print("[DEBUG] API result_text:", repr(result_text))

        lines = str(result_text).strip().split("\n")
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": f"AI analysis failed: {str(exc)}"}), 500

    result = {}
    for line in lines:
        if "VERDICT:" in line:
            result["verdict"] = line.split("VERDICT:")[1].strip()
        elif "CONFIDENCE:" in line:
            result["confidence"] = line.split("CONFIDENCE:")[1].strip()
        elif "RISK:" in line:
            result["risk"] = line.split("RISK:")[1].strip()
        elif "SIGNALS:" in line:
            result["signals"] = line.split("SIGNALS:")[1].strip()
        elif "EXPLANATION:" in line:
            result["explanation"] = line.split("EXPLANATION:")[1].strip()

    if not result:
        return jsonify({
            "error": "API response did not include expected keys",
            "raw_response": result_text
        }), 500

    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True)