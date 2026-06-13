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
  const response = await fetch("/api/audit", {
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
        <p class="summary">${escapeHtml(claim.summary)}</p>
        ${claim.evidence.map(evidenceHtml).join("")}
        ${claim.caveat ? `<p class="caveat">${escapeHtml(claim.caveat)}</p>` : ""}
      </article>`).join("")
    : `<article class="claim-card unknown"><span class="claim-name">No supported claim detected</span><p class="summary">Try High Protein, No Added Sugar, Multigrain, 100% Natural, FSSAI Approved, or No Preservatives.</p></article>`;
  const facts = [
    ["Basis", data.nutrition.basis],
    ["Protein", data.nutrition.protein_g == null ? "Not found" : `${data.nutrition.protein_g}g`],
    ["Total sugar", data.nutrition.total_sugar_g == null ? "Not found" : `${data.nutrition.total_sugar_g}g`],
    ["Added sugar", data.nutrition.added_sugar_g == null ? "Not found" : `${data.nutrition.added_sugar_g}g`],
    ["Sodium", data.nutrition.sodium_mg == null ? "Not found" : `${data.nutrition.sodium_mg}mg`],
  ];
  $("#nutrition-grid").innerHTML = facts.map(([key, value]) => `<div><span>${key}</span><b>${value}</b></div>`).join("");
  $("#expiry-status").textContent = data.expiry.status;
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
    const response = await fetch("/api/ocr", { method: "POST", body: form });
    const result = await response.json();
    $("#front-text").value = result.front.text;
    $("#back-text").value = result.back.text;
    $("#ocr-status").textContent = `${result.front.status} ${result.back.status}`;
    setMode("text");
  } catch (error) { $("#ocr-status").textContent = "OCR failed. Paste the label text to continue."; }
});

async function loadSamples() {
  const samples = await fetch("/api/samples").then((response) => response.json());
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

