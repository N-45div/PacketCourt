from __future__ import annotations

import os
from functools import lru_cache


MODEL_ID = os.getenv(
    "PACKETCOURT_ROUTER_MODEL",
    "build-small-hackathon/packetcourt-evidence-router",
)

LABEL_TO_TOOL = {
    "ingredients": "inspect_ingredients",
    "nutrition": "inspect_nutrition",
    "license": "inspect_license",
    "dates": "resolve_dates",
    "refuse_absolute": "apply_safety_boundary",
}


@lru_cache(maxsize=1)
def _pipeline():
    if os.getenv("PACKETCOURT_ROUTER", "0") != "1":
        return None
    from transformers import pipeline

    return pipeline("text-classification", model=MODEL_ID, tokenizer=MODEL_ID)


def route_claim(claim: str) -> tuple[str | None, str]:
    try:
        classifier = _pipeline()
    except Exception:
        return None, "deterministic fallback"
    if classifier is None:
        return None, "deterministic fallback"
    result = classifier(claim, truncation=True, max_length=32)[0]
    label = str(result["label"]).lower()
    return LABEL_TO_TOOL.get(label), MODEL_ID
