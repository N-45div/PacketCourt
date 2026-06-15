from __future__ import annotations

from .evidence_router import route_claim
from .models import InvestigationPlan, InvestigationStep


POLICY_TOOLS = {
    "Sugar Free": "inspect_nutrition",
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

def policy_tool_for(claim: str) -> str:
    if claim in POLICY_TOOLS:
        return POLICY_TOOLS[claim]
    lowered = claim.lower()
    if any(term in lowered for term in ("calcium", "dha", "protein", "sugar", "fat", "sodium")):
        return "inspect_nutrition"
    if any(term in lowered for term in ("real", "with", "contains", "ingredient", "grain", "natural")):
        return "inspect_ingredients"
    return "inspect_label_evidence"


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
        expected_tool = policy_tool_for(claim)
        if claim in POLICY_TOOLS and routed_tool and routed_tool != expected_tool:
            tool = expected_tool
            step_source = "policy guard over fine-tuned router"
        else:
            tool = routed_tool or expected_tool
            step_source = "fine-tuned router" if routed_tool else "policy fallback"
        if tool in seen:
            continue
        seen.add(tool)
        steps.append(
            InvestigationStep(
                tool=tool,
                reason=f"Required to audit the front claim: {claim}.",
                status="completed",
                source=step_source,
            )
        )

    if claim_names and not ingredients and any(policy_tool_for(name) == "inspect_ingredients" for name in claim_names):
        missing.append("A readable ingredient list")
    if claim_names and nutrition.basis == "unknown" and any(policy_tool_for(name) == "inspect_nutrition" for name in claim_names):
        missing.append("A readable nutrition panel with its measurement basis")
    elif claim_names and any(policy_tool_for(name) == "inspect_nutrition" for name in claim_names) and not any(
        value is not None
        for value in (
            nutrition.protein_g,
            nutrition.total_sugar_g,
            nutrition.added_sugar_g,
            nutrition.sodium_mg,
            nutrition.saturated_fat_g,
        )
    ):
        missing.append("Readable nutrient quantities from the nutrition table")
    if expiry.instruction and not expiry.packed_on:
        missing.append("The packing or manufacturing date needed to resolve relative shelf life")

    if expiry.best_before or expiry.instruction or expiry.after_opening_instruction or expiry.visible_date_texts:
        steps.append(
            InvestigationStep(
                tool="resolve_dates",
                reason="Date or after-opening evidence is visible on the supplied label.",
                status="completed" if expiry.best_before or expiry.after_opening_instruction else "needs evidence",
            )
        )
    if expiry.visible_date_texts and not expiry.best_before:
        missing.append("Labels identifying the visible dates as packed, manufactured, best-before, or expiry")

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
