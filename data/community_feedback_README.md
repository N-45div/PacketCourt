---
license: mit
tags:
- build-small-hackathon
- packetcourt
- feedback
- traces
- human-in-the-loop
---

# PacketCourt Community Feedback

This dataset is PacketCourt's public correction-driven learning queue.

Each submitted review preserves:

- the original front and back label evidence;
- PacketCourt's claim verdicts and investigation path;
- the independent Nemotron evidence-gap review;
- the user's correction or confirmation;
- candidate evidence-router examples.

## Learning policy

New records begin with:

```json
{
  "review_status": "pending_human_review",
  "training_eligible": false
}
```

Public feedback never fine-tunes a production model immediately. That would
allow accidental or malicious feedback to poison later audits. A correction
must first be checked against the supplied packet evidence. Approved records
can then be promoted into a versioned router-training release and evaluated
against PacketCourt's golden cases before deployment.

Nemotron reviews investigations and missing evidence. It is not silently
self-modified by community feedback.
