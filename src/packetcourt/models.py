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
    confidence: str = "medium"


class NutritionFacts(BaseModel):
    basis: str = "unknown"
    serving_size_g: float | None = None
    package_size_g: float | None = None
    protein_g: float | None = None
    total_sugar_g: float | None = None
    added_sugar_g: float | None = None
    sodium_mg: float | None = None
    saturated_fat_g: float | None = None


class WholePacketNutrition(BaseModel):
    calculable: bool = False
    multiplier: float | None = None
    protein_g: float | None = None
    total_sugar_g: float | None = None
    added_sugar_g: float | None = None
    sugar_teaspoons: float | None = None
    sodium_mg: float | None = None
    saturated_fat_g: float | None = None
    explanation: str = "Package size and nutrition basis are required."


class PersuasionFinding(BaseModel):
    headline: str
    front_impression: str
    quiet_context: str
    severity: str
    evidence: list[Evidence] = Field(default_factory=list)


class ExpiryInfo(BaseModel):
    packed_on: str | None = None
    best_before: str | None = None
    instruction: str | None = None
    after_opening_instruction: str | None = None
    status: str = "Not enough label evidence"


class PacketAudit(BaseModel):
    claims: list[ClaimAudit]
    nutrition: NutritionFacts
    whole_packet: WholePacketNutrition
    persuasion_gap: list[PersuasionFinding]
    ingredients: list[str]
    expiry: ExpiryInfo
    front_text: str
    back_text: str
    limitations: list[str]
