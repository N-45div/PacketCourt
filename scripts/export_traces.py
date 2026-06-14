from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from packetcourt import audit_packet


def main() -> None:
    cases = [json.loads(line) for line in (ROOT / "data" / "golden_cases.jsonl").read_text().splitlines() if line.strip()]
    target = ROOT / "traces" / "packetcourt_traces.jsonl"
    target.parent.mkdir(exist_ok=True)
    records = []
    for case in cases:
        audit = audit_packet(case["front_text"], case["back_text"])
        records.append(
            {
                "trace_id": f"trace-{case['id']}",
                "case_id": case["id"],
                "input": {"front_text": case["front_text"], "back_text": case["back_text"]},
                "steps": [
                    {"name": "detect_front_claims", "output": [claim.claim for claim in audit.claims]},
                    {"name": "extract_back_evidence", "output": {"ingredients": audit.ingredients, "nutrition": audit.nutrition.model_dump()}},
                    {"name": "calculate_whole_packet", "output": audit.whole_packet.model_dump()},
                    {"name": "audit_claims", "output": [claim.model_dump(mode="json") for claim in audit.claims]},
                    {"name": "surface_persuasion_gap", "output": [finding.model_dump() for finding in audit.persuasion_gap]},
                    {"name": "resolve_dates", "output": audit.expiry.model_dump()},
                ],
                "limitations": audit.limitations,
            }
        )
    target.write_text("\n".join(json.dumps(record) for record in records) + "\n")
    print(f"Wrote {len(records)} transparent traces to {target}")


if __name__ == "__main__":
    main()

