---
license: cc-by-4.0
task_categories:
  - text-classification
language:
  - en
tags:
  - build-small-hackathon
  - packetcourt
  - claim-routing
size_categories:
  - n<1K
---

# PacketCourt Evidence Router Training Set

Small, inspectable claim-routing dataset used to fine-tune
[`packetcourt-evidence-router`](https://huggingface.co/build-small-hackathon/packetcourt-evidence-router).

The five labels map packet text to the next bounded investigation tool:

- `ingredients`
- `nutrition`
- `license`
- `dates`
- `refuse_absolute`

The router only proposes a tool. PacketCourt's deterministic evidence engine
remains responsible for final verdicts and calculations.
