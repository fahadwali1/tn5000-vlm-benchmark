#!/usr/bin/env python3
"""
Tier 3: Supervised deep-learning baselines on TN5000.

Architectures reported in the paper:
  - swin_tiny_patch4_window7_224 (Swin-T, best)
  - resnet50
  - efficientnet_b0

Two-phase training strategy: (1) frozen backbone for 5 epochs,
(2) full fine-tuning at LR / 10 for the remainder. Class weights inversely
proportional to class frequency. WeightedRandomSampler for balanced batches.

Usage
-----
python supervised_train.py \
    --arch swin_tiny_patch4_window7_224 \
    --data_dir /path/to/tn5000 \
    --output_dir outputs/swin_t \
    --epochs 30 \
    --batch_size 32 \
    --learning_rate 1e-4 \
    --weight_decay 1e-4 \
    --phase1_epochs 5 \
    --patience 7 \
    --seed 42

Expected directory layout:
  data_dir/
    train/benign/*.png
    train/malignant/*.png
    val/benign/*.png
    val/malignant/*.png
    test/benign/*.png
    test/malignant/*.png
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision import datasets, transforms
import timm

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def build_transforms(train: bool) -> transforms.Compose:
    if train:
        return transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomRotation(15),
            transforms.ColorJitter(brightness=0.2, contrast=0.2,
                                   saturation=0.2, hue=0.2),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ])
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])


def make_weighted_sampler(dataset) -> WeightedRandomSampler:
    targets = [label for _, label in dataset.samples]
    class_counts = np.bincount(targets)
    class_weights = 1.0 / class_counts
    sample_weights = np.array([class_weights[t] for t in targets])
    return WeightedRandomSampler(weights=sample_weights.tolist(),
                                 num_samples=len(sample_weights), replacement=True)


def set_backbone_trainable(model, trainable: bool) -> None:
    """Freeze everything except the classification head when trainable=False."""
    for name, param in model.named_parameters():
        if "head" in name or "fc" in name or "classifier" in name:
            param.requires_grad = True
        else:
            param.requires_grad = trainable


def run_epoch(model, loader, loss_fn, optimizer, device, train: bool):
    model.train() if train else model.eval()
    total_loss, total_correct, total_n = 0.0, 0, 0
    with torch.set_grad_enabled(train):
        for imgs, labels in loader:
            imgs = imgs.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            logits = model(imgs)
            loss = loss_fn(logits, labels)
            if train:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            total_loss += loss.item() * imgs.size(0)
            total_correct += (logits.argmax(1) == labels).sum().item()
            total_n += imgs.size(0)
    return total_loss / total_n, total_correct / total_n


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--arch", required=True,
                   help="timm architecture name (e.g. swin_tiny_patch4_window7_224).")
    p.add_argument("--data_dir", required=True, type=Path)
    p.add_argument("--output_dir", required=True, type=Path)
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--batch_size", type=int, default=32)
    p.add_argument("--learning_rate", type=float, default=1e-4)
    p.add_argument("--weight_decay", type=float, default=1e-4)
    p.add_argument("--phase1_epochs", type=int, default=5,
                   help="Number of initial epochs with frozen backbone.")
    p.add_argument("--patience", type=int, default=7,
                   help="Early stopping patience on val loss.")
    p.add_argument("--num_workers", type=int, default=4)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    train_ds = datasets.ImageFolder(args.data_dir / "train",
                                    transform=build_transforms(train=True))
    val_ds = datasets.ImageFolder(args.data_dir / "val",
                                  transform=build_transforms(train=False))

    # class_to_idx must be {benign: 0, malignant: 1}
    assert train_ds.class_to_idx == {"benign": 0, "malignant": 1}

    train_loader = DataLoader(train_ds, batch_size=args.batch_size,
                              sampler=make_weighted_sampler(train_ds),
                              num_workers=args.num_workers, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size,
                            shuffle=False, num_workers=args.num_workers,
                            pin_memory=True)

    # Inverse-frequency class weights
    counts = np.bincount([lbl for _, lbl in train_ds.samples])
    class_weights = torch.tensor(counts.sum() / (2 * counts), dtype=torch.float32).to(device)
    loss_fn = nn.CrossEntropyLoss(weight=class_weights)

    model = timm.create_model(args.arch, pretrained=True, num_classes=2).to(device)

    # --- Phase 1: frozen backbone ---
    set_backbone_trainable(model, trainable=False)
    params_phase1 = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(params_phase1, lr=args.learning_rate,
                                  weight_decay=args.weight_decay)

    best_val_loss = float("inf")
    patience_counter = 0
    history = []

    for epoch in range(args.epochs):
        if epoch == args.phase1_epochs:
            # --- Phase 2: full fine-tune at LR / 10 ---
            set_backbone_trainable(model, trainable=True)
            optimizer = torch.optim.AdamW(model.parameters(),
                                          lr=args.learning_rate / 10,
                                          weight_decay=args.weight_decay)

        tr_loss, tr_acc = run_epoch(model, train_loader, loss_fn,
                                    optimizer, device, train=True)
        val_loss, val_acc = run_epoch(model, val_loader, loss_fn,
                                      optimizer, device, train=False)
        history.append({"epoch": epoch + 1, "train_loss": tr_loss,
                        "train_acc": tr_acc, "val_loss": val_loss,
                        "val_acc": val_acc})
        print(f"Epoch {epoch + 1}: train_loss={tr_loss:.4f} train_acc={tr_acc:.4f} "
              f"val_loss={val_loss:.4f} val_acc={val_acc:.4f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save(model.state_dict(), args.output_dir / "best.pt")
        else:
            patience_counter += 1
            if patience_counter >= args.patience:
                print(f"  Early stopping at epoch {epoch + 1}")
                break

    with open(args.output_dir / "history.json", "w") as f:
        json.dump(history, f, indent=2)
    print(f"✓ Best model saved: {args.output_dir / 'best.pt'}")


if __name__ == "__main__":
    main()
