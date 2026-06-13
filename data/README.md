---
license: cc-by-4.0
task_categories:
  - text-classification
  - question-answering
language:
  - en
tags:
  - build-small-hackathon
  - food-labels
  - claim-verification
  - india
  - evaluation
size_categories:
  - n<1K
---

# PacketCourt Golden Cases

A small evidence-first evaluation set for auditing front-of-pack claims against
the text printed on the same Indian packaged-food label.

Each record contains:

- front-label claim text
- back-label evidence text
- expected claims and conservative verdicts
- expected persuasion-gap concepts
- expected deterministic date or whole-packet calculations

The initial set is intentionally small and hand-audited. It is a regression and
demonstration asset, not a representation of all Indian packaged foods.

