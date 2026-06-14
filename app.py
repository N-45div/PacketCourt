from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

import gradio as gr
import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

from packetcourt import audit_packet
from packetcourt.ocr import extract_text
from packetcourt.remote_vision import extract_remote, is_configured
from packetcourt.samples import SAMPLES
from packetcourt.vlm import model_status


class AuditRequest(BaseModel):
    front_text: str
    back_text: str


def build_gradio_engine() -> gr.Blocks:
    with gr.Blocks(title="PacketCourt Engine") as engine:
        gr.Markdown(
            "# PacketCourt Engine\n"
            "The public product interface is served at `/`. This mounted Gradio engine "
            "keeps PacketCourt compatible with the Build Small Gradio requirement."
        )
        front = gr.Textbox(label="Front claims")
        back = gr.Textbox(label="Back-label evidence")
        output = gr.JSON(label="Evidence case")
        gr.Button("Audit").click(
            lambda front_text, back_text: audit_packet(front_text, back_text).model_dump(mode="json"),
            [front, back],
            output,
        )
    return engine


app = FastAPI(title="PacketCourt")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    html = (ROOT / "frontend" / "index.html").read_text()
    css = (ROOT / "frontend" / "styles.css").read_text()
    javascript = (ROOT / "frontend" / "app.js").read_text()
    return html.replace("/*__PACKETCOURT_CSS__*/", css).replace("/*__PACKETCOURT_JS__*/", javascript)


@app.get("/api/samples")
def samples() -> dict:
    return SAMPLES


@app.get("/api/model")
def model() -> dict:
    status = model_status()
    status["router"] = (
        os.getenv("PACKETCOURT_ROUTER_MODEL", "build-small-hackathon/packetcourt-evidence-router")
        if os.getenv("PACKETCOURT_ROUTER", "0") == "1"
        else "deterministic fallback"
    )
    if is_configured():
        status.update(
            enabled=True,
            mode="OpenBMB MiniCPM-V-4.6 ZeroGPU extraction with deterministic audit",
            companion=os.getenv("PACKETCOURT_VISION_SPACE"),
        )
    return status


@app.post("/api/audit")
def audit(request: AuditRequest) -> dict:
    return audit_packet(request.front_text, request.back_text).model_dump(mode="json")


@app.post("/api/ocr")
async def ocr(front: UploadFile | None = File(default=None), back: UploadFile | None = File(default=None)) -> dict:
    result: dict[str, dict[str, str]] = {}
    for name, upload in (("front", front), ("back", back)):
        if not upload:
            result[name] = {"text": "", "status": "No image supplied."}
            continue
        suffix = Path(upload.filename or "image.jpg").suffix or ".jpg"
        with NamedTemporaryFile(suffix=suffix) as temp:
            temp.write(await upload.read())
            temp.flush()
            text, status = extract_text(temp.name, name, extract_remote if is_configured() else None)
        result[name] = {"text": text, "status": status}
    return result


app = gr.mount_gradio_app(app, build_gradio_engine(), path="/engine")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
