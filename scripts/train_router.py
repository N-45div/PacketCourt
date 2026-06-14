from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import torch
from huggingface_hub import HfApi
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer


ROOT = Path(__file__).resolve().parents[1]
LABELS = ["ingredients", "nutrition", "license", "dates", "refuse_absolute"]
LABEL_TO_ID = {label: index for index, label in enumerate(LABELS)}


class RouterDataset(Dataset):
    def __init__(self, records, tokenizer):
        self.records = records
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.records)

    def __getitem__(self, index):
        record = self.records[index]
        encoded = self.tokenizer(
            record["text"],
            padding="max_length",
            truncation=True,
            max_length=32,
            return_tensors="pt",
        )
        return {
            "input_ids": encoded["input_ids"].squeeze(0),
            "attention_mask": encoded["attention_mask"].squeeze(0),
            "labels": torch.tensor(LABEL_TO_ID[record["label"]]),
        }


def evaluate(model, loader, device):
    model.eval()
    correct = total = 0
    with torch.no_grad():
        for batch in loader:
            labels = batch.pop("labels").to(device)
            logits = model(**{key: value.to(device) for key, value in batch.items()}).logits
            correct += (logits.argmax(dim=-1) == labels).sum().item()
            total += labels.numel()
    return correct / total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-id", default="build-small-hackathon/packetcourt-evidence-router")
    parser.add_argument("--base-model", default="google/bert_uncased_L-2_H-128_A-2")
    parser.add_argument("--epochs", type=int, default=30)
    args = parser.parse_args()

    random.seed(42)
    torch.manual_seed(42)
    records = [json.loads(line) for line in (ROOT / "data/router_training.jsonl").read_text().splitlines()]
    grouped = {label: [] for label in LABELS}
    for record in records:
        grouped[record["label"]].append(record)
    for group in grouped.values():
        random.shuffle(group)
    validation = [group.pop() for group in grouped.values()]
    training = [record for group in grouped.values() for record in group]
    random.shuffle(training)

    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base_model,
        num_labels=len(LABELS),
        id2label={index: label for index, label in enumerate(LABELS)},
        label2id=LABEL_TO_ID,
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    train_loader = DataLoader(RouterDataset(training, tokenizer), batch_size=8, shuffle=True)
    validation_loader = DataLoader(RouterDataset(validation, tokenizer), batch_size=5)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)

    for epoch in range(args.epochs):
        model.train()
        for batch in train_loader:
            optimizer.zero_grad()
            labels = batch.pop("labels").to(device)
            loss = model(**{key: value.to(device) for key, value in batch.items()}, labels=labels).loss
            loss.backward()
            optimizer.step()
        print(f"epoch={epoch + 1} validation_accuracy={evaluate(model, validation_loader, device):.3f}")

    output = ROOT / "router_model"
    model.save_pretrained(output)
    tokenizer.save_pretrained(output)
    score = evaluate(model, validation_loader, device)
    card = f"""---
license: apache-2.0
base_model: {args.base_model}
tags:
- text-classification
- build-small-hackathon
- packetcourt
- fine-tuned
---

# PacketCourt Evidence Router

A {sum(parameter.numel() for parameter in model.parameters()):,}-parameter fine-tuned classifier used by
PacketCourt's investigation agent to choose the next evidence tool for a packet claim.

Labels: `{", ".join(LABELS)}`.

Held-out validation accuracy: `{score:.3f}` on a small PacketCourt-specific routing set.
The router proposes an investigation tool; deterministic code remains responsible for final verdicts.
"""
    (output / "README.md").write_text(card)

    api = HfApi()
    api.create_repo(args.repo_id, repo_type="model", private=True, exist_ok=True)
    api.upload_folder(
        repo_id=args.repo_id,
        repo_type="model",
        folder_path=output,
        commit_message="feat: publish PacketCourt fine-tuned evidence router",
    )
    print(f"published={args.repo_id} validation_accuracy={score:.3f}")


if __name__ == "__main__":
    main()
