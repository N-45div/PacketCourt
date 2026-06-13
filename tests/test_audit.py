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

