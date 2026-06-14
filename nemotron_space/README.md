---
title: PacketCourt Nemotron Reviewer
emoji: 🟩
colorFrom: green
colorTo: gray
sdk: gradio
sdk_version: 5.49.1
app_file: app.py
pinned: false
license: other
tags:
  - build-small-hackathon
  - sponsor:nvidia
  - nemotron
  - agent
  - zerogpu
models:
  - nvidia/Nemotron-Mini-4B-Instruct
---

# PacketCourt Nemotron Reviewer

Private ZeroGPU companion that uses NVIDIA Nemotron Mini 4B as an independent
evidence-gap reviewer for PacketCourt investigations.

Nemotron may request missing packet evidence or confirm that the bounded
investigation plan is complete. It never issues or overrides PacketCourt's
deterministic verdicts.
