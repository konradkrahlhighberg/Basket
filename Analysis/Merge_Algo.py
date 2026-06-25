#%%

import polars as pl
from itertools import combinations
import json

#%%

df = pl.read_excel("/Users/konradkrahl/Library/CloudStorage/OneDrive-Highberg/Desktop/Beck/Data/Weitere Module.xlsx")
df = df.with_columns(pl.col('2025 Klicks Gesamtjahr').cast(pl.Float64, strict=False)).drop_nulls(subset=["2025 Klicks Gesamtjahr"])
df = df.filter(
    (pl.col("Publikationen") != "null") &
    (pl.col('2025 Klicks Gesamtjahr') > 0) &
    (pl.col('Modul') != "null")
)
df = df[["Publikationen", "Modul"]]


#%%


def build_pub_sets(df: pl.DataFrame) -> dict[str, set]:
    sets = {}
    for row in df.iter_rows(named=True):
        m = row["Modul"]
        p = row["Publikationen"]
        sets.setdefault(m, set()).add(p)
    return sets

def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

THRESHOLD = 0.7

def find_best_pair(pub_sets: dict[str, set]) -> tuple[str, str, float] | None:
    """Return the pair with the highest Jaccard above threshold, or None."""
    best = None
    best_score = THRESHOLD 
    modules = list(pub_sets.keys())
    for a, b in combinations(modules, 2):
        j = jaccard(pub_sets[a], pub_sets[b])
        if j >= best_score:
            best_score = j
            best = (a, b, j)
    return best

def merge_modules(pub_sets: dict[str, set], a: str, b: str) -> tuple[str, dict[str, set]]:
    """Merge module b into a, return new name and updated dict."""
    new_name = f"{a} | {b}"
    new_pubs = pub_sets[a] | pub_sets[b]
    updated = {k: v for k, v in pub_sets.items() if k not in (a, b)}
    updated[new_name] = new_pubs
    return new_name, updated


pub_sets = build_pub_sets(df)

# Dendrogram nodes: each merge = one node in the tree
merge_history = []   # list of dicts for JSON export
iteration = 0

print(f"Starting with {len(pub_sets)} modules")

while True:
    best = find_best_pair(pub_sets)
    if best is None:
        break
    a, b, score = best
    iteration += 1
    new_name, pub_sets = merge_modules(pub_sets, a, b)
    pubs_in_merge = sorted(pub_sets[new_name])

    record = {
        "iteration": iteration,
        "module_a": a,
        "module_b": b,
        "merged_name": new_name,
        "jaccard": round(score, 4),
        "pub_count": len(pubs_in_merge),
        "publications": pubs_in_merge,
    }
    merge_history.append(record)
    print(f"[{iteration:>3}] Jaccard={score:.4f}  '{a}'  +  '{b}'  →  {len(pubs_in_merge)} pubs")

print(f"\nDone. {iteration} merges. Remaining super-modules: {len(pub_sets)}")


# A. Merge history as Excel
history_df = pl.DataFrame([
    {k: v for k, v in r.items() if k != "publications"}
    for r in merge_history
])
history_df.write_excel(
    "/Users/konradkrahl/Library/CloudStorage/OneDrive-Highberg/Desktop/Beck/Output/Merge_History.xlsx"
)

# B. Final super-modules as Excel
final_rows = []
for name, pubs in pub_sets.items():
    for p in sorted(pubs):
        final_rows.append({"Super_Module": name, "Publikation": p})
pl.DataFrame(final_rows).write_excel(
    "/Users/konradkrahl/Library/CloudStorage/OneDrive-Highberg/Desktop/Beck/Output/Final_SuperModules.xlsx"
)

# C. Full history with pub lists as JSON (for interactive dendrogram)
with open(
    "/Users/konradkrahl/Library/CloudStorage/OneDrive-Highberg/Desktop/Beck/Output/merge_history.json",
    "w", encoding="utf-8"
) as f:
    # Also add the final state
    final_state = {
        "iteration": iteration + 1,
        "module_a": None,
        "module_b": None,
        "merged_name": "FINAL STATE",
        "jaccard": None,
        "pub_count": sum(len(v) for v in pub_sets.values()),
        "publications": [],
        "super_modules": {k: sorted(v) for k, v in pub_sets.items()},
    }
    json.dump({"merges": merge_history, "final": final_state}, f, ensure_ascii=False, indent=2)

print("\nFiles written:")
print("  → Merge_History.xlsx")
print("  → Final_SuperModules.xlsx")
print("  → merge_history.json  (load this into the interactive explorer)")
# %%
