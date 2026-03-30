// ─────────────────────────────────────────
// TAB SWITCHING
// ─────────────────────────────────────────
function switchTab(tab) {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));
    document.querySelector(`.tab[onclick="switchTab('${tab}')"]`).classList.add("active");
    document.getElementById(`tab-${tab}`).classList.add("active");
}

// ─────────────────────────────────────────
// SHARED HELPERS
// ─────────────────────────────────────────
function getVerdictClass(verdict) {
    const v = (verdict || "").toUpperCase();
    if (v.includes("FAKE") || v.includes("AI-GENERATED")) return "fake";
    if (v.includes("REAL") || v.includes("HUMAN")) return "real";
    return "suspicious";
}

function buildBaseResult(data) {
    const verdict = data.verdict || "UNKNOWN";
    const confidence = data.confidence ? data.confidence + "%" : "N/A";
    const risk = data.risk || "N/A";
    const signals = data.signals || "None detected";
    const explanation = data.explanation || "No explanation available";
    const cls = getVerdictClass(verdict);

    const emoji = cls === "fake" ? "🔴" : cls === "real" ? "🟢" : "🟡";

    return `
        <div class="result-box">
            <div class="verdict ${cls}">
                <h2>${emoji} ${verdict}</h2>
            </div>
            <div class="details">
                <div class="detail-card">
                    <span>Confidence</span>
                    <strong>${confidence}</strong>
                </div>
                <div class="detail-card">
                    <span>Risk Level</span>
                    <strong>${risk}</strong>
                </div>
            </div>
            <div class="chart-box">
                <h3>Confidence Score</h3>
                <canvas id="confidenceChart_${Date.now()}"></canvas>
            </div>
            <div class="signals-box">
                <h3>Detected Signals</h3>
                <p>${signals}</p>
            </div>
            <div class="explanation-box">
                <h3>Explanation</h3>
                <p>${explanation}</p>
            </div>
        </div>
    `;
}

function renderConfidenceChart(canvasId, confidence, verdict) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const conf = parseFloat(confidence) || 0;
    const cls = getVerdictClass(verdict);
    const color = cls === "fake" ? "#ef4444" : cls === "real" ? "#22c55e" : "#f59e0b";

    new Chart(canvas, {
        type: "doughnut",
        data: {
            datasets: [{
                data: [conf, 100 - conf],
                backgroundColor: [color, "#252540"],
                borderWidth: 0,
                borderRadius: 6,
            }]
        },
        options: {
            cutout: "70%",
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false }
            },
            animation: { animateRotate: true }
        },
        plugins: [{
            id: "centerText",
            beforeDraw(chart) {
                const { ctx, chartArea: { left, top, right, bottom } } = chart;
                const cx = (left + right) / 2;
                const cy = (top + bottom) / 2;
                ctx.save();
                ctx.font = "bold 28px Segoe UI";
                ctx.fillStyle = "#ffffff";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillText(`${Math.round(conf)}%`, cx, cy);
                ctx.restore();
            }
        }]
    });
}

// ─────────────────────────────────────────
// IMAGE DETECTION
// ─────────────────────────────────────────
let selectedFile = null;

const imageInput = document.getElementById("imageInput");
const uploadBox = document.getElementById("uploadBox");
const previewBox = document.getElementById("previewBox");
const previewImage = document.getElementById("previewImage");
const analyzeBtn = document.getElementById("analyzeBtn");

uploadBox.addEventListener("click", () => imageInput.click());

imageInput.addEventListener("change", function (e) {
    const file = e.target.files[0];
    if (!file) return;
    selectedFile = file;
    const reader = new FileReader();
    reader.onload = function (e) {
        previewImage.src = e.target.result;
        previewBox.style.display = "block";
        analyzeBtn.style.display = "block";
        document.getElementById("imageResult").innerHTML = "";
        uploadBox.style.display = "none";
    };
    reader.readAsDataURL(file);
});

uploadBox.addEventListener("dragover", e => {
    e.preventDefault();
    uploadBox.style.borderColor = "#6c63ff";
});
uploadBox.addEventListener("dragleave", () => {
    uploadBox.style.borderColor = "#444466";
});
uploadBox.addEventListener("drop", function (e) {
    e.preventDefault();
    uploadBox.style.borderColor = "#444466";
    const file = e.dataTransfer.files[0];
    if (!file) return;
    selectedFile = file;
    const reader = new FileReader();
    reader.onload = function (e) {
        previewImage.src = e.target.result;
        previewBox.style.display = "block";
        analyzeBtn.style.display = "block";
        document.getElementById("imageResult").innerHTML = "";
        uploadBox.style.display = "none";
    };
    reader.readAsDataURL(file);
});

function analyzeImage() {
    if (!selectedFile) return alert("Please upload an image first");
    analyzeBtn.style.display = "none";
    document.getElementById("imageLoading").style.display = "block";
    document.getElementById("imageResult").innerHTML = "";

    const formData = new FormData();
    formData.append("image", selectedFile);

    fetch("/analyze", { method: "POST", body: formData })
        .then(r => r.json())
        .then(data => {
            document.getElementById("imageLoading").style.display = "none";
            if (data.error) {
                document.getElementById("imageResult").innerHTML = `<div class="explanation-box"><p style="color:#ef4444">Error: ${data.error}</p></div>`;
                analyzeBtn.style.display = "block";
                return;
            }
            const chartId = `chart_${Date.now()}`;
            const html = buildBaseResult(data).replace('id="confidenceChart_', `id="${chartId}`);
            // Fix: replace the dynamic id properly
            document.getElementById("imageResult").innerHTML = buildBaseResult(data);
            // find the canvas and render
            const canvas = document.getElementById("imageResult").querySelector("canvas");
            if (canvas) renderConfidenceChart(canvas.id, data.confidence, data.verdict);
            // add reset
            document.getElementById("imageResult").innerHTML += `<button class="reset-btn" onclick="resetImage()">🔄 Analyze Another Image</button>`;
        })
        .catch(err => {
            document.getElementById("imageLoading").style.display = "none";
            alert("Error: " + err.message);
            analyzeBtn.style.display = "block";
        });
}

function resetImage() {
    selectedFile = null;
    imageInput.value = "";
    previewBox.style.display = "none";
    analyzeBtn.style.display = "none";
    document.getElementById("imageResult").innerHTML = "";
    uploadBox.style.display = "block";
}

// ─────────────────────────────────────────
// VIDEO DETECTION
// ─────────────────────────────────────────
let selectedVideo = null;

const videoInput = document.getElementById("videoInput");
const videoUploadBox = document.getElementById("videoUploadBox");
const videoPreviewBox = document.getElementById("videoPreviewBox");
const videoPreview = document.getElementById("videoPreview");
const videoAnalyzeBtn = document.getElementById("videoAnalyzeBtn");

videoUploadBox.addEventListener("click", () => videoInput.click());

videoInput.addEventListener("change", function (e) {
    const file = e.target.files[0];
    if (!file) return;
    selectedVideo = file;
    const url = URL.createObjectURL(file);
    videoPreview.src = url;
    videoPreviewBox.style.display = "block";
    videoAnalyzeBtn.style.display = "block";
    document.getElementById("videoResult").innerHTML = "";
    videoUploadBox.style.display = "none";
});

function analyzeVideo() {
    if (!selectedVideo) return alert("Please upload a video first");
    videoAnalyzeBtn.style.display = "none";
    document.getElementById("videoLoading").style.display = "block";
    document.getElementById("videoResult").innerHTML = "";

    const formData = new FormData();
    formData.append("video", selectedVideo);

    fetch("/analyze-video", { method: "POST", body: formData })
        .then(r => r.json())
        .then(data => {
            document.getElementById("videoLoading").style.display = "none";
            if (data.error) {
                document.getElementById("videoResult").innerHTML = `<div class="explanation-box"><p style="color:#ef4444">Error: ${data.error}</p></div>`;
                videoAnalyzeBtn.style.display = "block";
                return;
            }

            const cls = getVerdictClass(data.verdict);
            const emoji = cls === "fake" ? "🔴" : "🟢";

            let framesHTML = "";
            if (data.frame_results && data.frame_results.length > 0) {
                framesHTML = data.frame_results.map(f => {
                    const fc = getVerdictClass(f.verdict);
                    const conf = parseFloat(f.confidence) || 0;
                    return `
                        <div class="frame-item">
                            <span class="frame-time">${f.timestamp}s</span>
                            <span class="frame-verdict ${fc}">${f.verdict}</span>
                            <div class="frame-bar-wrap">
                                <div class="frame-bar ${fc}" style="width:${conf}%"></div>
                            </div>
                            <span class="frame-conf">${Math.round(conf)}%</span>
                        </div>
                    `;
                }).join("");
            }

            // Build chart data for timeline
            const labels = (data.frame_results || []).map(f => `${f.timestamp}s`);
            const confs = (data.frame_results || []).map(f => parseFloat(f.confidence) || 0);
            const colors = (data.frame_results || []).map(f => getVerdictClass(f.verdict) === "fake" ? "#ef4444" : "#22c55e");

            const chartCanvasId = `videoChart_${Date.now()}`;

            document.getElementById("videoResult").innerHTML = `
                <div class="result-box">
                    <div class="verdict ${cls}">
                        <h2>${emoji} ${data.verdict}</h2>
                    </div>
                    <div class="video-stats">
                        <div class="stat-card"><span>Confidence</span><strong>${data.confidence}%</strong></div>
                        <div class="stat-card"><span>Risk</span><strong>${data.risk}</strong></div>
                        <div class="stat-card"><span>Fake Frames</span><strong style="color:#ef4444">${data.fake_frames}</strong></div>
                        <div class="stat-card"><span>Real Frames</span><strong style="color:#22c55e">${data.real_frames}</strong></div>
                    </div>
                    <div class="chart-box">
                        <h3>Frame-by-Frame Confidence Timeline</h3>
                        <canvas id="${chartCanvasId}"></canvas>
                    </div>
                    <div class="frame-timeline">
                        <h3>Frame Analysis (${data.total_frames_analyzed} frames sampled)</h3>
                        ${framesHTML}
                    </div>
                    <div class="explanation-box">
                        <h3>Summary</h3>
                        <p>${data.explanation}</p>
                    </div>
                    <button class="reset-btn" onclick="resetVideo()">🔄 Analyze Another Video</button>
                </div>
            `;

            // Render timeline chart
            const canvas = document.getElementById(chartCanvasId);
            if (canvas && labels.length > 0) {
                new Chart(canvas, {
                    type: "bar",
                    data: {
                        labels: labels,
                        datasets: [{
                            label: "Confidence %",
                            data: confs,
                            backgroundColor: colors,
                            borderRadius: 6,
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: { legend: { display: false } },
                        scales: {
                            y: {
                                min: 0, max: 100,
                                ticks: { color: "#888888" },
                                grid: { color: "#252540" }
                            },
                            x: {
                                ticks: { color: "#888888" },
                                grid: { display: false }
                            }
                        }
                    }
                });
            }
        })
        .catch(err => {
            document.getElementById("videoLoading").style.display = "none";
            alert("Error: " + err.message);
            videoAnalyzeBtn.style.display = "block";
        });
}

function resetVideo() {
    selectedVideo = null;
    videoInput.value = "";
    videoPreviewBox.style.display = "none";
    videoAnalyzeBtn.style.display = "none";
    document.getElementById("videoResult").innerHTML = "";
    videoUploadBox.style.display = "block";
}

// ─────────────────────────────────────────
// AUDIO DETECTION
// ─────────────────────────────────────────
let selectedAudio = null;

const audioInput = document.getElementById("audioInput");
const audioUploadBox = document.getElementById("audioUploadBox");
const audioPreviewBox = document.getElementById("audioPreviewBox");
const audioPreview = document.getElementById("audioPreview");
const audioAnalyzeBtn = document.getElementById("audioAnalyzeBtn");

audioUploadBox.addEventListener("click", () => audioInput.click());

audioInput.addEventListener("change", function (e) {
    const file = e.target.files[0];
    if (!file) return;
    selectedAudio = file;
    const url = URL.createObjectURL(file);
    audioPreview.src = url;
    audioPreviewBox.style.display = "block";
    audioAnalyzeBtn.style.display = "block";
    document.getElementById("audioResult").innerHTML = "";
    audioUploadBox.style.display = "none";
});

function analyzeAudio() {
    if (!selectedAudio) return alert("Please upload an audio file first");
    audioAnalyzeBtn.style.display = "none";
    document.getElementById("audioLoading").style.display = "block";
    document.getElementById("audioResult").innerHTML = "";

    const formData = new FormData();
    formData.append("audio", selectedAudio);

    fetch("/analyze-audio", { method: "POST", body: formData })
        .then(r => r.json())
        .then(data => {
            document.getElementById("audioLoading").style.display = "none";
            if (data.error) {
                document.getElementById("audioResult").innerHTML = `<div class="explanation-box"><p style="color:#ef4444">Error: ${data.error}</p></div>`;
                audioAnalyzeBtn.style.display = "block";
                return;
            }

            const cls = getVerdictClass(data.verdict);
            const emoji = cls === "fake" ? "🔴" : "🟢";
            const chartCanvasId = `audioChart_${Date.now()}`;
            const conf = parseFloat(data.confidence) || 0;
            const color = cls === "fake" ? "#ef4444" : "#22c55e";

            document.getElementById("audioResult").innerHTML = `
                <div class="result-box">
                    <div class="verdict ${cls}">
                        <h2>${emoji} ${data.verdict}</h2>
                    </div>
                    <div class="details">
                        <div class="detail-card"><span>Confidence</span><strong>${data.confidence}%</strong></div>
                        <div class="detail-card"><span>Risk Level</span><strong>${data.risk}</strong></div>
                    </div>
                    <div class="chart-box">
                        <h3>Confidence Score</h3>
                        <canvas id="${chartCanvasId}"></canvas>
                    </div>
                    <div class="transcription-box">
                        <h3>Transcription</h3>
                        <p>${data.transcription || "No transcription available"}</p>
                    </div>
                    <div class="signals-box">
                        <h3>Detected Signals</h3>
                        <p>${data.signals || "None"}</p>
                    </div>
                    <div class="explanation-box">
                        <h3>Explanation</h3>
                        <p>${data.explanation || ""}</p>
                    </div>
                    <button class="reset-btn" onclick="resetAudio()">🔄 Analyze Another Audio</button>
                </div>
            `;
            renderConfidenceChart(chartCanvasId, data.confidence, data.verdict);
        })
        .catch(err => {
            document.getElementById("audioLoading").style.display = "none";
            alert("Error: " + err.message);
            audioAnalyzeBtn.style.display = "block";
        });
}

function resetAudio() {
    selectedAudio = null;
    audioInput.value = "";
    audioPreviewBox.style.display = "none";
    audioAnalyzeBtn.style.display = "none";
    document.getElementById("audioResult").innerHTML = "";
    audioUploadBox.style.display = "block";
}

// ─────────────────────────────────────────
// TEXT DETECTION
// ─────────────────────────────────────────
const textInput = document.getElementById("textInput");
const charCount = document.getElementById("charCount");

textInput.addEventListener("input", () => {
    charCount.textContent = `${textInput.value.length} characters`;
});

function analyzeText() {
    const text = textInput.value.trim();
    if (text.length < 50) return alert("Please enter at least 50 characters.");

    document.getElementById("textLoading").style.display = "block";
    document.getElementById("textResult").innerHTML = "";

    fetch("/analyze-text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
    })
        .then(r => r.json())
        .then(data => {
            document.getElementById("textLoading").style.display = "none";
            if (data.error) {
                document.getElementById("textResult").innerHTML = `<div class="explanation-box"><p style="color:#ef4444">Error: ${data.error}</p></div>`;
                return;
            }

            const cls = getVerdictClass(data.verdict);
            const emoji = cls === "fake" ? "🔴" : "🟢";
            const chartCanvasId = `textChart_${Date.now()}`;

            document.getElementById("textResult").innerHTML = `
                <div class="result-box" style="margin-top:20px;">
                    <div class="verdict ${cls}">
                        <h2>${emoji} ${data.verdict}</h2>
                    </div>
                    <div class="details">
                        <div class="detail-card"><span>Confidence</span><strong>${data.confidence}%</strong></div>
                        <div class="detail-card"><span>Risk Level</span><strong>${data.risk}</strong></div>
                    </div>
                    <div class="chart-box">
                        <h3>Confidence Score</h3>
                        <canvas id="${chartCanvasId}"></canvas>
                    </div>
                    <div class="signals-box">
                        <h3>Detected Patterns</h3>
                        <p>${data.signals || "None"}</p>
                    </div>
                    <div class="explanation-box">
                        <h3>Explanation</h3>
                        <p>${data.explanation || ""}</p>
                    </div>
                    <button class="reset-btn" onclick="resetText()">🔄 Analyze Another Text</button>
                </div>
            `;
            renderConfidenceChart(chartCanvasId, data.confidence, data.verdict);
        })
        .catch(err => {
            document.getElementById("textLoading").style.display = "none";
            alert("Error: " + err.message);
        });
}

function resetText() {
    textInput.value = "";
    charCount.textContent = "0 characters";
    document.getElementById("textResult").innerHTML = "";
}