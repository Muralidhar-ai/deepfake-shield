let selectedFile = null;

const imageInput = document.getElementById("imageInput");
const uploadBox = document.getElementById("uploadBox");
const previewBox = document.getElementById("previewBox");
const previewImage = document.getElementById("previewImage");
const analyzeBtn = document.getElementById("analyzeBtn");
const resultBox = document.getElementById("resultBox");
const loading = document.getElementById("loading");

uploadBox.addEventListener("click", function() {
    imageInput.click();
});

imageInput.addEventListener("change", function(e) {
    const file = e.target.files[0];

    if (!file) {
        return;
    }

    selectedFile = file;

    const reader = new FileReader();

    reader.onload = function(e) {
        previewImage.src = e.target.result;
        previewBox.style.display = "block";
        analyzeBtn.style.display = "block";
        resultBox.style.display = "none";
        uploadBox.style.display = "none";
    };

    reader.readAsDataURL(file);
});

uploadBox.addEventListener("dragover", function(e) {
    e.preventDefault();
    uploadBox.style.borderColor = "#6c63ff";
});

uploadBox.addEventListener("dragleave", function() {
    uploadBox.style.borderColor = "#444466";
});

uploadBox.addEventListener("drop", function(e) {
    e.preventDefault();
    uploadBox.style.borderColor = "#444466";
    const file = e.dataTransfer.files[0];

    if (!file) {
        return;
    }

    selectedFile = file;

    const reader = new FileReader();

    reader.onload = function(e) {
        previewImage.src = e.target.result;
        previewBox.style.display = "block";
        analyzeBtn.style.display = "block";
        resultBox.style.display = "none";
        uploadBox.style.display = "none";
    };

    reader.readAsDataURL(file);
});

function analyzeImage() {
    if (!selectedFile) {
        alert("Please upload an image first");
        return;
    }

    analyzeBtn.style.display = "none";
    loading.style.display = "block";
    resultBox.style.display = "none";

    const formData = new FormData();
    formData.append("image", selectedFile);

    console.log('Sending /analyze', selectedFile);

    fetch("/analyze", {
        method: "POST",
        body: formData
    })
    .then(async response => {
        const text = await response.text();
        let data;
        try {
            data = JSON.parse(text);
        } catch (e) {
            throw new Error('Non-JSON reply: ' + text);
        }
        if (!response.ok) {
            throw new Error(data.error || 'HTTP ' + response.status + ' ' + response.statusText);
        }
        return data;
    })
    .then(data => {
        loading.style.display = "none";

        if (data.error) {
            alert("Error: " + data.error);
            document.getElementById("verdictText").textContent = "Error";
            document.getElementById("explanationText").textContent = data.error;
            resultBox.style.display = "block";
            return;
        }

        const verdict = data.verdict ? data.verdict.toUpperCase() : "UNKNOWN";
        const confidence = data.confidence ? data.confidence + "%" : "N/A";
        const risk = data.risk ? data.risk : "N/A";
        const signals = data.signals ? data.signals : "None detected";
        const explanation = data.explanation ? data.explanation : "No explanation available";

        document.getElementById("verdictText").textContent = verdict === "FAKE" ? "🔴 FAKE" : "🟢 REAL";

        const verdictBox = document.getElementById("verdictBox");
        verdictBox.className = "verdict";

        if (verdict === "FAKE") {
            verdictBox.classList.add("fake");
        } else if (verdict === "REAL") {
            verdictBox.classList.add("real");
        } else {
            verdictBox.classList.add("suspicious");
        }

        document.getElementById("confidenceText").textContent = confidence;
        document.getElementById("riskText").textContent = risk;
        document.getElementById("signalsText").textContent = signals;
        document.getElementById("explanationText").textContent = explanation;

        resultBox.style.display = "block";
    })
    .catch(error => {
        loading.style.display = "none";
        console.error(error);
        const message = error?.message || (error?.toString ? error.toString() : "Unknown error");
        alert("Something went wrong: " + message);
        document.getElementById("verdictText").textContent = "Error";
        document.getElementById("explanationText").textContent = message;
        resultBox.style.display = "block";
    });
}

function resetApp() {
    selectedFile = null;
    imageInput.value = "";
    previewBox.style.display = "none";
    analyzeBtn.style.display = "none";
    resultBox.style.display = "none";
    uploadBox.style.display = "block";
}
