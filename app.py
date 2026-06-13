from __future__ import annotations

import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

import gradio as gr
import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

try:
    import spaces
except ImportError:
    class _SpacesFallback:
        @staticmethod
        def GPU(*_args, **_kwargs):
            return lambda function: function

    spaces = _SpacesFallback()

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

from packetcourt import audit_packet
from packetcourt.ocr import extract_text
from packetcourt.samples import SAMPLES
from packetcourt.vlm import model_status
from packetcourt.vlm import extract_with_vlm


class AuditRequest(BaseModel):
    front_text: str
    back_text: str


@spaces.GPU(duration=180)
def gpu_extract_label(image_path: str, side: str) -> str:
    return extract_with_vlm(image_path, side)


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
    return model_status()


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
            text, status = extract_text(temp.name, name, gpu_extract_label)
        result[name] = {"text": text, "status": status}
    return result


app = gr.mount_gradio_app(app, build_gradio_engine(), path="/engine")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
