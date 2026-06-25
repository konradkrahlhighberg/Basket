import numpy as np
import matplotlib.pyplot as plt

results = []

ratios = [(2, 1), (1, 1), (1, 2)]

MAX_SIZE = 500
log_max = np.log1p(MAX_SIZE)

MINIMAL_PERFORMANCE = 0.05

for r_a, r_b in ratios:
    for size_a in range(20, 501, 20):
        size_b = size_a * r_b // r_a
        for overlap_pct in range(1, 101, 10):

            # Build module sets as lists
            list_a = list(range(size_a))
            list_b = list(range(size_a, size_a + size_b))  # disjoint by default

            # Force overlap
            n_overlap = int(min(size_a, size_b) * overlap_pct / 100)
            list_b[:n_overlap] = list_a[:n_overlap]

            # Derive proportions from the sets
            set_a, set_b = set(list_a), set(list_b)
            overlap = len(set_a & set_b)
            union = len(set_a | set_b)
            naive_jaccard = overlap / union

            score = naive_jaccard * (np.log1p(overlap) / log_max) * (np.log1p(min(size_a, size_b)) / log_max)

            # --- Weighted score ---
            perf_a = np.where(np.random.rand(size_a) < 0.1, np.random.uniform(0, 0.1, size_a), np.random.uniform(0.1, 1, size_a))
            perf_b = np.where(np.random.rand(size_b) < 0.1, np.random.uniform(0, 0.1, size_b), np.random.uniform(0.1, 1, size_b))

            filtered_a = [list_a[i] for i in range(len(list_a)) if perf_a[i] >= MINIMAL_PERFORMANCE]
            filtered_b = [list_b[i] for i in range(len(list_b)) if perf_b[i] >= MINIMAL_PERFORMANCE]

            # Weighted score on filtered sets
            fset_a, fset_b = set(filtered_a), set(filtered_b)
            f_overlap = len(fset_a & fset_b)
            f_union = len(fset_a | fset_b)
            weighted_jaccard = f_overlap / f_union if f_union > 0 else 0.0
            weighted_score = weighted_jaccard * (np.log1p(f_overlap) / log_max) * (np.log1p(min(len(fset_a), len(fset_b))) / log_max)

            results.append((r_a, r_b, size_a, size_b, overlap_pct, score, naive_jaccard, weighted_score))

# --- Plotting ---

fig, axes = plt.subplots(3, 3, figsize=(15, 12))

overlap_pcts = [21, 51, 81]

for row, (r_a, r_b) in enumerate(ratios):
    for col, fixed_pct in enumerate(overlap_pcts):
        ax = axes[row, col]
        subset = [(s_a, score, nj, ws) for ra, rb, s_a, s_b, ov_pct, score, nj, ws in results
                  if ra == r_a and rb == r_b and ov_pct == fixed_pct]
        sizes = [x[0] for x in subset]
        scores = [x[1] for x in subset]
        naive_jaccards = [x[2] for x in subset]
        weighted_scores = [x[3] for x in subset]

        ax.plot(sizes, scores, label="Adapted Jaccard (normalized)")
        ax.plot(sizes, naive_jaccards, label="Naive Jaccard", linestyle="--")
        ax.plot(sizes, weighted_scores, label="Weighted Jaccard", linestyle=":")
        ax.set_ylim(0, 1)
        ax.set_title(f"Ratio {r_a}:{r_b}, Overlap={fixed_pct}%")
        ax.set_xlabel("Module Size (A)")
        ax.set_ylabel("Value")
        ax.legend()

plt.tight_layout()
plt.show()