#!/usr/bin/env python3
"""
Create publication-quality figures for TN5000 VLM Benchmark manuscript.
npj Digital Medicine style: clean, minimal, Nature-quality.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os

# Output directory
OUT = '/Users/fahadwali/Downloads/TN5000/figures'
os.makedirs(OUT, exist_ok=True)

# --- Nature/npj style settings ---
plt.rcParams.update({
    'font.family': 'Helvetica',
    'font.size': 8,
    'axes.titlesize': 9,
    'axes.labelsize': 8,
    'xtick.labelsize': 7,
    'ytick.labelsize': 7,
    'legend.fontsize': 7,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.linewidth': 0.5,
    'xtick.major.width': 0.5,
    'ytick.major.width': 0.5,
    'axes.spines.top': False,
    'axes.spines.right': False,
})

# Color palette (Nature-friendly, colorblind-safe)
C_ZERO = '#4575b4'     # Blue for zero-shot
C_FINE = '#d73027'     # Red for fine-tuned
C_SUP = '#1a9850'      # Green for supervised
C_FAIL = '#bdbdbd'     # Grey for Gemma failure
C_LIGHT_ZERO = '#abd9e9'
C_LIGHT_FINE = '#fdae61'
C_LIGHT_SUP = '#a6d96a'

# ===== DATA =====
# Zero-shot (best prompt per model)
zs_models = [
    'Qwen3-VL-235B', 'Qwen2.5-VL-72B', 'GPT-4.1 Mini', 'Claude Sonnet 4',
    'Gemini 2.0 Flash\n(CoT)', 'GPT-4.1', 'Gemini 2.5 Pro', 'Claude Sonnet 4.6',
    'Gemini 2.0 Flash\n(Baseline)', 'Grok 4', 'Gemini 2.5 Flash', 'OpenAI o4-mini',
    'Llama 4 Scout'
]
zs_acc =  [0.745, 0.738, 0.735, 0.735, 0.730, 0.725, 0.724, 0.713, 0.713, 0.707, 0.689, 0.680, 0.623]
zs_sens = [0.982, 0.971, 0.988, 0.995, 0.906, 0.958, 0.923, 0.926, 0.866, 0.917, 0.840, 0.887, 0.758]
zs_spec = [0.100, 0.108, 0.048, 0.030, 0.253, 0.093, 0.186, 0.134, 0.297, 0.138, 0.279, 0.116, 0.257]

# Fine-tuned VLMs
ft_models = ['LLaVA-NeXT 7B', 'Qwen2.5-VL-7B', 'Gemma 4 27B']
ft_acc =  [0.871, 0.802, 0.625]
ft_sens = [0.881, 0.819, 0.802]
ft_spec = [0.844, 0.755, 0.145]
ft_mcc =  [0.693, 0.539, -0.061]
ft_auc =  [0.938, 0.862, 0.481]

# Supervised DL
sup_models = ['Swin-T', 'ResNet-50', 'EfficientNet-B0']
sup_acc =  [0.856, 0.760, 0.705]
sup_sens = [0.852, 0.720, 0.640]
sup_spec = [0.866, 0.870, 0.881]
sup_mcc =  [0.672, 0.527, 0.462]
sup_auc =  [0.937, 0.889, 0.849]


# ============================================================
# FIGURE 1: Sensitivity vs Specificity scatter (THE key figure)
# ============================================================
fig, ax = plt.subplots(figsize=(180/25.4, 130/25.4))  # 180mm x 130mm (double column)

# Zero-shot
ax.scatter(zs_spec, zs_sens, c=C_ZERO, s=50, marker='o', alpha=0.85,
           edgecolors='white', linewidths=0.5, zorder=3, label='Zero-shot VLMs (n=13)')

# Fine-tuned VLMs
ax.scatter(ft_spec[0], ft_sens[0], c=C_FINE, s=100, marker='^', edgecolors='white',
           linewidths=0.5, zorder=4)  # LLaVA
ax.scatter(ft_spec[1], ft_sens[1], c=C_FINE, s=80, marker='^', edgecolors='white',
           linewidths=0.5, zorder=4)  # Qwen
ax.scatter(ft_spec[2], ft_sens[2], c=C_FAIL, s=80, marker='x', linewidths=1.5,
           zorder=4)  # Gemma (failed)

# Supervised
ax.scatter(sup_spec, sup_sens, c=C_SUP, s=80, marker='s', edgecolors='white',
           linewidths=0.5, zorder=4)

# Annotations
ax.annotate('LLaVA-NeXT 7B\n(fine-tuned)', (ft_spec[0], ft_sens[0]),
            textcoords='offset points', xytext=(10, -15), fontsize=6.5,
            color=C_FINE, fontweight='bold')
ax.annotate('Qwen2.5-VL-7B\n(fine-tuned)', (ft_spec[1], ft_sens[1]),
            textcoords='offset points', xytext=(10, 5), fontsize=6.5,
            color=C_FINE)
ax.annotate('Gemma 4 27B\n(failed)', (ft_spec[2], ft_sens[2]),
            textcoords='offset points', xytext=(10, -15), fontsize=6.5,
            color='#666666')
ax.annotate('Swin-T', (sup_spec[0], sup_sens[0]),
            textcoords='offset points', xytext=(8, 3), fontsize=6.5,
            color=C_SUP, fontweight='bold')
ax.annotate('ResNet-50', (sup_spec[1], sup_sens[1]),
            textcoords='offset points', xytext=(8, 3), fontsize=6.5, color=C_SUP)
ax.annotate('EfficientNet-B0', (sup_spec[2], sup_sens[2]),
            textcoords='offset points', xytext=(5, 5), fontsize=6.5, color=C_SUP)

# Shaded "specificity collapse" zone
ax.axvspan(0, 0.30, alpha=0.06, color='red', zorder=0)
ax.text(0.15, 0.61, 'Specificity\ncollapse\nzone', ha='center', va='center',
        fontsize=7, color='#cc0000', alpha=0.5, fontstyle='italic')

# Diagonal
ax.plot([0, 1], [0, 1], '--', color='#aaaaaa', linewidth=0.5, alpha=0.5, zorder=1)

# Legend
legend_elements = [
    mpatches.Patch(facecolor=C_ZERO, edgecolor='white', label='Zero-shot VLMs (n=13)'),
    plt.Line2D([0], [0], marker='^', color='w', markerfacecolor=C_FINE, markersize=8,
               label='QLoRA fine-tuned VLMs'),
    plt.Line2D([0], [0], marker='x', color=C_FAIL, markersize=7, linestyle='None',
               markeredgewidth=1.5, label='Fine-tuning failure (Gemma 4)'),
    plt.Line2D([0], [0], marker='s', color='w', markerfacecolor=C_SUP, markersize=7,
               label='Supervised baselines'),
]
ax.legend(handles=legend_elements, loc='lower right', frameon=True, framealpha=0.9,
          edgecolor='#cccccc', fontsize=7)

ax.set_xlabel('Specificity')
ax.set_ylabel('Sensitivity')
ax.set_xlim(-0.02, 1.02)
ax.set_ylim(0.58, 1.02)
ax.set_title('a', loc='left', fontweight='bold', fontsize=10)

fig.savefig(f'{OUT}/Fig1_sensitivity_specificity.png', dpi=300)
fig.savefig(f'{OUT}/Fig1_sensitivity_specificity.pdf')
plt.close()
print("✓ Fig 1 done")


# ============================================================
# FIGURE 2: MCC comparison across all models (horizontal bar)
# ============================================================
# Combine all models sorted by MCC
all_names = []
all_mcc = []
all_colors = []

# Zero-shot MCC (approximate from accuracy/sens/spec using full formula)
# MCC = (TP*TN - FP*FN) / sqrt((TP+FP)(TP+FN)(TN+FP)(TN+FN))
# n_test=1000, n_mal=731, n_ben=269
n_mal, n_ben = 731, 269
for i in range(len(zs_models)):
    tp = round(zs_sens[i] * n_mal)
    fn = n_mal - tp
    tn = round(zs_spec[i] * n_ben)
    fp = n_ben - tn
    denom = np.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
    mcc_val = (tp*tn - fp*fn) / denom if denom > 0 else 0
    all_names.append(zs_models[i].replace('\n', ' '))
    all_mcc.append(round(mcc_val, 3))
    all_colors.append(C_ZERO)

for i, m in enumerate(ft_models):
    all_names.append(f'{m} (QLoRA)')
    all_mcc.append(ft_mcc[i])
    all_colors.append(C_FINE if ft_mcc[i] > 0.1 else C_FAIL)

for i, m in enumerate(sup_models):
    all_names.append(m)
    all_mcc.append(sup_mcc[i])
    all_colors.append(C_SUP)

# Sort by MCC
sorted_idx = np.argsort(all_mcc)
sorted_names = [all_names[i] for i in sorted_idx]
sorted_mcc = [all_mcc[i] for i in sorted_idx]
sorted_colors = [all_colors[i] for i in sorted_idx]

fig, ax = plt.subplots(figsize=(180/25.4, 160/25.4))
y_pos = np.arange(len(sorted_names))
bars = ax.barh(y_pos, sorted_mcc, color=sorted_colors, edgecolor='white', linewidth=0.3, height=0.7)

# MCC value labels
for i, (bar, v) in enumerate(zip(bars, sorted_mcc)):
    if v >= 0:
        ax.text(v + 0.01, bar.get_y() + bar.get_height()/2, f'{v:.3f}',
                va='center', ha='left', fontsize=6)
    else:
        ax.text(v - 0.01, bar.get_y() + bar.get_height()/2, f'{v:.3f}',
                va='center', ha='right', fontsize=6)

ax.set_yticks(y_pos)
ax.set_yticklabels(sorted_names, fontsize=6.5)
ax.set_xlabel("Matthews Correlation Coefficient (MCC)")
ax.axvline(x=0.2, color='#999999', linestyle=':', linewidth=0.5, alpha=0.6)
ax.text(0.205, len(sorted_names)-0.5, 'Near-random\nthreshold', fontsize=5.5,
        color='#999999', va='top')

legend_elements = [
    mpatches.Patch(facecolor=C_ZERO, label='Zero-shot VLMs'),
    mpatches.Patch(facecolor=C_FINE, label='QLoRA fine-tuned VLMs'),
    mpatches.Patch(facecolor=C_FAIL, label='Fine-tuning failure'),
    mpatches.Patch(facecolor=C_SUP, label='Supervised baselines'),
]
ax.legend(handles=legend_elements, loc='lower right', frameon=True, fontsize=6.5,
          edgecolor='#cccccc')
ax.set_title('b', loc='left', fontweight='bold', fontsize=10)

fig.savefig(f'{OUT}/Fig2_MCC_comparison.png', dpi=300)
fig.savefig(f'{OUT}/Fig2_MCC_comparison.pdf')
plt.close()
print("✓ Fig 2 done")


# ============================================================
# FIGURE 3: Grouped bar -- top model per tier comparison
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(180/25.4, 80/25.4))

# Panel a: Accuracy, Sensitivity, Specificity
metrics = ['Accuracy', 'Sensitivity', 'Specificity']
best_zs = [0.745, 0.982, 0.100]  # Qwen3-VL-235B
best_ft = [0.871, 0.881, 0.844]  # LLaVA-NeXT FT
best_sup = [0.856, 0.852, 0.866]  # Swin-T

x = np.arange(len(metrics))
w = 0.25
axes[0].bar(x - w, best_zs, w, color=C_ZERO, edgecolor='white', label='Best zero-shot\n(Qwen3-VL-235B)')
axes[0].bar(x, best_ft, w, color=C_FINE, edgecolor='white', label='Best fine-tuned\n(LLaVA-NeXT 7B)')
axes[0].bar(x + w, best_sup, w, color=C_SUP, edgecolor='white', label='Best supervised\n(Swin-T)')

# Value labels
for i, (z, f, s) in enumerate(zip(best_zs, best_ft, best_sup)):
    axes[0].text(i - w, z + 0.015, f'{z:.1%}', ha='center', va='bottom', fontsize=5.5)
    axes[0].text(i, f + 0.015, f'{f:.1%}', ha='center', va='bottom', fontsize=5.5)
    axes[0].text(i + w, s + 0.015, f'{s:.1%}', ha='center', va='bottom', fontsize=5.5)

axes[0].set_xticks(x)
axes[0].set_xticklabels(metrics)
axes[0].set_ylim(0, 1.12)
axes[0].set_ylabel('Score')
axes[0].legend(fontsize=5.5, loc='upper center', ncol=3, frameon=False,
               bbox_to_anchor=(0.5, 1.15))
axes[0].set_title('a', loc='left', fontweight='bold', fontsize=10)

# Panel b: MCC and AUC
metrics2 = ['MCC', 'AUC-ROC']
# Best zero-shot MCC ≈ 0.13 (from Qwen3), AUC not available for zero-shot (no probabilities)
zs_vals = [0.130, None]  # No AUC for zero-shot
ft_vals = [0.693, 0.938]
sup_vals = [0.672, 0.937]

x2 = np.arange(2)
# Zero-shot only has MCC
axes[1].bar(0 - w, 0.130, w, color=C_ZERO, edgecolor='white')
axes[1].bar(x2, ft_vals, w, color=C_FINE, edgecolor='white')
axes[1].bar(x2 + w, sup_vals, w, color=C_SUP, edgecolor='white')

axes[1].text(0 - w, 0.130 + 0.015, '0.130', ha='center', va='bottom', fontsize=5.5)
axes[1].text(0, 0.693 + 0.015, '0.693', ha='center', va='bottom', fontsize=5.5)
axes[1].text(0 + w, 0.672 + 0.015, '0.672', ha='center', va='bottom', fontsize=5.5)
axes[1].text(1, 0.938 + 0.015, '0.938', ha='center', va='bottom', fontsize=5.5)
axes[1].text(1 + w, 0.937 + 0.015, '0.937', ha='center', va='bottom', fontsize=5.5)
axes[1].text(1 - w, 0.02, 'N/A', ha='center', va='bottom', fontsize=5.5, color='#999999')

axes[1].set_xticks(x2)
axes[1].set_xticklabels(metrics2)
axes[1].set_ylim(0, 1.08)
axes[1].set_ylabel('Score')
axes[1].set_title('b', loc='left', fontweight='bold', fontsize=10)

plt.tight_layout()
fig.savefig(f'{OUT}/Fig3_tier_comparison.png', dpi=300)
fig.savefig(f'{OUT}/Fig3_tier_comparison.pdf')
plt.close()
print("✓ Fig 3 done")


# ============================================================
# FIGURE 4: Prevalence-adjusted PPV curves
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(180/25.4, 80/25.4))

prev = np.linspace(0.01, 0.30, 200)

# Models: Qwen3 (best ZS), LLaVA-FT, Swin-T
models_ppv = [
    ('Qwen3-VL-235B\n(zero-shot)', 0.982, 0.100, C_ZERO, '-'),
    ('LLaVA-NeXT 7B\n(QLoRA)', 0.881, 0.844, C_FINE, '-'),
    ('Swin-T\n(supervised)', 0.852, 0.866, C_SUP, '--'),
]

# Panel a: PPV
for name, sens, spec, color, ls in models_ppv:
    ppv = (sens * prev) / (sens * prev + (1 - spec) * (1 - prev))
    axes[0].plot(prev * 100, ppv * 100, color=color, linestyle=ls, linewidth=1.5, label=name)

axes[0].axhline(y=50, color='#cccccc', linestyle=':', linewidth=0.5)
axes[0].text(28, 51, 'PPV = 50%', fontsize=5.5, color='#999999')
axes[0].set_xlabel('Malignancy prevalence (%)')
axes[0].set_ylabel('Positive predictive value (%)')
axes[0].legend(fontsize=6, loc='upper left', frameon=True, edgecolor='#cccccc')
axes[0].set_xlim(1, 30)
axes[0].set_ylim(0, 80)
axes[0].set_title('a', loc='left', fontweight='bold', fontsize=10)

# Panel b: FP/TP ratio
for name, sens, spec, color, ls in models_ppv:
    fp_tp = ((1 - spec) * (1 - prev)) / (sens * prev)
    axes[1].plot(prev * 100, fp_tp, color=color, linestyle=ls, linewidth=1.5, label=name)

axes[1].axhline(y=1, color='#cccccc', linestyle=':', linewidth=0.5)
axes[1].text(28, 1.3, 'FP/TP = 1', fontsize=5.5, color='#999999')
axes[1].set_xlabel('Malignancy prevalence (%)')
axes[1].set_ylabel('False positives per true positive')
axes[1].legend(fontsize=6, loc='upper right', frameon=True, edgecolor='#cccccc')
axes[1].set_xlim(1, 30)
axes[1].set_ylim(0, 25)
axes[1].set_title('b', loc='left', fontweight='bold', fontsize=10)

plt.tight_layout()
fig.savefig(f'{OUT}/Fig4_prevalence_adjusted.png', dpi=300)
fig.savefig(f'{OUT}/Fig4_prevalence_adjusted.pdf')
plt.close()
print("✓ Fig 4 done")


# ============================================================
# FIGURE 5: Specificity improvement waterfall (before → after fine-tuning)
# ============================================================
fig, ax = plt.subplots(figsize=(88/25.4, 80/25.4))  # Single column

# Models and their zero-shot median spec vs fine-tuned spec
labels = ['Zero-shot\nmedian', 'LLaVA-NeXT\n(QLoRA)', 'Qwen2.5-VL\n(QLoRA)', 'Swin-T\n(supervised)']
specs_before = [0.138, 0.138, 0.138, None]  # zero-shot median as baseline
specs_after = [0.138, 0.844, 0.755, 0.866]

x = np.arange(4)
colors = [C_ZERO, C_FINE, C_FINE, C_SUP]

# Draw bars
bars = ax.bar(x, specs_after, color=colors, edgecolor='white', width=0.6)

# Baseline line
ax.axhline(y=0.138, color=C_ZERO, linestyle='--', linewidth=0.8, alpha=0.5)
ax.text(3.35, 0.15, 'Zero-shot\nmedian: 13.8%', fontsize=5.5, color=C_ZERO, alpha=0.7)

# Improvement arrows for LLaVA and Qwen
for i in [1, 2]:
    improvement = specs_after[i] - 0.138
    ax.annotate(f'+{improvement:.1%}',
                xy=(i, specs_after[i]), xytext=(i, specs_after[i] + 0.04),
                ha='center', fontsize=6, color=colors[i], fontweight='bold')

# Swin-T label
ax.annotate(f'{specs_after[3]:.1%}',
            xy=(3, specs_after[3]), xytext=(3, specs_after[3] + 0.04),
            ha='center', fontsize=6, color=C_SUP, fontweight='bold')

ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=6.5)
ax.set_ylabel('Specificity')
ax.set_ylim(0, 1.05)
ax.set_title('', loc='left', fontweight='bold', fontsize=10)

fig.savefig(f'{OUT}/Fig5_specificity_correction.png', dpi=300)
fig.savefig(f'{OUT}/Fig5_specificity_correction.pdf')
plt.close()
print("✓ Fig 5 done")

print(f"\n✅ All figures saved to {OUT}/")
print("Files:", os.listdir(OUT))
