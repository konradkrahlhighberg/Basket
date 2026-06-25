import pandas as pd
import polars as pl
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder

# Load and prepare data
df = pl.read_excel("/Users/konradkrahl/Library/CloudStorage/OneDrive-Highberg/Desktop/Beck/Data/Publikation_Modul.xlsx")
df = df.with_columns(pl.col('2025 \nKlicks Gesamtjahr').cast(pl.Float64, strict=False)).drop_nulls(subset=["2025 \nKlicks Gesamtjahr"])
df = df.filter((pl.col("Publikation") != "null") & (pl.col('2025 \nKlicks Gesamtjahr') > 0) & (pl.col("Module") != "null"))
df = df[["Publikation", "Module"]]

# Flip: each publication is a basket of modules it appears in
transactions_flipped = df.group_by("Publikation").agg(pl.col("Module")).to_pandas()
transactions_flipped = transactions_flipped["Module"].tolist()

# Encode
te2 = TransactionEncoder()
te_array2 = te2.fit_transform(transactions_flipped)
basket_df2 = pd.DataFrame(te_array2, columns=te2.columns_)

print(f"Unique modules in encoder: {len(te2.columns_)}")

# Apriori — only keep itemsets of size 1 and 2 for clean pairwise comparison
frequent_modules = apriori(basket_df2, min_support=0.001, use_colnames=True)
frequent_modules = frequent_modules[frequent_modules["itemsets"].apply(lambda x: len(x) <= 2)]

# Association rules
module_rules = association_rules(frequent_modules, metric="lift", min_threshold=1)

# Force pairwise only: single module → single module
module_rules = module_rules[
    (module_rules["antecedents"].apply(lambda x: len(x) == 1)) &
    (module_rules["consequents"].apply(lambda x: len(x) == 1))
].reset_index(drop=True)

module_rules = module_rules.sort_values("lift", ascending=False).reset_index(drop=True)

# Flatten frozensets to plain strings
module_rules["antecedents"] = module_rules["antecedents"].apply(lambda x: list(x)[0])
module_rules["consequents"] = module_rules["consequents"].apply(lambda x: list(x)[0])

# Select and display key KPIs
result = module_rules[[
    "antecedents", "consequents",
    "support", "confidence", "lift",
    "leverage", "conviction"
]].copy()

result["support"]    = result["support"].round(3)
result["confidence"] = result["confidence"].round(3)
result["lift"]       = result["lift"].round(2)
result["leverage"]   = result["leverage"].round(4)
result["conviction"] = result["conviction"].round(2)

print(f"Total pairwise rules: {len(result)}")
print(f"Unique antecedents: {result['antecedents'].nunique()}")
print(f"Unique consequents: {result['consequents'].nunique()}")
print(result.head(30))

# Filter for strong redundancy candidates
strong = result[
    (result["confidence"] >= 0.7) &
    (result["lift"] >= 2.0)
].copy()

print("\n=== Strong Redundancy Candidates ===")
print(strong)

result.to_excel("/Users/konradkrahl/Library/CloudStorage/OneDrive-Highberg/Desktop/Beck/Data/module_association_rules.xlsx", index=False)
strong.to_excel("/Users/konradkrahl/Library/CloudStorage/OneDrive-Highberg/Desktop/Beck/Data/module_association_rules_red.xlsx", index=False)