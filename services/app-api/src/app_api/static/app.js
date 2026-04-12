const form = document.getElementById("meal-form");
const questionForm = document.getElementById("question-form");
const questionInput = document.getElementById("question-input");
const questionAnswer = document.getElementById("question-answer");
const imageFileInput = document.getElementById("image-file");
const resultPanel = document.getElementById("result-panel");
const resultStatus = document.getElementById("result-status");
const resultMessage = document.getElementById("result-message");
const analysisView = document.getElementById("analysis-view");
const moderationSummary = document.getElementById("moderation-summary");
const observerSummary = document.getElementById("observer-summary");
const inferenceSummary = document.getElementById("inference-summary");
const outputReviewSummary = document.getElementById("output-review-summary");
const detectedComponents = document.getElementById("detected-components");
const nutritionSummary = document.getElementById("nutrition-summary");
const nutritionInsights = document.getElementById("nutrition-insights");
const nutritionDisclaimer = document.getElementById("nutrition-disclaimer");
const mealItems = document.getElementById("meal-items");
const validationDetails = document.getElementById("validation-details");
const moderationJson = document.getElementById("moderation-json");
const observerJson = document.getElementById("observer-json");
const resultJson = document.getElementById("result-json");
const outputReviewJson = document.getElementById("output-review-json");
const apiStatus = document.getElementById("api-status");
const openaiStatus = document.getElementById("openai-status");
const modeBanner = document.getElementById("mode-banner");
let currentMealId = null;
let currentAnalysis = null;

async function loadStatus() {
  const response = await fetch("/");
  const data = await response.json();
  apiStatus.textContent = `API: ${data.status}`;
  if (data.openai_responses_enabled) {
    openaiStatus.textContent = "Image analysis: OpenAI enabled";
    modeBanner.className = "banner banner-success";
    modeBanner.textContent =
      "OpenAI image analysis is enabled. The app runs moderation first, then a low-cost food observer, then detailed meal-item inference only for likely food images.";
    modeBanner.classList.remove("hidden");
  } else {
    openaiStatus.textContent = "Image analysis: unavailable";
    modeBanner.className = "banner banner-warning";
    modeBanner.textContent =
      "OpenAI image analysis is currently disabled. Start the app with OPENAI_API_KEY set to inspect uploaded images.";
    modeBanner.classList.remove("hidden");
  }
}

function toBase64(file) {
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

function renderRows(container, rows) {
  container.innerHTML = rows
    .map(
      (row) => `
        <div class="data-row">
          <span class="data-label">${row.label}</span>
          <span class="data-value">${row.value}</span>
        </div>
      `
    )
    .join("");
}

function renderDetectedComponents(items) {
  detectedComponents.innerHTML = items.length
    ? items
        .map(
          (item) => `
            <article class="item-card">
              <p class="item-title">${item}</p>
              <p class="item-meta">Visible food item inferred by the model.</p>
            </article>
          `
        )
        .join("")
    : `
      <article class="item-card">
        <p class="item-title">No inferred items yet</p>
        <p class="item-meta">Try a clearer image with the full plate visible.</p>
      </article>
    `;
}

function renderMealItems(items) {
  mealItems.innerHTML = items.length
    ? items
        .map((item) => {
          const parts = [];
          if (item.confidence !== undefined) {
            parts.push(`Confidence: ${item.confidence}`);
          }
          if (item.item_count !== undefined && item.item_count !== null) {
            const countConfidence = item.item_count_confidence ? ` (${item.item_count_confidence} confidence)` : "";
            parts.push(`Estimated count: ${item.item_count}${countConfidence}`);
          }
          if (item.estimated_portion_description) {
            parts.push(`Estimated portion: ${item.estimated_portion_description}`);
          } else if (item.estimated_amount !== undefined && item.estimated_amount !== null && item.estimated_unit) {
            parts.push(`Estimated portion: ${item.estimated_amount} ${item.estimated_unit}`);
          }
          if (item.portion_confidence) {
            parts.push(`Portion confidence: ${item.portion_confidence}`);
          }
          if (item.notes) {
            parts.push(item.notes);
          }
          const usda = item.usda_match;
          const usdaHtml = usda
            ? `
              <div class="usda-match">
                <p class="item-meta"><strong>USDA match:</strong> ${usda.description || "Unknown food"}</p>
                <p class="item-meta"><strong>FDC ID:</strong> ${usda.fdc_id || "--"}</p>
                <p class="item-meta"><strong>Type:</strong> ${usda.data_type || "--"}</p>
                <p class="item-meta"><strong>Calories:</strong> ${usda.nutrients?.calories ?? "--"}</p>
                <p class="item-meta"><strong>Protein:</strong> ${usda.nutrients?.protein_g ?? "--"} g</p>
                <p class="item-meta"><strong>Carbs:</strong> ${usda.nutrients?.carbs_g ?? "--"} g</p>
                <p class="item-meta"><strong>Fat:</strong> ${usda.nutrients?.fat_g ?? "--"} g</p>
              </div>
            `
            : `<p class="item-meta">No USDA match attached.</p>`;
          return `
            <article class="item-card">
              <p class="item-title">${item.label || "Unnamed item"}</p>
              <p class="item-meta">${parts.join("<br />") || "No extra notes."}</p>
              ${usdaHtml}
            </article>
          `;
        })
        .join("")
    : `
      <article class="item-card">
        <p class="item-title">No model-labeled items returned</p>
        <p class="item-meta">The model did not provide a structured meal item list for this image.</p>
      </article>
    `;
}

function formatNumber(value, suffix = "") {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "--";
  }
  return `${Number(value).toFixed(1).replace(/\.0$/, "")}${suffix}`;
}

function formatMs(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "--";
  }
  const numeric = Number(value);
  return numeric >= 1000 ? `${(numeric / 1000).toFixed(2)} s` : `${numeric.toFixed(1).replace(/\.0$/, "")} ms`;
}

function renderNutritionSummary(summary) {
  const totals = summary?.totals || {};
  nutritionSummary.innerHTML = `
    <article class="metric-card metric-card-primary">
      <span class="metric-label">Estimated Calories</span>
      <strong class="metric-value">${formatNumber(totals.calories)}</strong>
    </article>
    <article class="metric-card">
      <span class="metric-label">Protein</span>
      <strong class="metric-value">${formatNumber(totals.protein_g, " g")}</strong>
    </article>
    <article class="metric-card">
      <span class="metric-label">Carbs</span>
      <strong class="metric-value">${formatNumber(totals.carbs_g, " g")}</strong>
    </article>
    <article class="metric-card">
      <span class="metric-label">Fat</span>
      <strong class="metric-value">${formatNumber(totals.fat_g, " g")}</strong>
    </article>
  `;
  nutritionInsights.innerHTML = (summary?.insights || [])
    .map((insight) => `<li>${insight}</li>`)
    .join("");
  nutritionDisclaimer.textContent = summary?.disclaimer || "";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderQuestionAnswer(question, answer, disclaimer, timings) {
  const answerText = answer || "";
  const disclaimerLabel = "Disclaimer:";
  const disclaimerIndex = answerText.indexOf(disclaimerLabel);
  const bodyText =
    disclaimerIndex >= 0 ? answerText.slice(0, disclaimerIndex).trim() : answerText.trim();
  const bodyParagraphs = bodyText
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);
  const summary = currentAnalysis?.nutrition_summary;
  const totals = summary?.totals || {};

  const tableHtml = summary
    ? `
      <table class="qa-table">
        <thead>
          <tr>
            <th>Metric</th>
            <th>Estimate</th>
          </tr>
        </thead>
        <tbody>
          <tr><td>Calories</td><td>${formatNumber(totals.calories)}</td></tr>
          <tr><td>Protein</td><td>${formatNumber(totals.protein_g, " g")}</td></tr>
          <tr><td>Carbs</td><td>${formatNumber(totals.carbs_g, " g")}</td></tr>
          <tr><td>Fat</td><td>${formatNumber(totals.fat_g, " g")}</td></tr>
        </tbody>
      </table>
    `
    : "";

  const timingsHtml = timings
    ? `
      <table class="qa-table">
        <thead>
          <tr>
            <th>Q&A Step</th>
            <th>Time</th>
          </tr>
        </thead>
        <tbody>
          <tr><td>Answer generation</td><td>${formatMs(timings.answer_generation)}</td></tr>
          <tr><td>Output safety review</td><td>${formatMs(timings.output_review)}</td></tr>
          <tr><td>Total</td><td>${formatMs(timings.total)}</td></tr>
        </tbody>
      </table>
    `
    : "";

  questionAnswer.innerHTML = `
    <div class="question-answer-card">
      <p class="question-answer-label">Question</p>
      <p class="question-answer-question">${escapeHtml(question)}</p>
      <p class="question-answer-label">Answer</p>
      <div class="question-answer-body">
        ${bodyParagraphs.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("")}
      </div>
      ${tableHtml}
      ${timingsHtml}
      <div class="question-answer-disclaimer">
        <strong>Disclaimer</strong>
        <p>${escapeHtml(disclaimer || currentAnalysis?.nutrition_summary?.disclaimer || "")}</p>
      </div>
    </div>
  `;
  questionAnswer.classList.remove("hidden");
}

function renderStageSummaries(data) {
  const moderation = data.model_response?.moderation || null;
  const observer = data.model_response?.observer || null;
  const modelOutput = data.model_response?.model_output || null;
  const outputReview = data.model_response?.output_review || null;
  const pipelineStarted = Boolean(data.model_response);
  const requestFailed = Boolean(data.error || data.detail);
  const timings = data.model_response?.timings_ms || {};
  const moderationFlags = data.validation?.moderation_flags || [];
  const passedModeration = moderationFlags.length === 0 && data.validation?.reason_code !== "unsafe_content";
  const observerDecision = observer?.food_relevance || (passedModeration ? data.validation?.food_relevance || "--" : "--");
  const passedObserver = observerDecision === "food";
  const advancedToInference = Boolean(modelOutput) && passedModeration && passedObserver;

  renderRows(moderationSummary, [
    {
      label: "Moderation ran",
      value: moderation ? "Yes" : pipelineStarted ? "No" : "No",
    },
    { label: "Passed moderation", value: moderation ? (passedModeration ? "Yes" : "No") : "--" },
    { label: "Time", value: formatMs(timings.moderation) },
    { label: "Safety flags", value: moderationFlags.join(", ") || "None" },
    {
      label: "Blocked at moderation",
      value: data.model_response?.reason === "unsafe_content" ? "Yes" : "No",
    },
  ]);

  renderRows(observerSummary, [
    { label: "Observer ran", value: observer ? "Yes" : moderation ? "No" : "--" },
    { label: "Observer decision", value: observerDecision },
    { label: "Time", value: formatMs(timings.observer) },
    {
      label: "Passed observer",
      value: observer ? (passedObserver ? "Yes" : "No") : "--",
    },
  ]);

  renderRows(inferenceSummary, [
    { label: "Moved to model inference", value: modelOutput ? "Yes" : observer ? "No" : "--" },
    {
      label: "Model returned items",
      value: (modelOutput?.meal_items || data.analysis?.meal_items || []).length ? "Yes" : "No",
    },
    { label: "Time", value: formatMs(timings.inference) },
    {
      label: "Blocked before inference",
      value: data.model_response?.reason === "observer_filtered" ? "Yes" : "No",
    },
  ]);

  renderRows(outputReviewSummary, [
    { label: "Reviewer ran", value: outputReview ? "Yes" : modelOutput ? "No" : "--" },
    { label: "Time", value: formatMs(timings.output_review) },
    {
      label: "Safe to display",
      value: outputReview ? (outputReview.is_safe ? "Yes" : "No") : "--",
    },
    {
      label: "Reviewer note",
      value: outputReview?.notes || "--",
    },
  ]);

  moderationJson.textContent = JSON.stringify(
    moderation ||
      (requestFailed
        ? { status: "request_failed_before_moderation", detail: data.detail || data.error }
        : pipelineStarted
          ? { status: "moderation_skipped" }
          : { status: "pipeline_not_started" }),
    null,
    2
  );
  observerJson.textContent = JSON.stringify(
    observer ||
      (requestFailed
        ? { status: "request_failed_before_observer", detail: data.detail || data.error }
        : moderation
          ? { status: "observer_not_reached" }
          : { status: "pipeline_not_started" }),
    null,
    2
  );
  resultJson.textContent = JSON.stringify(
    modelOutput ||
      (requestFailed
        ? { status: "request_failed_before_inference", detail: data.detail || data.error }
        : data.model_response?.blocked_before_model
          ? { status: "skipped_due_to_stage_gate", reason: data.model_response?.reason || "unknown" }
          : { status: "inference_not_reached" }),
    null,
    2
  );
  outputReviewJson.textContent = JSON.stringify(
    outputReview ||
      (requestFailed
        ? { status: "request_failed_before_output_review", detail: data.detail || data.error }
        : modelOutput
          ? { status: "output_review_not_reached" }
          : { status: "pipeline_not_started" }),
    null,
    2
  );
}

function renderAnalysis(data) {
  const analysis = data.analysis;
  currentAnalysis = analysis || null;
  const inferredComponents = data.detected_components || analysis?.detected_components || [];
  const labeledItems = analysis?.meal_items || [];

  renderStageSummaries(data);
  renderDetectedComponents(inferredComponents);
  renderRows(validationDetails, [
    { label: "Status", value: data.validation?.status || "--" },
    { label: "Reason", value: data.validation?.reason_code || "--" },
    { label: "Food relevance", value: data.validation?.food_relevance || "--" },
    {
      label: "Moderation flags",
      value: (data.validation?.moderation_flags || []).join(", ") || "None",
    },
  ]);

  if (!analysis) {
    analysisView.classList.add("hidden");
    resultMessage.classList.remove("hidden");
    resultMessage.textContent =
      data.validation?.status === "needs_clarification"
        ? "The app needs a little more detail before it can confidently list the meal items in this image."
        : data.detail || data.error || "No model analysis is available for this request.";
    return;
  }

  resultMessage.classList.add("hidden");
  analysisView.classList.remove("hidden");
  renderNutritionSummary(analysis?.nutrition_summary);
  renderMealItems(labeledItems);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const file = imageFileInput.files?.[0];

  if (!file) {
    alert("Add a meal photo before submitting.");
    return;
  }

  const payload = {
    filename: file.name,
    mime_type: file.type || "image/jpeg",
    size_bytes: file.size || 1,
    image_base64: await toBase64(file),
  };

  resultPanel.classList.remove("hidden");
  resultStatus.textContent = "Submitting...";
  resultMessage.classList.add("hidden");
  analysisView.classList.add("hidden");
  questionAnswer.classList.add("hidden");
  questionAnswer.innerHTML = "";
  moderationJson.textContent = "";
  observerJson.textContent = "";
  resultJson.textContent = "";
  outputReviewJson.textContent = "";

  try {
    const response = await fetch("/meals", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-user-id": "web-demo-user",
      },
      body: JSON.stringify(payload),
    });

    const rawText = await response.text();
    let data;
    try {
      data = rawText ? JSON.parse(rawText) : {};
    } catch {
      data = { error: rawText || "Unknown server response" };
    }

    resultStatus.textContent = response.ok ? data.status || "completed" : "error";
    currentMealId = data.meal_id || null;
    renderAnalysis(data);
  } catch (error) {
    resultStatus.textContent = "error";
    currentMealId = null;
    currentAnalysis = null;
    const errorPayload = { error: error instanceof Error ? error.message : "Unknown error" };
    moderationJson.textContent = JSON.stringify({ status: "request_failed" }, null, 2);
    observerJson.textContent = JSON.stringify({ status: "request_failed" }, null, 2);
    resultJson.textContent = JSON.stringify(errorPayload, null, 2);
    renderAnalysis(errorPayload);
  }
});

loadStatus().catch(() => {
  apiStatus.textContent = "API: unavailable";
  openaiStatus.textContent = "Image analysis: unavailable";
});

questionForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const question = questionInput.value.trim();
  if (!currentMealId) {
    alert("Analyze a meal first before asking a follow-up question.");
    return;
  }
  if (!question) {
    alert("Enter a question about the meal analysis.");
    return;
  }

  questionAnswer.classList.remove("hidden");
  questionAnswer.innerHTML = '<div class="question-answer-card"><p class="question-answer-label">Answer</p><p class="question-answer-question">Thinking...</p></div>';

  try {
    const response = await fetch(`/meals/${currentMealId}/questions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question }),
    });
    const rawText = await response.text();
    let data;
    try {
      data = rawText ? JSON.parse(rawText) : {};
    } catch {
      data = { error: rawText || "Unknown server response" };
    }

    if (!response.ok) {
      questionAnswer.innerHTML = `<div class="question-answer-card"><p class="question-answer-label">Answer</p><p class="question-answer-question">${escapeHtml(data.detail || data.error || "Unable to answer that question right now.")}</p></div>`;
      return;
    }

    renderQuestionAnswer(
      question,
      data.answer || "No answer was returned.",
      data.disclaimer || "",
      data.timings_ms || null
    );
  } catch (error) {
    questionAnswer.innerHTML = `<div class="question-answer-card"><p class="question-answer-label">Answer</p><p class="question-answer-question">${escapeHtml(error instanceof Error ? error.message : "Unknown error")}</p></div>`;
  }
});
