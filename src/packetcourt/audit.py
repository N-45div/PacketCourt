from __future__ import annotations

import re

from .models import ClaimAudit, Evidence, PacketAudit, PersuasionFinding, Verdict
from .parser import calculate_whole_packet, extract_claims, extract_ingredients, parse_expiry, parse_nutrition


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
                confidence="high",
            )
        if ingredients:
            return ClaimAudit(
                claim=claim,
                verdict=Verdict.SUPPORTED,
                summary="No common added-sugar term was found in the provided ingredient list.",
                evidence=[Evidence(source="ingredient list", text=", ".join(ingredients))],
                caveat="Unrecognized sweeteners or incomplete OCR may change this result.",
                confidence="medium",
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
                confidence="high",
            )

    if claim == "High Protein":
        if nutrition.protein_g is not None:
            if nutrition.basis == "unknown":
                return ClaimAudit(
                    claim=claim,
                    verdict=Verdict.CANNOT_VERIFY,
                    summary="Protein is listed, but its measurement basis could not be determined.",
                    evidence=[Evidence(source="nutrition panel", text=f"Protein {nutrition.protein_g:g}g")],
                    confidence="low",
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
                confidence="medium",
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
                confidence="high",
            )
        if ingredients:
            return ClaimAudit(
                claim=claim,
                verdict=Verdict.SUPPORTED,
                summary="No recognizable preservative term was found in the supplied ingredient list.",
                evidence=[Evidence(source="ingredient list", text=", ".join(ingredients))],
                caveat="Incomplete OCR or unfamiliar additive codes may change this result.",
                confidence="medium",
            )

    if claim == "100% Natural":
        return ClaimAudit(
            claim=claim,
            verdict=Verdict.CANNOT_VERIFY,
            summary="An absolute naturalness claim cannot be established from package text alone.",
            evidence=[Evidence(source="front claim", text=claim)],
            caveat="PacketCourt refuses to infer product composition beyond the supplied label.",
            confidence="high",
        )

    if claim == "FSSAI Approved":
        license_match = re.search(r"\bfssai\b.{0,30}(\d{14})", back_text, re.IGNORECASE)
        evidence = [Evidence(source="back label", text=f"FSSAI license number {license_match.group(1)}")] if license_match else []
        return ClaimAudit(
            claim=claim,
            verdict=Verdict.CONTEXT_MISSING,
            summary="An FSSAI license indicates regulatory registration; it is not a health endorsement.",
            evidence=evidence or [Evidence(source="front claim", text=claim)],
            confidence="high" if license_match else "medium",
        )

    if claim == "Baked Not Fried":
        return ClaimAudit(
            claim=claim,
            verdict=Verdict.CONTEXT_MISSING,
            summary="The preparation claim does not establish that the complete packet is low in fat, sodium, or calories.",
            evidence=[Evidence(source="front claim", text=claim)],
            caveat="Review the nutrition panel and ingredient list for the complete product context.",
            confidence="high",
        )

    if claim == "Zero Trans Fat":
        trans_match = re.search(r"\btrans[\s-]*fat\b[^0-9]{0,20}(0(?:\.0+)?)\s*g\b", back_text, re.IGNORECASE)
        return ClaimAudit(
            claim=claim,
            verdict=Verdict.SUPPORTED if trans_match else Verdict.CANNOT_VERIFY,
            summary=(
                "The supplied nutrition panel reports 0g trans fat."
                if trans_match
                else "No explicit trans-fat quantity was found in the supplied back-label text."
            ),
            evidence=[
                Evidence(source="nutrition panel", text=trans_match.group(0))
                if trans_match
                else Evidence(source="front claim", text=claim)
            ],
            caveat="A zero declaration may still be subject to applicable rounding rules.",
            confidence="high" if trans_match else "low",
        )

    if claim == "Whole Grain":
        whole_matches = [item for item in ingredients if "whole" in item.lower() and any(g in item.lower() for g in ("wheat", "grain", "oat"))]
        first = ingredients[0] if ingredients else ""
        if whole_matches:
            return ClaimAudit(
                claim=claim,
                verdict=Verdict.CONTEXT_MISSING if "refined" in first.lower() else Verdict.SUPPORTED,
                summary=(
                    "Whole grain is present, but refined grain appears first."
                    if "refined" in first.lower()
                    else "A whole-grain ingredient is present in the supplied ingredient list."
                ),
                evidence=_ingredient_evidence(ingredients, whole_matches + ([first] if first and first not in whole_matches else [])),
                confidence="high",
            )

    return ClaimAudit(
        claim=claim,
        verdict=Verdict.CANNOT_VERIFY,
        summary="The supplied back-label evidence is insufficient for this claim.",
        evidence=[Evidence(source="front claim", text=claim)],
        confidence="low",
    )


def _persuasion_gap(claims: list[ClaimAudit], ingredients: list[str], whole_packet) -> list[PersuasionFinding]:
    findings: list[PersuasionFinding] = []
    claim_names = {claim.claim for claim in claims}
    if "High Protein" in claim_names and whole_packet.sugar_teaspoons is not None and whole_packet.sugar_teaspoons >= 5:
        findings.append(
            PersuasionFinding(
                headline="Protein leads. Whole-packet sugar stays quiet.",
                front_impression="The front positions protein as the packet's defining fact.",
                quiet_context=f"The complete packet contains about {whole_packet.sugar_teaspoons:g} teaspoons of total sugar.",
                severity="high" if whole_packet.sugar_teaspoons >= 10 else "medium",
                evidence=[
                    Evidence(source="whole-packet calculation", text=f"Total sugar {whole_packet.total_sugar_g:g}g"),
                    Evidence(source="conversion", text=f"{whole_packet.total_sugar_g:g}g ÷ 4 = {whole_packet.sugar_teaspoons:g} teaspoons"),
                ],
            )
        )
    if claim_names.intersection({"High Protein", "Baked Not Fried", "Multigrain", "Whole Grain"}) and whole_packet.sodium_mg is not None and whole_packet.sodium_mg >= 600:
        findings.append(
            PersuasionFinding(
                headline="A positive front claim competes with substantial sodium.",
                front_impression="The front emphasizes a favorable product attribute.",
                quiet_context=f"The complete packet calculates to approximately {whole_packet.sodium_mg:g}mg sodium.",
                severity="high" if whole_packet.sodium_mg >= 1200 else "medium",
                evidence=[Evidence(source="whole-packet calculation", text=f"Sodium {whole_packet.sodium_mg:g}mg")],
            )
        )
    if claim_names.intersection({"Multigrain", "Whole Grain"}) and ingredients and "refined" in ingredients[0].lower():
        findings.append(
            PersuasionFinding(
                headline="Grain variety is prominent. The first ingredient is refined.",
                front_impression="The front suggests a grain-forward product.",
                quiet_context=f"The ingredient list begins with “{ingredients[0]}”.",
                severity="medium",
                evidence=[Evidence(source="first ingredient", text=ingredients[0])],
            )
        )
    if "FSSAI Approved" in claim_names:
        findings.append(
            PersuasionFinding(
                headline="Registration language can look like a health endorsement.",
                front_impression="“FSSAI Approved” may imply the product has been endorsed as healthy.",
                quiet_context="An FSSAI license identifies regulatory registration; it is not a nutrition recommendation.",
                severity="medium",
                evidence=[Evidence(source="claim interpretation", text="FSSAI registration is not a health score.")],
            )
        )
    return findings


def audit_packet(front_text: str, back_text: str) -> PacketAudit:
    claims = extract_claims(front_text)
    ingredients = extract_ingredients(back_text)
    nutrition = parse_nutrition(back_text)
    whole_packet = calculate_whole_packet(nutrition)
    expiry = parse_expiry(back_text)
    claim_audits = [_audit_claim(claim, back_text, ingredients, nutrition) for claim in claims]

    limitations = [
        "PacketCourt audits only the text and images supplied by the user.",
        "Verdicts are evidence summaries, not legal, medical, or food-safety determinations.",
        "Users should verify low-confidence OCR against the physical packet.",
    ]

    return PacketAudit(
        claims=claim_audits,
        nutrition=nutrition,
        whole_packet=whole_packet,
        persuasion_gap=_persuasion_gap(claim_audits, ingredients, whole_packet),
        ingredients=ingredients,
        expiry=expiry,
        front_text=front_text,
        back_text=back_text,
        limitations=limitations,
    )
