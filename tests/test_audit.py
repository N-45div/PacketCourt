from packetcourt import audit_packet
from packetcourt.models import Verdict


def by_claim(result, name):
    return next(claim for claim in result.claims if claim.claim == name)


def test_no_added_sugar_is_contradicted_by_glucose_syrup():
    result = audit_packet(
        "NO ADDED SUGAR",
        "Ingredients: rolled oats, glucose syrup, peanuts. Nutrition per 100g: Total Sugar 18g.",
    )
    assert by_claim(result, "No Added Sugar").verdict == Verdict.CONTRADICTED


def test_multigrain_exposes_refined_flour_context():
    result = audit_packet(
        "MULTIGRAIN",
        "Ingredients: refined wheat flour, oats, ragi flour, salt.",
    )
    assert by_claim(result, "Multigrain").verdict == Verdict.CONTEXT_MISSING


def test_absolute_natural_claim_is_refused():
    result = audit_packet("100% NATURAL", "Ingredients: chickpea flour, salt.")
    assert by_claim(result, "100% Natural").verdict == Verdict.CANNOT_VERIFY


def test_relative_best_before_date_is_resolved():
    result = audit_packet(
        "HIGH PROTEIN",
        "PKD: 13 JUN 26. Best before 6 months from packaging. Nutrition per 100g: Protein 12g.",
    )
    assert result.expiry.best_before == "2026-12-13"


def test_fssai_claim_is_not_treated_as_health_endorsement():
    result = audit_packet(
        "FSSAI APPROVED",
        "FSSAI Lic. No. 12345678901234. Ingredients: oats.",
    )
    audit = by_claim(result, "FSSAI Approved")
    assert audit.verdict == Verdict.CONTEXT_MISSING
    assert "not a health endorsement" in audit.summary


def test_whole_packet_nutrition_exposes_persuasion_gap():
    result = audit_packet(
        "HIGH PROTEIN",
        (
            "Ingredients: oats, sugar. Nutrition information per 100g: Protein 12g, "
            "Total Sugars 22g, Sodium 410mg. Net weight 300g."
        ),
    )
    assert result.whole_packet.total_sugar_g == 66
    assert result.whole_packet.sugar_teaspoons == 16.5
    assert result.whole_packet.sodium_mg == 1230
    assert any("sugar" in finding.headline.lower() for finding in result.persuasion_gap)
    assert any("sodium" in finding.headline.lower() for finding in result.persuasion_gap)


def test_baked_and_whole_grain_claims_keep_material_context():
    result = audit_packet(
        "BAKED NOT FRIED | WHOLE GRAIN | ZERO TRANS FAT",
        (
            "Ingredients: refined wheat flour, whole wheat flour, oil, salt. "
            "Nutrition per 100g: Sodium 780mg, Trans Fat 0g. Net weight 180g."
        ),
    )
    assert by_claim(result, "Baked Not Fried").verdict == Verdict.CONTEXT_MISSING
    assert by_claim(result, "Whole Grain").verdict == Verdict.CONTEXT_MISSING
    assert by_claim(result, "Zero Trans Fat").verdict == Verdict.SUPPORTED
    assert any("refined" in finding.quiet_context.lower() for finding in result.persuasion_gap)


def test_after_opening_instruction_is_extracted():
    result = audit_packet(
        "NO PRESERVATIVES",
        "Ingredients: tomato, salt. Use by: 08 JUL 2026. Consume within 3 days after opening.",
    )
    assert result.expiry.after_opening_instruction == "Consume within 3 days after opening"


def test_investigation_requests_missing_evidence_and_stops_explicitly():
    result = audit_packet("HIGH PROTEIN", "Protein 9g.")
    assert any(step.tool == "inspect_nutrition" for step in result.investigation.steps)
    assert any("nutrition panel" in item.lower() for item in result.investigation.missing_evidence)
    assert "missing-evidence" in result.investigation.stop_reason
    assert result.agent_review.status == "NOT_REQUESTED"
