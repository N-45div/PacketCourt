---
title: PacketCourt
emoji: ⚖️
colorFrom: yellow
colorTo: red
sdk: gradio
sdk_version: 5.49.1
app_file: app.py
pinned: false
license: mit
tags:
  - track:backyard
  - sponsor:openbmb
  - sponsor:openai
  - achievement:offbrand
  - build-small-hackathon
---

# PacketCourt

**The packet takes the stand.**

PacketCourt audits front-of-pack marketing claims against evidence printed on
the same Indian packaged-food label. It produces traceable, conservative
verdicts instead of an unexplained health score.

## Current MVP

- Reads front and back label photos with local OCR.
- Uses OpenBMB `MiniCPM-V-4.6` for local vision extraction when `PACKETCOURT_VLM=1`, with Tesseract fallback.
- Requests ZeroGPU only during MiniCPM-V photo extraction; text and prepared-case audits remain CPU-only.
- Serves a fully custom responsive product interface with a mounted Gradio engine.
- Detects six common front claims.
- Links claims to ingredients, nutrition, FSSAI license, and expiry evidence.
- Resolves relative dates such as `best before 6 months from packaging`.
- Produces a machine-readable evidence case.
- Refuses unsupported legal, medical, and food-safety conclusions.

## Run Locally

```bash
python -m pip install -r requirements.txt
python app.py
```

## Test

```bash
pytest
python scripts/evaluate.py
```

## Model Plan

Phase 2 integrates OpenBMB's 1.3B-parameter `MiniCPM-V-4.6` for evidence-region
discovery and OCR correction, plus a fine-tuned `MiniCPM5-1B` for constrained
claim-to-evidence mapping. Deterministic code remains responsible for numeric
calculations and final verdict triggers.

## Safety Boundary

PacketCourt does not declare products healthy, safe, illegal, or fraudulent.
It audits only the supplied label evidence and exposes uncertainty explicitly.

## Codex Attribution

The repository is being built with OpenAI Codex as the primary coding agent.
Codex is responsible for the initial architecture, deterministic audit engine,
tests, Gradio application, and deployment workflow.
