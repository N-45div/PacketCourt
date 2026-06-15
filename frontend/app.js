const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const verdictClass = {
  "SUPPORTED BY PROVIDED LABEL": "supported",
  "CONTRADICTED BY PROVIDED LABEL": "contradicted",
  "TECHNICALLY TRUE, CONTEXT MISSING": "context",
  "CANNOT VERIFY": "unknown",
};
let currentAudit = null;
let feedbackVerdict = "";

function setMode(mode) {
  $$(".mode-switch button").forEach((button) => button.classList.toggle("active", button.dataset.mode === mode));
  $$(".mode-panel").forEach((panel) => panel.classList.toggle("active", panel.id === `mode-${mode}`));
}

$$(".mode-switch button").forEach((button) => button.addEventListener("click", () => setMode(button.dataset.mode)));
$$("[data-scroll]").forEach((button) => button.addEventListener("click", () => $(`#${button.dataset.scroll}`).scrollIntoView()));

const photoSets = { front: [], back: [] };

function preview(input, target, side) {
  input.addEventListener("change", () => {
    const incoming = [...input.files];
    if (!incoming.length) return;
    const available = Math.max(0, 6 - photoSets[side].length);
    photoSets[side].push(...incoming.slice(0, available));
    const file = photoSets[side][photoSets[side].length - 1];
    target.style.backgroundImage = `url(${URL.createObjectURL(file)})`;
    target.innerHTML = "";
    $(`#${side}-count`).textContent = `${photoSets[side].length} photo${photoSets[side].length === 1 ? "" : "s"} · add more`;
    input.value = "";
  });
}
preview($("#front-file"), $("#front-preview"), "front");
preview($("#back-file"), $("#back-preview"), "back");

$("#clear-photos").addEventListener("click", () => {
  photoSets.front.length = 0;
  photoSets.back.length = 0;
  [["front", "F"], ["back", "B"]].forEach(([side, label]) => {
    $(`#${side}-preview`).style.backgroundImage = "";
    $(`#${side}-preview`).innerHTML = `<span class="upload-icon">${label}</span>`;
    $(`#${side}-count`).textContent = "Add photos";
  });
  $("#ocr-status").textContent = "Selected photos cleared.";
});

async function runAudit(frontText, backText) {
  const response = await fetch("api/audit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ front_text: frontText, back_text: backText }),
  });
  if (!response.ok) throw new Error("The evidence engine could not open this case.");
  render(await response.json());
}

function evidenceHtml(item) {
  return `<div class="evidence"><b>${escapeHtml(item.source)}</b><span>${escapeHtml(item.text)}</span></div>`;
}

function escapeHtml(value = "") {
  return value.replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[char]);
}

function render(data) {
  currentAudit = data;
  $("#claim-count").textContent = data.claims.length;
  $("#router-model").textContent = data.investigation.router_model;
  $("#agent-steps").innerHTML = data.investigation.steps.map((step, index) => `
    <article>
      <span>${String(index + 1).padStart(2, "0")}</span>
      <div><b>${escapeHtml(step.tool.replaceAll("_", " "))}</b><p>${escapeHtml(step.reason)}</p></div>
      <small>${escapeHtml(step.source)} · ${escapeHtml(step.status)}</small>
    </article>
  `).join("");
  $("#stop-reason").textContent = data.investigation.stop_reason;
  $("#missing-evidence").textContent = data.investigation.missing_evidence.length
    ? data.investigation.missing_evidence.join(" · ")
    : "None. The required evidence path completed.";
  const review = data.agent_review;
  $("#nemotron-review").innerHTML = review.status === "NOT_REQUESTED"
    ? ""
    : `<b>NVIDIA NEMOTRON INDEPENDENT REVIEW · ${escapeHtml(review.status)}</b>
       <strong>${escapeHtml(review.priority || "No additional action requested.")}</strong>
       <span>${escapeHtml(review.evidence_request || review.rationale)}</span>`;
  $("#claim-grid").innerHTML = data.claims.length
    ? data.claims.map((claim) => `
      <article class="claim-card ${verdictClass[claim.verdict]}">
        <div class="claim-top"><span class="claim-name">${escapeHtml(claim.claim)}</span><span class="verdict">${escapeHtml(claim.verdict)}</span></div>
        <span class="confidence">Evidence confidence · ${escapeHtml(claim.confidence)}</span>
        <p class="summary">${escapeHtml(claim.summary)}</p>
        ${claim.evidence.map(evidenceHtml).join("")}
        ${claim.caveat ? `<p class="caveat">${escapeHtml(claim.caveat)}</p>` : ""}
      </article>`).join("")
    : `<article class="claim-card unknown"><span class="claim-name">No supported claim detected</span><p class="summary">Try High Protein, No Added Sugar, Multigrain, 100% Natural, FSSAI Approved, or No Preservatives.</p></article>`;
  $("#gap-grid").innerHTML = data.persuasion_gap.length
    ? data.persuasion_gap.map((finding) => `
      <article class="gap-card ${escapeHtml(finding.severity)}">
        <span class="gap-severity">${escapeHtml(finding.severity)} context gap</span>
        <h4>${escapeHtml(finding.headline)}</h4>
        <div class="gap-compare"><p><b>FRONT IMPRESSION</b>${escapeHtml(finding.front_impression)}</p><p><b>QUIET CONTEXT</b>${escapeHtml(finding.quiet_context)}</p></div>
        ${finding.evidence.map(evidenceHtml).join("")}
      </article>`).join("")
    : `<article class="gap-empty"><b>No persuasion gap calculated</b><span>More complete nutrition, ingredient, or package-size evidence may be required.</span></article>`;
  const packet = data.whole_packet;
  const facts = [
    ["Declared basis", data.nutrition.basis],
    ["Packet size", data.nutrition.package_size_g == null ? "Not found" : `${data.nutrition.package_size_g}g`],
    ["Whole-packet protein", packet.protein_g == null ? "Not calculable" : `${packet.protein_g}g`],
    ["Whole-packet total sugar", packet.total_sugar_g == null ? "Not calculable" : `${packet.total_sugar_g}g`],
    ["Sugar equivalent", packet.sugar_teaspoons == null ? "Not calculable" : `≈ ${packet.sugar_teaspoons} tsp`],
    ["Whole-packet sodium", packet.sodium_mg == null ? "Not calculable" : `${packet.sodium_mg}mg`],
  ];
  $("#nutrition-grid").innerHTML = facts.map(([key, value]) => `<div><span>${key}</span><b>${value}</b></div>`).join("");
  $("#nutrition-explanation").textContent = packet.explanation;
  $("#expiry-status").textContent = data.expiry.status;
  $("#opening-status").textContent = data.expiry.after_opening_instruction
    ? `After opening: ${data.expiry.after_opening_instruction}`
    : "No after-opening deadline found.";
  $("#raw-json").textContent = JSON.stringify(data, null, 2);
  $("#results").classList.remove("hidden");
  $("#results").scrollIntoView({ behavior: "smooth" });
}

$$("[data-feedback]").forEach((button) => button.addEventListener("click", () => {
  feedbackVerdict = button.dataset.feedback;
  $$("[data-feedback]").forEach((choice) => choice.classList.toggle("active", choice === button));
}));

$("#submit-feedback").addEventListener("click", async () => {
  if (!currentAudit || !feedbackVerdict) {
    $("#feedback-status").textContent = "Run an audit and choose a review outcome first.";
    return;
  }
  $("#feedback-status").textContent = "Packaging evidence review...";
  const response = await fetch("api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      verdict: feedbackVerdict,
      correction: $("#feedback-correction").value,
      audit: currentAudit,
    }),
  });
  const result = await response.json();
  $("#feedback-status").textContent = result.message;
});

$("#audit-text").addEventListener("click", async () => {
  $("#audit-text").textContent = "Examining evidence...";
  try { await runAudit($("#front-text").value, $("#back-text").value); }
  catch (error) { alert(error.message); }
  finally { $("#audit-text").innerHTML = "Put this packet on trial <span>→</span>"; }
});

$("#read-photos").addEventListener("click", async () => {
  const form = new FormData();
  photoSets.front.forEach((file) => form.append("fronts", file));
  photoSets.back.forEach((file) => form.append("backs", file));
  $("#ocr-status").textContent = `Reading ${photoSets.front.length + photoSets.back.length} packet photos...`;
  try {
    const response = await fetch("api/ocr", { method: "POST", body: form });
    const result = await response.json();
    $("#front-text").value = result.front.text;
    $("#back-text").value = result.back.text;
    $("#ocr-status").textContent = `${result.front.status} ${result.back.status} Review merged evidence before trial.`;
    setMode("text");
  } catch (error) { $("#ocr-status").textContent = "OCR failed. Paste the label text to continue."; }
});

async function loadSamples() {
  const samples = await fetch("api/samples").then((response) => response.json());
  $("#sample-grid").innerHTML = Object.entries(samples).map(([name, value]) => `
    <button class="sample-card" data-name="${escapeHtml(name)}"><b>${escapeHtml(name)}</b><span>${escapeHtml(value.front)}</span></button>
  `).join("");
  $$(".sample-card").forEach((button) => button.addEventListener("click", async () => {
    const sample = samples[button.dataset.name];
    $("#front-text").value = sample.front;
    $("#back-text").value = sample.back;
    await runAudit(sample.front, sample.back);
  }));
  $("#hero-sample").addEventListener("click", () => { setMode("samples"); $("#workspace").scrollIntoView(); });
}
loadSamples();

fetch("api/model").then((response) => response.json()).then((status) => {
  $("#model-mode").textContent = status.enabled ? "MiniCPM-V evidence engine online" : "Deterministic evidence engine online";
}).catch(() => {});
