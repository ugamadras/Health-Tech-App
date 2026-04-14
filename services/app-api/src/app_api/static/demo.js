const form = document.getElementById("meal-form");
const imageFileInput = document.getElementById("image-file");
const dropzone = document.getElementById("dropzone");
const fileName = document.getElementById("file-name");
const analyzeButton = document.getElementById("analyze-button");
const apiStatus = document.getElementById("api-status");
const modelStatus = document.getElementById("model-status");
const messagePanel = document.getElementById("message-panel");
const resultPanel = document.getElementById("result-panel");
const metricCalories = document.getElementById("metric-calories");
const metricProtein = document.getElementById("metric-protein");
const metricCarbs = document.getElementById("metric-carbs");
const metricFat = document.getElementById("metric-fat");
const mealItems = document.getElementById("meal-items");
const insights = document.getElementById("insights");
const disclaimerText = document.getElementById("disclaimer-text");
const questionForm = document.getElementById("question-form");
const questionInput = document.getElementById("question-input");
const qaAnswer = document.getElementById("qa-answer");

let currentMealId = null;
let currentDisclaimer = "";

function formatNumber(value, suffix = "") {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "--";
  }
  return `${Number(value).toFixed(1).replace(/\.0$/, "")}${suffix}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setMessage(text, variant = "") {
  messagePanel.textContent = text;
  messagePanel.className = "card";
  if (variant) {
    messagePanel.classList.add(variant);
  }
  messagePanel.classList.remove("hidden");
}

function clearMessage() {
  messagePanel.textContent = "";
  messagePanel.className = "card hidden";
}

function resetResultView() {
  resultPanel.classList.add("hidden");
  qaAnswer.classList.add("hidden");
  qaAnswer.innerHTML = "";
  currentMealId = null;
  currentDisclaimer = "";
}

function renderSummary(analysis) {
  const totals = analysis?.nutrition_summary?.totals || {};
  metricCalories.textContent = formatNumber(totals.calories);
  metricProtein.textContent = formatNumber(totals.protein_g, " g");
  metricCarbs.textContent = formatNumber(totals.carbs_g, " g");
  metricFat.textContent = formatNumber(totals.fat_g, " g");
}

function renderMealItems(items) {
  if (!items?.length) {
    mealItems.innerHTML =
      '<div class="item"><p><strong>No items were confidently identified.</strong></p><p>Try a clearer photo with the full plate visible.</p></div>';
    return;
  }

  mealItems.innerHTML = items
    .map((item) => {
      const details = [];
      if (item.item_count !== null && item.item_count !== undefined) {
        details.push(`Estimated count: ${item.item_count}`);
      }
      if (item.estimated_portion_description) {
        details.push(`Estimated portion: ${item.estimated_portion_description}`);
      } else if (item.estimated_amount !== null && item.estimated_amount !== undefined && item.estimated_unit) {
        details.push(`Estimated portion: ${formatNumber(item.estimated_amount)} ${item.estimated_unit}`);
      }
      if (item.notes) {
        details.push(item.notes);
      }
      return `
        <article class="item">
          <p><strong>${escapeHtml(item.label || "Unnamed item")}</strong></p>
          ${details.map((entry) => `<p>${escapeHtml(entry)}</p>`).join("")}
        </article>
      `;
    })
    .join("");
}

function renderInsights(analysis) {
  const items = analysis?.nutrition_summary?.insights || [];
  if (!items.length) {
    insights.innerHTML = "<li>No additional nutrition insights were returned.</li>";
    return;
  }
  insights.innerHTML = items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function renderDisclaimer(analysis, fallbackDisclaimer) {
  const disclaimer = analysis?.nutrition_summary?.disclaimer || fallbackDisclaimer || "";
  currentDisclaimer = disclaimer;
  disclaimerText.textContent = disclaimer;
}

function explainBlockedFlow(data) {
  const moderationFlags = data?.validation?.moderation_flags || [];
  const relevance = data?.validation?.food_relevance || "uncertain";

  if (moderationFlags.length) {
    return "This upload could not be analyzed because it did not pass safety checks. Please upload a different image.";
  }
  if (relevance === "non_food") {
    return "This image appears to be non-food content. Please upload a meal photo.";
  }
  return "We could not confidently identify meal items from this image. Please try another photo with better lighting and a clearer view of the plate.";
}

async function toBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result || "";
      resolve(String(result).split(",")[1] || "");
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function loadStatus() {
  const response = await fetch("/");
  const data = await response.json();
  apiStatus.textContent = `API: ${data.status || "unknown"}`;
  if (data.openai_responses_enabled) {
    modelStatus.textContent = "Model pipeline: enabled";
    modelStatus.classList.remove("pill-muted");
  } else {
    modelStatus.textContent = "Model pipeline: unavailable";
    modelStatus.classList.add("pill-muted");
  }
}

function bindDropzone() {
  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.add("drag-active");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.remove("drag-active");
    });
  });

  dropzone.addEventListener("drop", (event) => {
    const dropped = event.dataTransfer?.files?.[0];
    if (!dropped) {
      return;
    }
    const transfer = new DataTransfer();
    transfer.items.add(dropped);
    imageFileInput.files = transfer.files;
    fileName.textContent = dropped.name;
  });

  imageFileInput.addEventListener("change", () => {
    const file = imageFileInput.files?.[0];
    fileName.textContent = file ? file.name : "PNG, JPG, or HEIC";
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = imageFileInput.files?.[0];
  if (!file) {
    setMessage("Please upload a meal photo before analyzing.", "warning");
    return;
  }

  clearMessage();
  resetResultView();
  analyzeButton.disabled = true;
  analyzeButton.textContent = "Analyzing...";

  try {
    const payload = {
      filename: file.name,
      mime_type: file.type || "image/jpeg",
      size_bytes: file.size || 1,
      image_base64: await toBase64(file),
    };

    const response = await fetch("/meals", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-user-id": "web-demo-user",
      },
      body: JSON.stringify(payload),
    });

    const rawText = await response.text();
    let data = {};
    try {
      data = rawText ? JSON.parse(rawText) : {};
    } catch {
      data = { error: rawText || "Unexpected server response." };
    }

    if (!response.ok) {
      setMessage(data.detail || data.error || "We could not process this image right now.", "error");
      return;
    }

    const analysis = data.analysis;
    if (!analysis) {
      setMessage(explainBlockedFlow(data), "warning");
      return;
    }

    currentMealId = data.meal_id || null;
    renderSummary(analysis);
    renderMealItems(analysis.meal_items || []);
    renderInsights(analysis);
    renderDisclaimer(analysis, data.disclaimer || "");
    resultPanel.classList.remove("hidden");
    setMessage("Analysis complete. You can now ask follow-up questions about this meal.");
  } catch (error) {
    setMessage(error instanceof Error ? error.message : "Unexpected error while analyzing image.", "error");
  } finally {
    analyzeButton.disabled = false;
    analyzeButton.textContent = "Analyze Meal";
  }
});

questionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();

  if (!currentMealId) {
    setMessage("Analyze a meal first, then ask a follow-up question.", "warning");
    return;
  }
  if (!question) {
    setMessage("Enter a question about the meal insights.", "warning");
    return;
  }

  qaAnswer.classList.remove("hidden");
  qaAnswer.innerHTML = "<p><strong>Answer</strong></p><p>Thinking...</p>";

  try {
    const response = await fetch(`/meals/${currentMealId}/questions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const rawText = await response.text();
    let data = {};
    try {
      data = rawText ? JSON.parse(rawText) : {};
    } catch {
      data = { error: rawText || "Unexpected server response." };
    }

    if (!response.ok) {
      qaAnswer.innerHTML = `<p><strong>Answer</strong></p><p>${escapeHtml(
        data.detail || data.error || "We could not answer that question right now."
      )}</p>`;
      return;
    }

    const answer = String(data.answer || "").trim();
    const disclaimer = data.disclaimer || currentDisclaimer;
    const marker = "Disclaimer:";
    const splitAt = answer.indexOf(marker);
    const body = splitAt >= 0 ? answer.slice(0, splitAt).trim() : answer;
    const paragraphs = body
      .split(/\n{2,}/)
      .map((part) => part.trim())
      .filter(Boolean);

    qaAnswer.innerHTML = `
      <p><strong>Answer</strong></p>
      ${paragraphs.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("")}
      <div class="qa-disclaimer">
        <p><strong>Disclaimer</strong></p>
        <p>${escapeHtml(disclaimer)}</p>
      </div>
    `;
  } catch (error) {
    qaAnswer.innerHTML = `<p><strong>Answer</strong></p><p>${escapeHtml(
      error instanceof Error ? error.message : "Unexpected error."
    )}</p>`;
  }
});

bindDropzone();
loadStatus().catch(() => {
  apiStatus.textContent = "API: unavailable";
  modelStatus.textContent = "Model pipeline: unavailable";
});
