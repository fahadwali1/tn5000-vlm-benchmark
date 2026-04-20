# TN5000 VLM Benchmark

**Parameter-Efficient Fine-Tuning Corrects Specificity Collapse in Zero-Shot Vision-Language Models for Thyroid Ultrasound Classification**

Ahmed F.W., Ahmed F.W., Moftah B. (2026). *npj Digital Medicine*, [DOI to be assigned].

## Overview

This repository contains the full benchmarking pipeline for a three-tier evaluation on the public TN5000 thyroid ultrasound dataset:

1. **Tier 1 — Zero-shot VLMs.** 12 frontier vision-language models × 3 prompt strategies (36 configurations), accessed via the OpenRouter API gateway.
2. **Tier 2 — QLoRA fine-tuned VLMs.** 3 open-weight VLMs adapted using 4-bit NF4 quantisation + LoRA on the TN5000 training split.
3. **Tier 3 — Supervised DL baselines.** ResNet-50, EfficientNet-B0, and Swin-T trained from ImageNet pretrained weights.

All three tiers are evaluated on the same 1,000-image held-out test set (731 malignant, 269 benign).

## Key findings

| Paradigm | Best model | Accuracy | Specificity | AUC-ROC | MCC |
|---|---|---|---|---|---|
| Zero-shot VLM | Qwen3-VL-235B | 74.5% | 10.0% | N/A | 0.13 |
| QLoRA fine-tuned VLM | LLaVA-NeXT 7B | 87.1% | 84.4% | 0.938 | 0.693 |
| Supervised DL | Swin-T | 85.6% | 86.6% | 0.937 | 0.672 |

- Zero-shot VLMs: median specificity 13.8% across 12 models
- QLoRA: corrected specificity in LLaVA-NeXT (+70.6 percentage points), failed entirely in Gemma 4 27B
- Supervised Swin-T: comparable performance to fine-tuned LLaVA-NeXT (p = 0.33) at 30× faster training

## Repository structure

```
.
├── scripts/
│   ├── zero_shot_inference.py        # Tier 1: OpenRouter API calls
│   ├── qlora_finetune.py             # Tier 2: QLoRA fine-tuning
│   ├── supervised_train.py           # Tier 3: ResNet/EfficientNet/Swin-T
│   ├── evaluate.py                   # All metrics, bootstrap CIs, MCC
│   ├── parse_outputs.py              # 3-level VLM response parsing pipeline
│   └── build_manuscript.py           # Reproducible manuscript build (python-docx)
├── prompts/
│   ├── baseline.txt                  # Direct classification prompt
│   ├── chain_of_thought.txt          # Systematic feature evaluation prompt
│   └── ti_rads_guided.txt            # ACR TI-RADS scoring prompt
├── results/
│   ├── zero_shot_predictions.csv     # 36,000 predictions (12 models × 3 prompts × 1,000)
│   ├── finetuned_predictions.csv     # 3,000 predictions (3 models × 1,000)
│   ├── supervised_predictions.csv    # 3,000 predictions (3 models × 1,000)
│   └── summary_metrics.csv           # All models, all metrics, all CIs
├── docs/
│   ├── SUPPLEMENTARY_APPENDICES.md   # A through G
│   └── HYPERPARAMETERS.md            # Full training configuration
├── figures/
│   └── Fig1-Fig5 (PNG + PDF, 300dpi)
├── LICENSE
├── requirements.txt
└── README.md
```

## Dataset

The TN5000 dataset is publicly available:
- **DOI:** [10.6084/m9.figshare.27962824](https://doi.org/10.6084/m9.figshare.27962824)
- **Citation:** Zhang, H. et al. TN5000: An Ultrasound Image Dataset for Thyroid Nodule Detection and Classification. *Sci. Data* **12**, 1437 (2025). PMID: 40819171.

Follow the authors' recommended partition: 3,500 training / 500 validation / 1,000 test.

## Reproducing the benchmark

### Environment

```bash
pip install -r requirements.txt
```

Core dependencies:
- `transformers>=4.45`
- `peft>=0.12`
- `bitsandbytes>=0.43`
- `trl>=0.11`
- `torch>=2.4`
- `accelerate>=0.34`
- `scikit-learn`
- `statsmodels`
- `pandas`, `numpy`, `matplotlib`
- `openai` (for OpenRouter-compatible client)
- `python-docx` (for manuscript rebuild)

### Tier 1: Zero-shot VLMs

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
python scripts/zero_shot_inference.py \
    --data_dir /path/to/tn5000/test \
    --labels /path/to/tn5000/test_labels.csv \
    --prompt prompts/baseline.txt \
    --model "google/gemini-2.5-pro" \
    --output results/zs_gemini25pro_baseline.jsonl
```

Repeat for each of the 12 models × 3 prompts.

### Tier 2: QLoRA fine-tuning

```bash
# LLaVA-NeXT 7B
python scripts/qlora_finetune.py \
    --model_id "llava-hf/llava-v1.6-mistral-7b-hf" \
    --train_data /path/to/tn5000/train.json \
    --output_dir outputs/llava_qlora \
    --epochs 3 \
    --lora_r 16 \
    --lora_alpha 32 \
    --learning_rate 2e-4 \
    --batch_size 16 \
    --quantization_bits 4

# Qwen2.5-VL-7B (same args)
# Gemma 4 27B (see Supplementary Appendix B.3 for adapter placement notes)
```

### Tier 3: Supervised baselines

```bash
python scripts/supervised_train.py \
    --arch swin_tiny_patch4_window7_224 \
    --data_dir /path/to/tn5000 \
    --output_dir outputs/swin_t \
    --epochs 30 \
    --batch_size 32 \
    --learning_rate 1e-4 \
    --weight_decay 1e-4 \
    --phase1_epochs 5 \
    --seed 42
```

### Evaluation

```bash
python scripts/evaluate.py \
    --predictions_dir results/ \
    --labels /path/to/tn5000/test_labels.csv \
    --output results/summary_metrics.csv \
    --bootstrap 10000
```

## Prompts

All three prompt templates are included in `prompts/`. The structured TI-RADS-guided prompt embeds the complete ACR TI-RADS point-based scoring criteria (Tessler et al., 2017).

## Response parsing pipeline

Zero-shot VLM responses are parsed in three stages (see `scripts/parse_outputs.py`):

1. Explicit `malignant`/`benign` keyword matching (case-insensitive)
2. TI-RADS category extraction (TR4/TR5 → malignant; TR1/TR2/TR3 → benign)
3. Rule-based sentiment classification using predefined term lists

Level 3 fallback was required for < 0.3% of predictions. Parsing failure rate < 1% for all models.

## Cite this work

```bibtex
@article{ahmed2026tn5000vlm,
    title={Parameter-Efficient Fine-Tuning Corrects Specificity Collapse in
           Zero-Shot Vision-Language Models for Thyroid Ultrasound Classification},
    author={Ahmed, Fahad Wali and Ahmed, Fauwad Wali and Moftah, Belal},
    journal={npj Digital Medicine},
    year={2026},
    doi={TBD}
}
```

## License

Code is released under the MIT License (see `LICENSE`).

The TN5000 dataset is distributed under its original licence — please consult the dataset DOI above.

## Contact

- Corresponding author: Fahad Wali Ahmed — fahadwali@yahoo.com
  (ORCID: [0000-0003-4100-1571](https://orcid.org/0000-0003-4100-1571))

For issues reproducing the benchmark, please open a GitHub Issue.
