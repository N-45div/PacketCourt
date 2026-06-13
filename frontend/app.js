const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const verdictClass = {
  "SUPPORTED BY PROVIDED LABEL": "supported",
  "CONTRADICTED BY PROVIDED LABEL": "contradicted",
  "TECHNICALLY TRUE, CONTEXT MISSING": "context",
  "CANNOT VERIFY": "unknown",
};

function setMode(mode) {
  $$(".mode-switch button").forEach((button) => button.classList.toggle("active", button.dataset.mode === mode));
  $$(".mode-panel").forEach((panel) => panel.classList.toggle("active", panel.id === `mode-${mode}`));
}

$$(".mode-switch button").forEach((button) => button.addEventListener("click", () => setMode(button.dataset.mode)));
$$("[data-scroll]").forEach((button) => button.addEventListener("click", () => $(`#${button.dataset.scroll}`).scrollIntoView()));

function preview(input, target) {
  input.addEventListener("change", () => {
    const file = input.files[0];
    if (!file) return;
    target.style.backgroundImage = `url(${URL.createObjectURL(file)})`;
    target.innerHTML = "";
  });
}
preview($("#front-file"), $("#front-preview"));
preview($("#back-file"), $("#back-preview"));

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
  $("#claim-count").textContent = data.claims.length;
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
  $("#expiry-status").textContent = data.expiry.status;
  $("#opening-status").textContent = data.expiry.after_opening_instruction
    ? `After opening: ${data.expiry.after_opening_instruction}`
    : "No after-opening deadline found.";
  $("#raw-json").textContent = JSON.stringify(data, null, 2);
  $("#results").classList.remove("hidden");
  $("#results").scrollIntoView({ behavior: "smooth" });
}

$("#audit-text").addEventListener("click", async () => {
  $("#audit-text").textContent = "Examining evidence...";
  try { await runAudit($("#front-text").value, $("#back-text").value); }
  catch (error) { alert(error.message); }
  finally { $("#audit-text").innerHTML = "Put this packet on trial <span>→</span>"; }
});

$("#read-photos").addEventListener("click", async () => {
  const form = new FormData();
  if ($("#front-file").files[0]) form.append("front", $("#front-file").files[0]);
  if ($("#back-file").files[0]) form.append("back", $("#back-file").files[0]);
  $("#ocr-status").textContent = "Reading label evidence...";
  try {
    const response = await fetch("api/ocr", { method: "POST", body: form });
    const result = await response.json();
    $("#front-text").value = result.front.text;
    $("#back-text").value = result.back.text;
    $("#ocr-status").textContent = `${result.front.status} ${result.back.status}`;
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
