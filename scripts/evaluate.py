from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from packetcourt import audit_packet


def load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def evaluate_case(case: dict) -> tuple[int, int, list[str]]:
    audit = audit_packet(case["front_text"], case["back_text"])
    checks: list[tuple[bool, str]] = []
    actual_claims = {claim.claim for claim in audit.claims}
    checks.append((actual_claims == set(case["expected_claims"]), "claim set"))

    verdicts = {claim.claim: claim.verdict.value for claim in audit.claims}
    for claim, expected in case.get("expected_verdicts", {}).items():
        checks.append((verdicts.get(claim) == expected, f"{claim} verdict"))

    gap_text = " ".join(
        f"{finding.headline} {finding.front_impression} {finding.quiet_context}"
        for finding in audit.persuasion_gap
    ).lower()
    for term in case.get("expected_gap_terms", []):
        checks.append((term.lower() in gap_text, f"gap contains {term}"))

    if "expected_best_before" in case:
        checks.append((audit.expiry.best_before == case["expected_best_before"], "best-before date"))
    if "expected_after_opening" in case:
        checks.append((audit.expiry.after_opening_instruction == case["expected_after_opening"], "after-opening instruction"))
    if "expected_sugar_teaspoons" in case:
        checks.append((audit.whole_packet.sugar_teaspoons == case["expected_sugar_teaspoons"], "sugar teaspoons"))

    failures = [label for passed, label in checks if not passed]
    return len(checks) - len(failures), len(checks), failures


def main() -> int:
    cases = load_cases(ROOT / "data" / "golden_cases.jsonl")
    passed = total = 0
    for case in cases:
        case_passed, case_total, failures = evaluate_case(case)
        passed += case_passed
        total += case_total
        marker = "PASS" if not failures else "FAIL"
        print(f"{marker} {case['id']} {case['title']}: {case_passed}/{case_total}")
        for failure in failures:
            print(f"  - {failure}")
    print(f"\nPacketCourt golden evaluation: {passed}/{total} checks passed across {len(cases)} cases.")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())

