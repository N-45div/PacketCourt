from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

MODEL_ID = os.getenv("PACKETCOURT_MODEL_ID", "openbmb/MiniCPM-V-4.6")

try:
    import spaces
except ImportError:
    class _SpacesFallback:
        @staticmethod
        def GPU(*_args, **_kwargs):
            return lambda function: function

    spaces = _SpacesFallback()

PROMPTS = {
    "front": (
        "Transcribe the visible marketing claims on this food packet front. "
        "Return only text that is visibly printed. Preserve claims such as high protein, "
        "multigrain, natural, no added sugar, baked not fried, or zero trans fat. "
        "Do not explain or infer anything."
    ),
    "back": (
        "Transcribe the visible food-label evidence from this package image. Focus on the "
        "ingredient list, nutrition values with their basis, net weight, FSSAI license, "
        "manufacturing or packing date, best-before or use-by date, and after-opening instructions. "
        "Return only visibly printed evidence. Do not explain or infer anything."
    ),
}


@lru_cache(maxsize=1)
def _load_model():
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = AutoModelForImageTextToText.from_pretrained(
        MODEL_ID,
        torch_dtype="auto",
        device_map="auto",
    )
    model.eval()
    return processor, model


def is_enabled() -> bool:
    return os.getenv("PACKETCOURT_VLM", "0") == "1"


def model_status() -> dict[str, str | bool]:
    return {
        "enabled": is_enabled(),
        "model": MODEL_ID,
        "mode": "OpenBMB vision extraction with deterministic audit" if is_enabled() else "Tesseract OCR with deterministic audit",
    }


@spaces.GPU(duration=180)
def extract_with_vlm(image_path: str, side: str) -> str:
    processor, model = _load_model()
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "url": str(Path(image_path).resolve())},
                {"type": "text", "text": PROMPTS.get(side, PROMPTS["back"])},
            ],
        }
    ]
    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
        downsample_mode="4x",
        max_slice_nums=16,
    ).to(model.device)
    generated = model.generate(
        **inputs,
        downsample_mode="4x",
        max_new_tokens=512,
        do_sample=False,
    )
    trimmed = [output[len(source) :] for source, output in zip(inputs.input_ids, generated)]
    return processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0].strip()
