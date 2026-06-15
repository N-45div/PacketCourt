from __future__ import annotations

import json
import traceback
from functools import lru_cache

import gradio as gr
import spaces
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_ID = "nvidia/Nemotron-Mini-4B-Instruct"

SYSTEM = """You are PacketCourt's evidence-gap reviewer.
Review the supplied packet investigation plan. Do not judge whether food is
healthy, safe, legal, or fraudulent. Do not change claim verdicts. Return only
compact JSON with these keys:
- status: COMPLETE or NEEDS_EVIDENCE
- priority: one short sentence naming the most important next action
- evidence_request: one short sentence, or an empty string
- rationale: one short sentence grounded only in the supplied investigation
Prioritize missing evidence required to resolve front-of-pack claims. Treat
expiry evidence as secondary unless expiry or shelf life is itself a front claim.
"""


@lru_cache(maxsize=1)
def load_model():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    model.eval()
    return tokenizer, model


@spaces.GPU(duration=180)
def review_investigation(snapshot: str) -> str:
    try:
        tokenizer, model = load_model()
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": snapshot[:12000]},
        ]
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        generated = model.generate(**inputs, max_new_tokens=180, do_sample=False)
        text = tokenizer.decode(generated[0][inputs.input_ids.shape[1] :], skip_special_tokens=True).strip()
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("Nemotron did not return JSON")
        payload = json.loads(text[start : end + 1])
        return json.dumps(
            {
                "status": "NEEDS_EVIDENCE" if payload.get("status") == "NEEDS_EVIDENCE" else "COMPLETE",
                "priority": str(payload.get("priority", ""))[:240],
                "evidence_request": str(payload.get("evidence_request", ""))[:240],
                "rationale": str(payload.get("rationale", ""))[:320],
                "model": MODEL_ID,
            }
        )
    except Exception as exc:
        return json.dumps(
            {
                "status": "UNAVAILABLE",
                "priority": "",
                "evidence_request": "",
                "rationale": f"{type(exc).__name__}: {exc}",
                "model": MODEL_ID,
                "diagnostic": traceback.format_exc(limit=3),
            }
        )


demo = gr.Interface(
    fn=review_investigation,
    inputs=gr.Textbox(label="Structured PacketCourt investigation snapshot", lines=14),
    outputs=gr.Textbox(label="Nemotron evidence-gap review"),
    title="PacketCourt Nemotron Reviewer",
    description="NVIDIA Nemotron Mini 4B reviews bounded PacketCourt investigations for missing evidence.",
    flagging_mode="never",
)

if __name__ == "__main__":
    demo.launch()
