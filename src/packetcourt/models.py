from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Verdict(StrEnum):
    SUPPORTED = "SUPPORTED BY PROVIDED LABEL"
    CONTRADICTED = "CONTRADICTED BY PROVIDED LABEL"
    CONTEXT_MISSING = "TECHNICALLY TRUE, CONTEXT MISSING"
    CANNOT_VERIFY = "CANNOT VERIFY"


class Evidence(BaseModel):
    source: str
    text: str


class ClaimAudit(BaseModel):
    claim: str
    verdict: Verdict
    summary: str
    evidence: list[Evidence] = Field(default_factory=list)
    caveat: str = ""


class NutritionFacts(BaseModel):
    basis: str = "unknown"
    serving_size_g: float | None = None
    package_size_g: float | None = None
    protein_g: float | None = None
    total_sugar_g: float | None = None
    added_sugar_g: float | None = None
    sodium_mg: float | None = None
    saturated_fat_g: float | None = None


class ExpiryInfo(BaseModel):
    packed_on: str | None = None
    best_before: str | None = None
    instruction: str | None = None
    status: str = "Not enough label evidence"


class PacketAudit(BaseModel):
    claims: list[ClaimAudit]
    nutrition: NutritionFacts
    ingredients: list[str]
    expiry: ExpiryInfo
    front_text: str
    back_text: str
    limitations: list[str]

