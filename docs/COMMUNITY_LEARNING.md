# Community Learning Loop

```mermaid
flowchart LR
    A["Packet audit"] --> R["User review"]
    R --> Q["Public feedback queue"]
    Q --> H["Evidence review"]
    H -->|reject| X["Retain as rejected trace"]
    H -->|approve| T["Versioned router training set"]
    T --> F["Fine-tune tiny evidence router"]
    F --> E["Golden-case regression evaluation"]
    E -->|pass| D["Deploy reviewed checkpoint"]
    E -->|fail| X
```

The loop is deliberately approval-gated. User feedback is valuable evidence,
but it is not automatically true. Every queued correction includes the audit,
investigation trace, and Nemotron review so a reviewer can decide whether it
should become training data.

PacketCourt's deterministic verdict engine and safety boundaries are never
rewritten by public feedback. Nemotron remains an independent reviewer rather
than a model that silently trains on its own outputs.
