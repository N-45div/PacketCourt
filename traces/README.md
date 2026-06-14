---
license: cc-by-4.0
task_categories:
  - text-classification
language:
  - en
tags:
  - build-small-hackathon
  - agent-traces
  - claim-verification
  - openbmb
size_categories:
  - n<1K
---

# PacketCourt Transparent Traces

Transparent PacketCourt investigation-agent runs showing the evidence pipeline
from claim-dependent tool planning through deterministic verdicts,
whole-packet arithmetic, persuasion-gap findings, and date resolution.

These traces contain no hidden chain-of-thought. They expose auditable tool and
decision outputs suitable for debugging and evaluation. Each trace records:

- the investigation objective and selected evidence tools;
- whether a tool came from the fine-tuned router or policy fallback;
- explicit missing-evidence requests and stop reason;
- extracted evidence, calculations, verdicts, and safety limitations.
