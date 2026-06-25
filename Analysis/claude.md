Claude antwortet



```

#%%



import polars as pl

from itertools import combinations

import matplotlib.pyplot as plt







#%%



#we keep only the ones with valid numbers in 2025 per klicks

#Each 



df = pl.read_excel("/Users/konradkrahl/Library/CloudStorage/OneDrive-Highberg/Desktop/Beck/Data/Weitere Module.xlsx")

df = df.with_columns(pl.col('2025 Klicks Gesamtjahr').cast(pl.Float64, strict=False)).drop_nulls(subset=["2025 Klicks Gesamtjahr"])

df = df.filter((pl.col("Publikationen") != "null") & (pl.col('2025 Klicks Gesamtjahr') >0) & (pl.col('Modul') != "null"))

df = df[["Publikationen", "Modul"]]



##Analysis



df["Publikationen"].unique()

df["Modul"].unique()



#572 Module

#3082 Publikation



#->Ein Modul beinhaltet mehrere Publikationen



#%%



df_Darstellungsform = pl.read_excel("/Users/konradkrahl/Library/CloudStorage/OneDrive-Highberg/Desktop/Beck/Data/Publikation_Darstellungsform.xlsx")





#%%



# Group publications per module

modul_to_pubs = {}

for row in df.iter_rows(named=True):

    pub = row["Publikationen"]

    modul = row["Modul"]

    if modul not in modul_to_pubs:

        modul_to_pubs[modul] = set()

    modul_to_pubs[modul].add(pub)



# Compare every module pair

modules = list(modul_to_pubs.keys())

results = []



for mod_a, mod_b in combinations(modules, 2):

    pubs_a = modul_to_pubs[mod_a]

    pubs_b = modul_to_pubs[mod_b]



    shared_pubs = pubs_a & pubs_b

    shared = len(shared_pubs)



    overlap_a_in_b = shared / len(pubs_a) if pubs_a else 0.0

    overlap_b_in_a = shared / len(pubs_b) if pubs_b else 0.0



    results.append({

        "Module_Pair": f"{mod_a} - {mod_b}",

        "Shared_Publications": shared,

        "Shared_Publication_Names": ", ".join(sorted(shared_pubs)),

        "Similarity_A_in_B": round(overlap_a_in_b, 4),

        "Similarity_B_in_A": round(overlap_b_in_a, 4),

    })



results_df = pl.DataFrame(results).sort(["Similarity_A_in_B","Similarity_B_in_A"], descending=[True,True])



results_df.write_excel("/Users/konradkrahl/Library/CloudStorage/OneDrive-Highberg/Desktop/Beck/Output/Similarity.xlsx")



#%%



#Analysis 



results_df_filtered = results_df.filter(pl.col("Shared_Publications") > 0).sort("Shared_Publications", descending=True)

print(results_df_filtered)



results_df_filtered["Shared_Publications"].hist(bin_count=50).filter(pl.col("count") >0)

results_df_filtered["Similarity_A_in_B"].hist(bin_count=10).filter(pl.col("count") >0)





# %%





#Example 'Justiz OPTIMUM - Beck Premium Rahmenvertrag Bund'



print(results_df_filtered[0,2])



Modul_1 = df.filter(pl.col("Modul")=="Justiz OPTIMUM")

Modul_2 = df.filter(pl.col("Modul")=="Beck Premium Rahmenvertrag Bund")





#%%



#comparison percentage



x = range(len(results_df_filtered))



fig, ax = plt.subplots(figsize=(12, 5))



ax.plot(x, results_df_filtered.sort("Similarity_A_in_B", descending=True)["Similarity_A_in_B"].to_list(), label="Similarity A in B")

ax.plot(x, results_df_filtered.sort("Similarity_B_in_A", descending=False)["Similarity_B_in_A"].to_list(), label="Similarity B in A")

ax.set_ylabel("Similarity")

ax.legend()



plt.tight_layout()

plt.show()



#Cave! not sorted simultaniously, so just for presentation









this is my similiartity analysis

-i want toi do the following:

-compute which pubs is in which module, as it is,

-then identify high similirity for example by mean (a in b + b in a /2)

-put them togehter

-then start new and make new similiarty anaysis







challenge that, is that meaningfull

```



