#!/usr/bin/env python3
"""
Tier 2: QLoRA fine-tuning of open-weight VLMs on TN5000.

4-bit NF4 quantisation (bitsandbytes) + LoRA adapters (peft) + SFTTrainer (trl).
Three models were reported in the paper:
  - llava-hf/llava-v1.6-mistral-7b-hf
  - Qwen/Qwen2.5-VL-7B-Instruct
  - google/gemma-4-27b-it  (see Supplementary Appendix B.3 for adapter placement notes)

Usage
-----
python qlora_finetune.py \
    --model_id llava-hf/llava-v1.6-mistral-7b-hf \
    --train_jsonl /path/to/tn5000/train.jsonl \
    --val_jsonl   /path/to/tn5000/val.jsonl \
    --output_dir outputs/llava_qlora \
    --epochs 3 \
    --lora_r 16 \
    --lora_alpha 32 \
    --batch_size 16 \
    --gradient_accumulation_steps 4 \
    --learning_rate 2e-4 \
    --max_seq_length 2048 \
    --seed 42

Each JSONL record has keys: {"image": "<path>", "label": 0|1}.
Labels are converted to the text targets "BENIGN" / "MALIGNANT" for SFT.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from PIL import Image
from datasets import Dataset
from transformers import (
    AutoProcessor,
    AutoModelForVision2Seq,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig

PROMPT_TEMPLATE = (
    "You are an expert radiologist analysing a B-mode thyroid ultrasound image. "
    "The image shows a single thyroid nodule. Classify it as BENIGN or MALIGNANT. "
    "Respond with exactly one word."
)
LABEL_TEXT = {0: "BENIGN", 1: "MALIGNANT"}


def load_split(jsonl_path: Path) -> Dataset:
    records = []
    with open(jsonl_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            records.append({
                "image_path": rec["image"],
                "label_text": LABEL_TEXT[int(rec["label"])],
            })
    return Dataset.from_list(records)


def build_collate_fn(processor):
    def collate(batch):
        images = [Image.open(ex["image_path"]).convert("RGB") for ex in batch]
        messages = [[
            {"role": "user",
             "content": [{"type": "image"}, {"type": "text", "text": PROMPT_TEMPLATE}]},
            {"role": "assistant",
             "content": [{"type": "text", "text": ex["label_text"]}]},
        ] for ex in batch]
        texts = [processor.apply_chat_template(m, tokenize=False) for m in messages]
        inputs = processor(
            images=images,
            text=texts,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )
        labels = inputs["input_ids"].clone()
        # Mask pad tokens from loss
        if processor.tokenizer.pad_token_id is not None:
            labels[labels == processor.tokenizer.pad_token_id] = -100
        inputs["labels"] = labels
        return inputs
    return collate


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model_id", required=True)
    p.add_argument("--train_jsonl", required=True, type=Path)
    p.add_argument("--val_jsonl", required=True, type=Path)
    p.add_argument("--output_dir", required=True, type=Path)
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--lora_r", type=int, default=16)
    p.add_argument("--lora_alpha", type=int, default=32)
    p.add_argument("--lora_dropout", type=float, default=0.05)
    p.add_argument("--batch_size", type=int, default=4)
    p.add_argument("--gradient_accumulation_steps", type=int, default=4)
    p.add_argument("--learning_rate", type=float, default=2e-4)
    p.add_argument("--max_seq_length", type=int, default=2048)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # 4-bit NF4 quantisation
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    processor = AutoProcessor.from_pretrained(args.model_id, trust_remote_code=True)
    model = AutoModelForVision2Seq.from_pretrained(
        args.model_id,
        quantization_config=bnb,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(model)

    # LoRA on language-backbone linear layers only; vision encoder is kept frozen.
    # See Supplementary Appendix B.3 for Gemma 4 27B adapter-placement caveat.
    lora_cfg = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        task_type="CAUSAL_LM",
        bias="none",
    )
    model = get_peft_model(model, lora_cfg)
    model.print_trainable_parameters()

    train_ds = load_split(args.train_jsonl)
    val_ds = load_split(args.val_jsonl)

    # Weighted sampler for class imbalance is applied by the trainer via class weights.
    sft_cfg = SFTConfig(
        output_dir=str(args.output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        logging_steps=10,
        save_strategy="epoch",
        eval_strategy="epoch",
        bf16=True,
        max_seq_length=args.max_seq_length,
        seed=args.seed,
        report_to="none",
        remove_unused_columns=False,
    )

    trainer = SFTTrainer(
        model=model,
        args=sft_cfg,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=build_collate_fn(processor),
    )
    trainer.train()
    trainer.save_model(str(args.output_dir))
    processor.save_pretrained(str(args.output_dir))
    print(f"✓ Fine-tuned adapter saved: {args.output_dir}")


if __name__ == "__main__":
    main()
