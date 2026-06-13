from __future__ import annotations

import calendar
import re
from datetime import date

from .models import ExpiryInfo, NutritionFacts, WholePacketNutrition


CLAIM_PATTERNS: list[tuple[str, str]] = [
    ("High Protein", r"\bhigh[\s-]*protein\b"),
    ("No Added Sugar", r"\bno[\s-]*added[\s-]*sugar\b"),
    ("Multigrain", r"\bmulti[\s-]*grain\b"),
    ("100% Natural", r"\b100\s*%\s*natural\b"),
    ("FSSAI Approved", r"\bfssai[\s-]*approved\b"),
    ("No Preservatives", r"\bno[\s-]*preservatives?\b"),
    ("Baked Not Fried", r"\bbaked[\s,/-]*not[\s-]*fried\b"),
    ("Zero Trans Fat", r"\b(?:zero|0)\s*(?:g\s*)?trans[\s-]*fat\b"),
    ("Whole Grain", r"\b(?:made\s+with\s+)?whole[\s-]*grains?\b"),
]


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def extract_claims(front_text: str) -> list[str]:
    text = normalize_space(front_text).lower()
    return [name for name, pattern in CLAIM_PATTERNS if re.search(pattern, text)]


def _number_after(label: str, text: str, unit: str) -> float | None:
    pattern = rf"\b{label}\b[^0-9]{{0,24}}(\d+(?:\.\d+)?)\s*{unit}\b"
    match = re.search(pattern, text, re.IGNORECASE)
    return float(match.group(1)) if match else None


def parse_nutrition(back_text: str) -> NutritionFacts:
    text = normalize_space(back_text)
    basis = "unknown"
    if re.search(r"\bper\s*100\s*g\b", text, re.IGNORECASE):
        basis = "per 100g"
    elif re.search(r"\bper\s*serving\b", text, re.IGNORECASE):
        basis = "per serving"

    return NutritionFacts(
        basis=basis,
        serving_size_g=_number_after(r"serving\s*size", text, "g"),
        package_size_g=_number_after(r"net\s*(?:weight|wt)", text, "g"),
        protein_g=_number_after("protein", text, "g"),
        total_sugar_g=_number_after(r"total\s*sugars?", text, "g"),
        added_sugar_g=_number_after(r"added\s*sugars?", text, "g"),
        sodium_mg=_number_after("sodium", text, "mg"),
        saturated_fat_g=_number_after(r"saturated\s*fat", text, "g"),
    )


def calculate_whole_packet(nutrition: NutritionFacts) -> WholePacketNutrition:
    multiplier = None
    explanation = "Package size and nutrition basis are required."
    if nutrition.package_size_g and nutrition.basis == "per 100g":
        multiplier = nutrition.package_size_g / 100
        explanation = f"Calculated from {nutrition.basis} values across a {nutrition.package_size_g:g}g packet."
    elif nutrition.package_size_g and nutrition.serving_size_g and nutrition.basis == "per serving":
        multiplier = nutrition.package_size_g / nutrition.serving_size_g
        explanation = (
            f"Calculated from {nutrition.basis} values across approximately {multiplier:.1f} servings "
            f"in a {nutrition.package_size_g:g}g packet."
        )
    if multiplier is None:
        return WholePacketNutrition(explanation=explanation)

    def scale(value: float | None) -> float | None:
        return round(value * multiplier, 1) if value is not None else None

    total_sugar = scale(nutrition.total_sugar_g)
    return WholePacketNutrition(
        calculable=True,
        multiplier=round(multiplier, 2),
        protein_g=scale(nutrition.protein_g),
        total_sugar_g=total_sugar,
        added_sugar_g=scale(nutrition.added_sugar_g),
        sugar_teaspoons=round(total_sugar / 4, 1) if total_sugar is not None else None,
        sodium_mg=scale(nutrition.sodium_mg),
        saturated_fat_g=scale(nutrition.saturated_fat_g),
        explanation=explanation,
    )


def extract_ingredients(back_text: str) -> list[str]:
    match = re.search(
        r"\bingredients?\s*:\s*(.+?)(?=\b(?:nutrition|allergen|contains|best before|mfd|pkd|manufactured|packed)\b|$)",
        normalize_space(back_text),
        re.IGNORECASE,
    )
    if not match:
        return []
    return [item.strip(" .") for item in re.split(r"[,;]", match.group(1)) if item.strip()]


def _parse_date(value: str) -> date | None:
    clean = value.strip().upper().replace(".", " ").replace("-", " ").replace("/", " ")
    formats = [
        r"(?P<day>\d{1,2})\s+(?P<month>\d{1,2})\s+(?P<year>\d{2,4})",
        r"(?P<day>\d{1,2})\s+(?P<month>[A-Z]{3,9})\s+(?P<year>\d{2,4})",
    ]
    for pattern in formats:
        match = re.search(pattern, clean)
        if not match:
            continue
        year = int(match.group("year"))
        year += 2000 if year < 100 else 0
        month_raw = match.group("month")
        if month_raw.isdigit():
            month = int(month_raw)
        else:
            month = next(
                (i for i, name in enumerate(calendar.month_abbr) if name and month_raw.startswith(name.upper())),
                0,
            )
        try:
            return date(year, month, int(match.group("day")))
        except ValueError:
            return None
    return None


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def parse_expiry(back_text: str) -> ExpiryInfo:
    text = normalize_space(back_text)
    packed_match = re.search(
        r"\b(?:pkd|packed(?:\s+on)?|mfd|manufactured(?:\s+on)?)\s*[:\-]?\s*"
        r"(\d{1,2}[\s/\-.]+(?:\d{1,2}|[A-Za-z]{3,9})[\s/\-.]+\d{2,4})",
        text,
        re.IGNORECASE,
    )
    packed = _parse_date(packed_match.group(1)) if packed_match else None

    direct_match = re.search(
        r"\b(?:exp|expiry|use\s+by|best\s+before)\s*[:\-]?\s*"
        r"(\d{1,2}[\s/\-.]+(?:\d{1,2}|[A-Za-z]{3,9})[\s/\-.]+\d{2,4})",
        text,
        re.IGNORECASE,
    )
    best_before = _parse_date(direct_match.group(1)) if direct_match else None

    relative_match = re.search(
        r"\bbest\s+before\s+(\d+)\s+months?\s+from\s+(?:packaging|packing|manufacture|manufacturing)\b",
        text,
        re.IGNORECASE,
    )
    instruction = relative_match.group(0) if relative_match else None
    if packed and relative_match:
        best_before = _add_months(packed, int(relative_match.group(1)))

    if best_before:
        status = f"Best-before evidence resolves to {best_before.isoformat()}"
    elif instruction and not packed:
        status = "Relative shelf-life found, but the starting date is missing"
    else:
        status = "No resolvable best-before date found"

    after_opening_match = re.search(
        r"\b(?:consume|use)\s+within\s+\d+\s+(?:hours?|days?|weeks?)\s+(?:after|of)\s+opening\b",
        text,
        re.IGNORECASE,
    )
    return ExpiryInfo(
        packed_on=packed.isoformat() if packed else None,
        best_before=best_before.isoformat() if best_before else None,
        instruction=instruction,
        after_opening_instruction=after_opening_match.group(0) if after_opening_match else None,
        status=status,
    )
