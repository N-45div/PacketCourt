from __future__ import annotations

import re

from .models import ClaimAudit, Evidence, PacketAudit, Verdict
from .parser import extract_claims, extract_ingredients, parse_expiry, parse_nutrition


ADDED_SUGAR_TERMS = {
    "sugar",
    "glucose",
    "glucose syrup",
    "corn syrup",
    "high fructose corn syrup",
    "invert syrup",
    "cane sugar",
    "brown sugar",
    "jaggery",
    "honey",
    "dextrose",
    "fructose",
    "sucrose",
}


def _ingredient_evidence(ingredients: list[str], matches: list[str]) -> list[Evidence]:
    return [Evidence(source="ingredient list", text=item) for item in matches]


def _audit_claim(claim: str, back_text: str, ingredients: list[str], nutrition) -> ClaimAudit:
    lowered_ingredients = [item.lower() for item in ingredients]

    if claim == "No Added Sugar":
        matches = [
            original
            for original, lowered in zip(ingredients, lowered_ingredients)
            if any(re.search(rf"\b{re.escape(term)}\b", lowered) for term in ADDED_SUGAR_TERMS)
        ]
        if matches:
            return ClaimAudit(
                claim=claim,
                verdict=Verdict.CONTRADICTED,
                summary="The provided ingredient list names one or more added-sugar ingredients.",
                evidence=_ingredient_evidence(ingredients, matches),
                caveat="This verdict only checks the supplied label text; it is not a laboratory analysis.",
            )
        if ingredients:
            return ClaimAudit(
                claim=claim,
                verdict=Verdict.SUPPORTED,
                summary="No common added-sugar term was found in the provided ingredient list.",
                evidence=[Evidence(source="ingredient list", text=", ".join(ingredients))],
                caveat="Unrecognized sweeteners or incomplete OCR may change this result.",
            )

    if claim == "Multigrain":
        grain_terms = ("wheat", "rice", "oat", "barley", "ragi", "millet", "jowar", "bajra", "maize", "corn")
        matches = [item for item in ingredients if any(term in item.lower() for term in grain_terms)]
        if len(matches) >= 2:
            first = ingredients[0] if ingredients else ""
            return ClaimAudit(
                claim=claim,
                verdict=Verdict.CONTEXT_MISSING if "refined" in first.lower() else Verdict.SUPPORTED,
                summary=(
                    "Multiple grains are listed, but refined grain appears first."
                    if "refined" in first.lower()
                    else "Multiple grain ingredients are present in the supplied ingredient list."
                ),
                evidence=_ingredient_evidence(ingredients, matches),
                caveat="Ingredient order indicates relative quantity, but exact grain percentages may be unavailable.",
            )

    if claim == "High Protein":
        if nutrition.protein_g is not None:
            if nutrition.basis == "unknown":
                return ClaimAudit(
                    claim=claim,
                    verdict=Verdict.CANNOT_VERIFY,
                    summary="Protein is listed, but its measurement basis could not be determined.",
                    evidence=[Evidence(source="nutrition panel", text=f"Protein {nutrition.protein_g:g}g")],
                )
            return ClaimAudit(
                claim=claim,
                verdict=Verdict.CONTEXT_MISSING,
                summary="The protein quantity is visible, but claim compliance depends on product category and applicable rules.",
                evidence=[
                    Evidence(
                        source="nutrition panel",
                        text=f"Protein {nutrition.protein_g:g}g ({nutrition.basis})",
                    )
                ],
                caveat="PacketCourt does not make a regulatory-compliance determination in this prototype.",
            )

    if claim == "No Preservatives":
        preservative_pattern = r"\b(?:preservative|sodium benzoate|potassium sorbate|ins\s*2\d{2})\b"
        matches = [item for item in ingredients if re.search(preservative_pattern, item, re.IGNORECASE)]
        if matches:
            return ClaimAudit(
                claim=claim,
                verdict=Verdict.CONTRADICTED,
                summary="The ingredient list contains a recognizable preservative term or code.",
                evidence=_ingredient_evidence(ingredients, matches),
            )
        if ingredients:
            return ClaimAudit(
                claim=claim,
                verdict=Verdict.SUPPORTED,
                summary="No recognizable preservative term was found in the supplied ingredient list.",
                evidence=[Evidence(source="ingredient list", text=", ".join(ingredients))],
                caveat="Incomplete OCR or unfamiliar additive codes may change this result.",
            )

    if claim == "100% Natural":
        return ClaimAudit(
            claim=claim,
            verdict=Verdict.CANNOT_VERIFY,
            summary="An absolute naturalness claim cannot be established from package text alone.",
            evidence=[Evidence(source="front claim", text=claim)],
            caveat="PacketCourt refuses to infer product composition beyond the supplied label.",
        )

    if claim == "FSSAI Approved":
        license_match = re.search(r"\bfssai\b.{0,30}(\d{14})", back_text, re.IGNORECASE)
        evidence = [Evidence(source="back label", text=f"FSSAI license number {license_match.group(1)}")] if license_match else []
        return ClaimAudit(
            claim=claim,
            verdict=Verdict.CONTEXT_MISSING,
            summary="An FSSAI license indicates regulatory registration; it is not a health endorsement.",
            evidence=evidence or [Evidence(source="front claim", text=claim)],
        )

    return ClaimAudit(
        claim=claim,
        verdict=Verdict.CANNOT_VERIFY,
        summary="The supplied back-label evidence is insufficient for this claim.",
        evidence=[Evidence(source="front claim", text=claim)],
    )


def audit_packet(front_text: str, back_text: str) -> PacketAudit:
    claims = extract_claims(front_text)
    ingredients = extract_ingredients(back_text)
    nutrition = parse_nutrition(back_text)
    expiry = parse_expiry(back_text)

    limitations = [
        "PacketCourt audits only the text and images supplied by the user.",
        "Verdicts are evidence summaries, not legal, medical, or food-safety determinations.",
        "Users should verify low-confidence OCR against the physical packet.",
    ]

    return PacketAudit(
        claims=[_audit_claim(claim, back_text, ingredients, nutrition) for claim in claims],
        nutrition=nutrition,
        ingredients=ingredients,
        expiry=expiry,
        front_text=front_text,
        back_text=back_text,
        limitations=limitations,
    )

