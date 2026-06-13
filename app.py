from __future__ import annotations

import html
import json
import sys
from pathlib import Path

import gradio as gr

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

from packetcourt import audit_packet
from packetcourt.ocr import extract_text
from packetcourt.samples import SAMPLES


VERDICT_CLASS = {
    "SUPPORTED BY PROVIDED LABEL": "supported",
    "CONTRADICTED BY PROVIDED LABEL": "contradicted",
    "TECHNICALLY TRUE, CONTEXT MISSING": "context",
    "CANNOT VERIFY": "unknown",
}


def render_report(front_text: str, back_text: str) -> tuple[str, str]:
    audit = audit_packet(front_text, back_text)
    if not audit.claims:
        cards = """
        <div class="empty-state">
          <div class="empty-mark">?</div>
          <h3>No supported claim type detected</h3>
          <p>Try a front label containing claims such as High Protein, No Added Sugar,
          Multigrain, 100% Natural, FSSAI Approved, or No Preservatives.</p>
        </div>
        """
    else:
        cards = "".join(
            f"""
            <article class="claim-card {VERDICT_CLASS[claim.verdict.value]}">
              <div class="claim-top">
                <span class="claim-name">{html.escape(claim.claim)}</span>
                <span class="verdict">{html.escape(claim.verdict.value)}</span>
              </div>
              <p class="summary">{html.escape(claim.summary)}</p>
              <div class="evidence-list">
                {''.join(f'<div class="evidence"><b>{html.escape(e.source)}</b><span>{html.escape(e.text)}</span></div>' for e in claim.evidence)}
              </div>
              {f'<p class="caveat">{html.escape(claim.caveat)}</p>' if claim.caveat else ''}
            </article>
            """
            for claim in audit.claims
        )

    nutrition_rows = [
        ("Basis", audit.nutrition.basis),
        ("Protein", f"{audit.nutrition.protein_g:g}g" if audit.nutrition.protein_g is not None else "Not found"),
        ("Total sugar", f"{audit.nutrition.total_sugar_g:g}g" if audit.nutrition.total_sugar_g is not None else "Not found"),
        ("Added sugar", f"{audit.nutrition.added_sugar_g:g}g" if audit.nutrition.added_sugar_g is not None else "Not found"),
        ("Sodium", f"{audit.nutrition.sodium_mg:g}mg" if audit.nutrition.sodium_mg is not None else "Not found"),
    ]
    facts = "".join(f"<div><span>{html.escape(k)}</span><b>{html.escape(v)}</b></div>" for k, v in nutrition_rows)
    expiry = html.escape(audit.expiry.status)
    report = f"""
    <section class="report-shell">
      <div class="report-heading">
        <div><span class="eyebrow">EVIDENCE HEARING</span><h2>Packet claim audit</h2></div>
        <span class="claim-count">{len(audit.claims)} claims examined</span>
      </div>
      <div class="claim-grid">{cards}</div>
      <div class="secondary-grid">
        <section class="facts-panel"><span class="eyebrow">NUTRITION EVIDENCE</span>{facts}</section>
        <section class="expiry-panel"><span class="eyebrow">DATE EVIDENCE</span><h3>{expiry}</h3><p>Expiry interpretation is shown as evidence, not a food-safety guarantee.</p></section>
      </div>
    </section>
    """
    return report, json.dumps(audit.model_dump(mode="json"), indent=2)


def read_images(front_image: str | None, back_image: str | None) -> tuple[str, str, str]:
    front, front_status = extract_text(front_image)
    back, back_status = extract_text(back_image)
    return front, back, f"Front: {front_status}\nBack: {back_status}"


def load_sample(name: str) -> tuple[str, str]:
    sample = SAMPLES[name]
    return sample["front"], sample["back"]


CSS = """
:root { --ink:#171611; --paper:#f7f2e7; --red:#d64c3f; --green:#2c7458; --amber:#b97918; }
.gradio-container { max-width: 1180px !important; margin:auto; background:var(--paper); color:var(--ink); }
.hero { border:1px solid #d7cdbd; border-radius:28px; padding:34px; margin:14px 0 20px;
  background:radial-gradient(circle at 90% 10%,#ffd7a8,transparent 35%),linear-gradient(135deg,#fffaf0,#f1e8d8); }
.hero h1 { font-size:clamp(42px,8vw,92px); line-height:.9; letter-spacing:-.07em; margin:8px 0 16px; }
.hero p { max-width:700px; font-size:18px; color:#514c43; }
.eyebrow { font:700 11px/1 monospace; letter-spacing:.16em; color:#6b6256; }
.report-shell { margin-top:18px; }.report-heading,.claim-top { display:flex; justify-content:space-between; gap:12px; align-items:start; }
.report-heading h2 { margin:6px 0 18px; font-size:34px; letter-spacing:-.04em; }
.claim-count,.verdict { font:700 10px/1.3 monospace; text-transform:uppercase; padding:8px 10px; border:1px solid #c9beae; border-radius:99px; }
.claim-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(290px,1fr)); gap:14px; }
.claim-card { background:#fffdf7; border:1px solid #d6ccbc; border-top:5px solid #777; border-radius:18px; padding:18px; box-shadow:0 8px 26px #5f493510; }
.claim-card.supported { border-top-color:var(--green); }.claim-card.contradicted { border-top-color:var(--red); }
.claim-card.context { border-top-color:var(--amber); }.claim-name { font-size:21px; font-weight:800; }
.summary { min-height:48px; color:#49443c; }.evidence-list { display:grid; gap:7px; }
.evidence { display:grid; gap:3px; background:#f4eee3; border-radius:10px; padding:10px; }
.evidence b { font:700 10px/1 monospace; text-transform:uppercase; color:#756b5e; }
.caveat { font-size:12px; color:#746b5f; border-top:1px dashed #cfc2af; padding-top:10px; }
.secondary-grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:14px; }
.facts-panel,.expiry-panel,.empty-state { border:1px solid #d6ccbc; border-radius:18px; padding:18px; background:#fffdf7; }
.facts-panel div { display:flex; justify-content:space-between; border-bottom:1px solid #ebe2d5; padding:9px 0; }
.empty-state { text-align:center; padding:35px; }.empty-mark { font-size:60px; color:var(--amber); }
@media(max-width:700px){.secondary-grid{grid-template-columns:1fr}.hero{padding:24px}.claim-top{display:grid}.verdict{width:fit-content}}
"""


with gr.Blocks(title="PacketCourt") as demo:
    gr.HTML(
        """
        <section class="hero">
          <span class="eyebrow">PACKETCOURT / INDIA</span>
          <h1>The packet<br>takes the stand.</h1>
          <p>Photograph the front and back of an Indian food packet. PacketCourt audits
          marketing claims against the evidence printed on the same package.</p>
        </section>
        """
    )
    with gr.Tabs():
        with gr.Tab("Audit a packet"):
            with gr.Row():
                front_image = gr.Image(type="filepath", label="Front of packet", sources=["upload", "webcam"])
                back_image = gr.Image(type="filepath", label="Back label", sources=["upload", "webcam"])
            read_button = gr.Button("Read label photos", variant="secondary")
            ocr_status = gr.Textbox(label="OCR status", interactive=False, lines=2)
            with gr.Row():
                front_text = gr.Textbox(label="Front claims", lines=7, placeholder="OCR output appears here. Correct it before auditing.")
                back_text = gr.Textbox(label="Back-label evidence", lines=10, placeholder="Ingredients, nutrition panel, dates, and license evidence.")
            audit_button = gr.Button("Put this packet on trial", variant="primary")
        with gr.Tab("Try a prepared case"):
            sample = gr.Dropdown(list(SAMPLES), value=list(SAMPLES)[0], label="Prepared evidence case")
            sample_button = gr.Button("Load prepared case")
            gr.Markdown("Prepared cases let judges test the complete audit flow without taking photos.")
        with gr.Tab("Method"):
            gr.Markdown(
                """
                ### Evidence before verdict
                PacketCourt does not declare a product healthy, safe, illegal, or fraudulent.
                It extracts visible claims, links them to supplied evidence, runs conservative
                deterministic checks, and refuses conclusions it cannot support.

                **Current Phase 1 claim types:** High Protein, No Added Sugar, Multigrain,
                100% Natural, FSSAI Approved, and No Preservatives.
                """
            )
    report = gr.HTML()
    raw_json = gr.Code(label="Machine-readable evidence case", language="json")

    read_button.click(read_images, [front_image, back_image], [front_text, back_text, ocr_status])
    sample_button.click(load_sample, sample, [front_text, back_text]).then(render_report, [front_text, back_text], [report, raw_json])
    audit_button.click(render_report, [front_text, back_text], [report, raw_json])

if __name__ == "__main__":
    demo.launch(css=CSS)
