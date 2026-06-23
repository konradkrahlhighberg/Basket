import pandas as pd
import polars as pl
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder



'''

each module is basket and pub is item, to find redundancy, we flip the logic
to observe whoch modle occures overs pubs the most

Support — how often do both modules share the same publications, relative to all publications. A support of 0.10 means 10% of all publications appear in both modules. Low support = niche overlap; high support = widespread redundancy.
Confidence — given a publication is in Module A, how likely is it also in Module B. 0.80 means 80% of Module A's publications also show up in Module B. This is your most direct redundancy signal — high confidence means Module B largely "contains" Module A.
Lift — is the overlap more than you'd expect by chance? 1.0 = random co-occurrence, 2.0 = the two modules share publications twice as often as chance would predict. Lift corrects for the fact that very large modules will naturally overlap with many others just due to size.
Leverage — the raw difference between observed co-occurrence and what's expected under independence. Similar to lift but in absolute terms. Useful for comparing pairs with similar lift but very different scales.
Conviction — measures how often the rule would be wrong if the two modules were independent. High conviction (e.g. 3.0+) means the dependency is strong and not coincidental. Unlike lift, conviction is directional — A → B and B → A give different values.

min_support=0.01 threshold. A module pair only appears in results if they co-occur in at least 1% of all publications. With 600 modules, most pairs are niche and never reach that bar — they get pruned before rules are even generated.


xlsx files 6+10 sind am wichtigsten 10 aus Pubikationssicht, 6 aus Module, hier sch
Schauen ob in manchen Modulen publikationen ünerhaiutop benutzt wernden???
6 welches publikation in welchen module, 10 welche publikation ist noch sinnvloll

siehe Copilot 

'''


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

# Apriori on modules
frequent_modules = apriori(basket_df2, min_support=0.01, use_colnames=True)

# Association rules
module_rules = association_rules(frequent_modules, metric="lift", min_threshold=1)
module_rules = module_rules.sort_values("lift", ascending=False).reset_index(drop=True)

# Clean up frozensets for readability
module_rules["antecedents"] = module_rules["antecedents"].apply(lambda x: ", ".join(sorted(x)))
module_rules["consequents"] = module_rules["consequents"].apply(lambda x: ", ".join(sorted(x)))

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

print(result.head(30))

# Optional: filter for strong redundancy candidates
strong = result[
    (result["confidence"] >= 0.7) &
    (result["lift"] >= 2.0)
].copy()

print("\n=== Strong Redundancy Candidates ===")
print(strong)


result.to_excel("/Users/konradkrahl/Library/CloudStorage/OneDrive-Highberg/Desktop/Beck/Data/module_association_rules.xlsx", index=False)
strong.to_excel("/Users/konradkrahl/Library/CloudStorage/OneDrive-Highberg/Desktop/Beck/Data/module_association_rules_red.xlsx", index=False)