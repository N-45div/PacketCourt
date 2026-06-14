from __future__ import annotations

from .evidence_router import route_claim
from .models import InvestigationPlan, InvestigationStep


POLICY_TOOLS = {
    "No Added Sugar": "inspect_ingredients",
    "Multigrain": "inspect_ingredients",
    "100% Natural": "apply_safety_boundary",
    "FSSAI Approved": "inspect_license",
    "No Preservatives": "inspect_ingredients",
    "Baked Not Fried": "inspect_nutrition",
    "Zero Trans Fat": "inspect_nutrition",
    "Whole Grain": "inspect_ingredients",
    "High Protein": "inspect_nutrition",
}


def build_investigation(
    claim_names: list[str],
    ingredients: list[str],
    nutrition,
    expiry,
) -> InvestigationPlan:
    steps: list[InvestigationStep] = []
    missing: list[str] = []
    seen: set[str] = set()
    router_model = "deterministic fallback"

    for claim in claim_names:
        routed_tool, source = route_claim(claim)
        router_model = source if source != "deterministic fallback" else router_model
        tool = routed_tool or POLICY_TOOLS[claim]
        if tool in seen:
            continue
        seen.add(tool)
        steps.append(
            InvestigationStep(
                tool=tool,
                reason=f"Required to audit the front claim: {claim}.",
                status="completed",
                source="fine-tuned router" if routed_tool else "policy fallback",
            )
        )

    if claim_names and not ingredients and any(POLICY_TOOLS[name] == "inspect_ingredients" for name in claim_names):
        missing.append("A readable ingredient list")
    if claim_names and nutrition.basis == "unknown" and any(POLICY_TOOLS[name] == "inspect_nutrition" for name in claim_names):
        missing.append("A readable nutrition panel with its measurement basis")
    if expiry.instruction and not expiry.packed_on:
        missing.append("The packing or manufacturing date needed to resolve relative shelf life")

    if expiry.best_before or expiry.instruction or expiry.after_opening_instruction:
        steps.append(
            InvestigationStep(
                tool="resolve_dates",
                reason="Date or after-opening evidence is visible on the supplied label.",
                status="completed" if expiry.best_before or expiry.after_opening_instruction else "needs evidence",
            )
        )

    stop_reason = (
        "Stopped with explicit missing-evidence requests."
        if missing
        else "Stopped after all evidence tools required by the detected claims completed."
    )
    return InvestigationPlan(
        objective="Audit front-of-pack claims against evidence printed on the same packet.",
        steps=steps,
        missing_evidence=missing,
        stop_reason=stop_reason,
        router_model=router_model,
    )
