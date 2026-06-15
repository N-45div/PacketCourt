import sys
from pathlib import Path

from packetcourt.models import AgentReview

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app


def test_run_audit_validates_nemotron_dict_into_agent_review(monkeypatch):
    monkeypatch.setattr(app, "nemotron_is_configured", lambda: True)
    monkeypatch.setattr(
        app,
        "nemotron_review",
        lambda snapshot: {
            "status": "COMPLETE",
            "priority": "Supplementary wording that should be normalized.",
            "evidence_request": "",
            "rationale": "All claim evidence paths completed.",
            "model": "nvidia/Nemotron-Mini-4B-Instruct",
        },
    )

    result = app.run_audit("SUGAR FREE", "Nutrition per 100g: Total Sugars 0g. Net Weight 200g.")

    assert isinstance(result.agent_review, AgentReview)
    assert result.agent_review.status == "COMPLETE"
    assert result.agent_review.priority == "No additional claim-resolving evidence is required."


def test_run_audit_preserves_nemotron_validation_error(monkeypatch):
    monkeypatch.setattr(app, "nemotron_is_configured", lambda: True)
    monkeypatch.setattr(app, "nemotron_review", lambda snapshot: "not a review object")

    result = app.run_audit("SUGAR FREE", "Nutrition per 100g: Total Sugars 0g. Net Weight 200g.")

    assert isinstance(result.agent_review, AgentReview)
    assert result.agent_review.status == "UNAVAILABLE"
    assert "ValidationError" in result.agent_review.rationale
