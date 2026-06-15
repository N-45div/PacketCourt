from __future__ import annotations

import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

import gradio as gr
import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

from packetcourt import audit_packet
from packetcourt.models import AgentReview
from packetcourt.ocr import extract_text, merge_extractions
from packetcourt.remote_vision import extract_remote, is_configured
from packetcourt.remote_nemotron import is_configured as nemotron_is_configured
from packetcourt.remote_nemotron import review as nemotron_review
from packetcourt.samples import SAMPLES
from packetcourt.vlm import model_status


class AuditRequest(BaseModel):
    front_text: str
    back_text: str


class FeedbackRequest(BaseModel):
    verdict: str
    correction: str = ""
    audit: dict


def run_audit(front_text: str, back_text: str):
    result = audit_packet(front_text, back_text)
    if not nemotron_is_configured():
        return result
    snapshot = {
        "claims": [claim.model_dump(mode="json") for claim in result.claims],
        "investigation": result.investigation.model_dump(),
        "nutrition": result.nutrition.model_dump(),
        "ingredients_found": bool(result.ingredients),
        "expiry": result.expiry.model_dump(),
        "limitations": result.limitations,
    }
    try:
        result.agent_review = AgentReview.model_validate(nemotron_review(snapshot))
        if not result.investigation.missing_evidence:
            result.agent_review.status = "COMPLETE"
            result.agent_review.priority = "No additional claim-resolving evidence is required."
            result.agent_review.evidence_request = ""
    except Exception as exc:
        result.agent_review = AgentReview(
            status="UNAVAILABLE",
            rationale=f"Nemotron review unavailable: {type(exc).__name__}: {exc}",
            model="nvidia/Nemotron-Mini-4B-Instruct",
        )
    return result


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
            lambda front_text, back_text: run_audit(front_text, back_text).model_dump(mode="json"),
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
    status["nemotron_reviewer"] = (
        "nvidia/Nemotron-Mini-4B-Instruct"
        if nemotron_is_configured()
        else "not configured"
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
    return run_audit(request.front_text, request.back_text).model_dump(mode="json")


@app.post("/api/feedback")
def feedback(request: FeedbackRequest) -> dict:
    if request.verdict not in {"accurate", "needs_correction"}:
        return {"status": "REJECTED", "message": "Choose accurate or needs correction."}
    if request.verdict == "needs_correction" and len(request.correction.strip()) < 8:
        return {"status": "REJECTED", "message": "Explain the correction so it can be reviewed."}

    record_id = str(uuid4())
    record = {
        "id": record_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "verdict": request.verdict,
        "correction": request.correction.strip()[:1200],
        "front_text": str(request.audit.get("front_text", ""))[:3000],
        "back_text": str(request.audit.get("back_text", ""))[:9000],
        "claims": request.audit.get("claims", []),
        "investigation": request.audit.get("investigation", {}),
        "nemotron_review": request.audit.get("agent_review", {}),
        "proposed_router_examples": [
            {
                "text": claim.get("claim", ""),
                "candidate_tools": [
                    step.get("tool", "")
                    for step in request.audit.get("investigation", {}).get("steps", [])
                ],
            }
            for claim in request.audit.get("claims", [])
        ],
        "review_status": "pending_human_review",
        "training_eligible": False,
        "learning_policy": "Only approved corrections enter the next evidence-router fine-tune.",
    }
    dataset_id = os.getenv("PACKETCOURT_FEEDBACK_DATASET")
    if not dataset_id:
        return {
            "status": "UNAVAILABLE",
            "message": "The community learning queue is not configured on this deployment.",
        }
    try:
        from huggingface_hub import HfApi

        HfApi().upload_file(
            path_or_fileobj=json.dumps(record, indent=2).encode(),
            path_in_repo=f"feedback/{record_id}.json",
            repo_id=dataset_id,
            repo_type="dataset",
            commit_message=f"feedback: queue PacketCourt review {record_id[:8]}",
        )
    except Exception as exc:
        return {
            "status": "UNAVAILABLE",
            "message": f"Feedback could not be persisted: {type(exc).__name__}",
        }
    return {
        "status": "QUEUED",
        "id": record_id,
        "message": "Review queued. It will become training data only after evidence review.",
        "dataset": f"https://huggingface.co/datasets/{dataset_id}",
    }


async def _read_uploads(uploads: list[UploadFile], side: str) -> dict:
    extracted: list[tuple[str, str]] = []
    for upload in uploads[:6]:
        suffix = Path(upload.filename or "image.jpg").suffix or ".jpg"
        with NamedTemporaryFile(suffix=suffix) as temp:
            temp.write(await upload.read())
            temp.flush()
            extracted.append(extract_text(temp.name, side, extract_remote if is_configured() else None))
    text, status, images = merge_extractions(extracted, side)
    if len(uploads) > 6:
        status += f" Only the first 6 of {len(uploads)} photos were processed."
    return {"text": text, "status": status, "images": images}


@app.post("/api/ocr")
async def ocr(
    fronts: list[UploadFile] | None = File(default=None),
    backs: list[UploadFile] | None = File(default=None),
    front: UploadFile | None = File(default=None),
    back: UploadFile | None = File(default=None),
) -> dict:
    front_uploads = list(fronts or []) + ([front] if front else [])
    back_uploads = list(backs or []) + ([back] if back else [])
    return {
        "front": await _read_uploads(front_uploads, "front"),
        "back": await _read_uploads(back_uploads, "back"),
    }


app = gr.mount_gradio_app(app, build_gradio_engine(), path="/engine")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
