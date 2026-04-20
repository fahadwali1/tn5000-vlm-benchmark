# How to upload this repository to GitHub

## 1. Create a new GitHub repository (via web UI)

Go to https://github.com/new and create a new repository, for example:
- Name: `tn5000-vlm-benchmark`
- Visibility: Public (required for npj Digital Medicine code availability)
- Do NOT initialise with README, .gitignore, or LICENSE (we already have them)

## 2. Upload from this folder

Open a terminal in `/Users/fahadwali/Downloads/TN5000/github_upload/` and run:

```bash
cd /Users/fahadwali/Downloads/TN5000/github_upload

git init
git add .
git commit -m "Initial release: TN5000 VLM benchmark (npj Digital Medicine, 2026)"
git branch -M main
git remote add origin https://github.com/<YOUR_USERNAME>/tn5000-vlm-benchmark.git
git push -u origin main
```

Replace `<YOUR_USERNAME>` with your actual GitHub username.

## 3. Tag a release (optional, recommended for reproducibility)

After the push:

```bash
git tag -a v1.0 -m "Manuscript submission version"
git push origin v1.0
```

This creates a permanent, citable snapshot.

## 4. Mint a DOI via Zenodo (optional, recommended for the paper)

- Go to https://zenodo.org and log in with your GitHub account.
- Enable the `tn5000-vlm-benchmark` repository under Settings → GitHub.
- Create a GitHub Release (not just a tag); Zenodo will automatically mint a DOI.
- Add the DOI badge to the top of `README.md` and cite it in the Code Availability section of the manuscript.

## 5. Update the manuscript

Once the repository is live, replace the placeholder in the manuscript:

Find: `[GitHub repository URL to be inserted prior to publication]`
Replace with: `https://github.com/<YOUR_USERNAME>/tn5000-vlm-benchmark`

This is in the Code Availability section of the manuscript.

## What is in this upload

```
github_upload/
├── README.md                    # Public-facing documentation
├── LICENSE                      # MIT
├── requirements.txt             # All Python dependencies
├── .gitignore                   # Excludes checkpoints, secrets, raw data
├── UPLOAD_TO_GITHUB.md          # This file
├── scripts/
│   ├── zero_shot_inference.py   # Tier 1: OpenRouter API calls
│   ├── qlora_finetune.py        # Tier 2: QLoRA (LLaVA-NeXT, Qwen2.5-VL, Gemma 4)
│   ├── supervised_train.py      # Tier 3: ResNet-50, EfficientNet-B0, Swin-T
│   ├── evaluate.py              # Metrics + bootstrap CIs + z-test + prevalence analysis
│   ├── parse_outputs.py         # 3-level VLM response parsing
│   ├── build_manuscript.py      # python-docx build of the full manuscript
│   ├── build_figures.py         # Matplotlib figure generation
│   └── build_cover_letter.py    # python-docx cover letter build
├── prompts/
│   ├── baseline.txt
│   ├── chain_of_thought.txt
│   └── ti_rads_guided.txt
├── figures/
│   └── Fig1-5 (PNG + PDF, 300 dpi)
└── results/                     # (empty on first push; add after running the benchmark)
    └── .gitkeep
```

The `results/` folder is empty on the initial push. You can add the processed
prediction CSVs, metric JSONs, and summary tables after running the benchmark
scripts on your end.

## What is NOT included (by design)

- Raw TN5000 images (redistribute via the original DOI, not this repo)
- Fine-tuned model checkpoints and LoRA adapters (too large; upload to Hugging Face Hub if desired)
- API keys or credentials
