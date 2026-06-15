from packetcourt import audit_packet
from packetcourt.models import Verdict
from packetcourt.ocr import merge_extractions


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


def test_sugar_free_packet_surfaces_sweetener_and_requests_nutrition_panel():
    result = audit_packet(
        "Sugar Free\nEnriched with Extra Calcium with DHA\nReal Badam",
        (
            "Ingredients: Maltodextrin (65%), Badam, Soya Protein Isolate, Sucralose, "
            "Vitamins and Mineral Mix. Net Weight: 200g. Dates: FEB 2024 - JUL 2025."
        ),
    )
    assert by_claim(result, "Sugar Free").verdict == Verdict.CANNOT_VERIFY
    assert any("Sucralose" in evidence.text for evidence in by_claim(result, "Sugar Free").evidence)
    assert any("sugar free" in finding.headline.lower() for finding in result.persuasion_gap)
    assert result.ingredients[-1] == "Vitamins and Mineral Mix"
    assert result.expiry.visible_date_texts == ["FEB 2024", "JUL 2025"]
    assert any("visible dates" in item.lower() for item in result.investigation.missing_evidence)
    sugar_step = next(step for step in result.investigation.steps if "Sugar Free" in step.reason)
    assert sugar_step.tool == "inspect_nutrition"


def test_dynamic_front_claim_is_audited_instead_of_dropped():
    result = audit_packet("Real Badam", "Ingredients: Maltodextrin, Badam. Net Weight: 200g.")
    claim = by_claim(result, "Real Badam")
    assert claim.verdict == Verdict.CONTEXT_MISSING
    assert any("Badam" in evidence.text for evidence in claim.evidence)


def test_multiple_photo_extractions_are_labeled_and_exact_duplicates_are_skipped():
    text, status, images = merge_extractions(
        [
            ("HIGH PROTEIN", "read one"),
            ("HIGH PROTEIN", "read duplicate"),
            ("REAL BADAM", "read another panel"),
        ],
        "front",
    )
    assert "[Front photo 1]" in text
    assert "[Front photo 3]" in text
    assert text.count("HIGH PROTEIN") == 1
    assert "2 unique front photos" in status
    assert "Exact duplicate skipped" in images[1]["status"]


def test_table_style_nutrition_values_are_calculated():
    result = audit_packet(
        "SUGAR FREE",
        (
            "Nutrition Information Per 100g | Protein (g) 12 | Total Sugars | g | 0 | "
            "Added Sugar (g) 0 | Sodium (mg) 410 | Saturated Fat g 2.5 | Net Weight: 200g."
        ),
    )
    assert result.nutrition.protein_g == 12
    assert result.nutrition.total_sugar_g == 0
    assert result.nutrition.sodium_mg == 410
    assert result.whole_packet.protein_g == 24
    assert result.whole_packet.total_sugar_g == 0
    assert result.whole_packet.sodium_mg == 820


def test_basis_and_packet_without_nutrient_rows_explain_the_real_missing_evidence():
    result = audit_packet("SUGAR FREE", "Nutrition Information Per 100g. Net Weight: 200g.")
    assert result.whole_packet.calculable is False
    assert "no readable nutrient quantities" in result.whole_packet.explanation.lower()
    assert any("nutrient quantities" in item.lower() for item in result.investigation.missing_evidence)


def test_enrichment_claim_cites_visible_back_label_evidence():
    result = audit_packet(
        "Extra Calcium with DHA",
        "Nutrition per 100g: Calcium 400mg, DHA 25mg. Net Weight: 200g.",
    )
    claim = by_claim(result, "Extra Calcium with DHA")
    assert claim.verdict == Verdict.CONTEXT_MISSING
    assert any("Calcium" in evidence.text for evidence in claim.evidence)


def test_one_character_ocr_claim_mismatch_is_surfaced_conservatively():
    result = audit_packet("Real Badar", "Ingredients: ** Maltodextrin (65%), Badam, Sucralose.")
    claim = by_claim(result, "Real Badar")
    assert claim.verdict == Verdict.CANNOT_VERIFY
    assert claim.confidence == "low"
    assert any(evidence.text == "Badam" for evidence in claim.evidence)
    assert result.ingredients[0] == "Maltodextrin (65%)"
