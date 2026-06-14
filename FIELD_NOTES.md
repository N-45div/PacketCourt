# Field Notes: Building PacketCourt

## The packet takes the stand

PacketCourt began with a narrow household problem: a food packet's front is
designed to persuade, while the evidence needed to interpret that persuasion
is scattered across the back. A shopper should not need to understand serving
bases, ingredient ordering, date arithmetic, or regulatory language while
standing in a grocery aisle.

The first idea was a nutrition scanner. That was too broad and too easy to turn
into an unexplained health score. PacketCourt instead asks one auditable
question:

> Does the evidence printed on this packet support the impression created by
> its front?

## Small models as witnesses, not judges

The system deliberately separates three responsibilities:

1. OpenBMB MiniCPM-V-4.6 transcribes visible front and back label evidence.
2. A fine-tuned 4.4M-parameter PacketCourt router selects the evidence tools
   required by each detected claim.
3. Deterministic code performs calculations and produces final verdicts.

The models can read and route an investigation. They cannot silently invent a
nutrition value or override the evidence standard.

## What the investigation agent does

Each packet creates a claim-dependent investigation plan. A `NO ADDED SUGAR`
claim sends the investigation toward ingredients. `HIGH PROTEIN` requires a
nutrition panel and its measurement basis. `FSSAI APPROVED` requires licensing
evidence and a warning that registration is not a health endorsement.

The agent stops in one of two explicit states:

- all evidence tools required by the detected claims completed; or
- required evidence is missing, so the audit returns a concrete request rather
  than guessing.

Every plan, tool decision, evidence extraction, calculation, verdict, and
limitation is exported as a trace.

## A failed first fine-tune

The first evidence-router training run reached only `0.40` held-out accuracy.
The dataset was too small and its random split did not preserve every routing
class. That model was published privately but was not enabled in the product.

The corrected run balanced claim variants across five routing classes and used
a stratified held-out split. PacketCourt only enables the router after its
measured result is recorded in the model card and its suggestions remain
bounded by deterministic policy fallbacks.

## Persuasion Gap

Claim verification alone was not enough. A `HIGH PROTEIN` claim can be
technically supportable while a full packet also contains substantial sugar or
sodium. PacketCourt therefore calculates a **Persuasion Gap**: material
back-label context that competes with the impression emphasized on the front.

This is not a health score. The output cites the exact calculation and leaves
the decision with the user.

## Current evidence

- `9` unit tests pass.
- `35/35` golden-case checks pass across `10` packet cases.
- `10` transparent investigation traces are exported.
- The vision model has `1.30B` parameters.
- The fine-tuned evidence router has approximately `4.4M` parameters.
- The complete product interface is responsive and built on Gradio.

## What PacketCourt refuses to claim

PacketCourt does not declare food healthy, safe, illegal, or fraudulent. It
does not treat OCR as ground truth. It does not use an LLM to perform arithmetic
that deterministic code can perform exactly. When supplied evidence is
insufficient, the correct result is `CANNOT VERIFY`.

That refusal is not a missing feature. It is the product's standard of proof.
