#%%

import polars as pl
from itertools import combinations
import matplotlib.pyplot as plt
import json
import webbrowser
import tempfile
import heapq


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
    intersection = len(pubs_a & pubs_b)
    union = len(pubs_a | pubs_b)

    jaccard = intersection / union 

    results.append({
        "Module_Pair": f"{mod_a} - {mod_b}",
        "Shared_Publications": shared,
        "Shared_Publication_Names": ", ".join(sorted(shared_pubs)),
        "Similarity_A_in_B": round(overlap_a_in_b, 4),
        "Similarity_B_in_A": round(overlap_b_in_a, 4),
        "Jaccard": round(jaccard,2),
    })

results_df = pl.DataFrame(results).sort(["Jaccard"], descending=[True])

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

# %%


#eventuell wie clusternaalye dann iterativ zusammenlegen, decision tree? 
#alles was bei beiden >0.8 hat zusammen, dann neue Similarity, dann wieder, dann neue etc, bis wir bei 300 angekommen sind
#loss metric is dann entscheidnend, Mittelwert z.b.?
#so was wie ein Dendrogramm interactive in dem ich sehen kann wie viele Publikationen es gibt

#Jaccard and clustering. containment (A in B / B in A)



# %%

#%%

THRESHOLD = 0.5
current_modules = {k: set(v) for k, v in modul_to_pubs.items()}
merge_history = []
iteration = 0


def jaccard(a, b):
    return len(a & b) / len(a | b) if a | b else 0.0

current_modules = {k: set(v) for k, v in modul_to_pubs.items()}
merge_history = []

heap = []
for mod_a, mod_b in combinations(list(current_modules.keys()), 2):
    j = jaccard(current_modules[mod_a], current_modules[mod_b])
    if j > 0:
        heapq.heappush(heap, (-j, mod_a, mod_b))

while heap:
    neg_j, mod_a, mod_b = heapq.heappop(heap)
    j = -neg_j

    if j < THRESHOLD:
        break

    if mod_a not in current_modules or mod_b not in current_modules:
        continue

    merged = current_modules[mod_a] | current_modules[mod_b]
    new_name = f"SuperModule_{len(merge_history) + 1}"

    merge_history.append({
        "iteration": len(merge_history) + 1,
        "module_a": mod_a,
        "module_b": mod_b,
        "jaccard": round(j, 4),
        "pub_count": len(merged),
    })

    del current_modules[mod_a]
    del current_modules[mod_b]
    current_modules[new_name] = merged

    for existing in list(current_modules.keys()):
        if existing == new_name:
            continue
        j_new = jaccard(merged, current_modules[existing])
        if j_new > 0:
            heapq.heappush(heap, (-j_new, new_name, existing))

print(f"Done. {len(merge_history)} total merges. Remaining modules: {len(current_modules)}")

#%%

# Save
pl.DataFrame(merge_history).write_excel("/Users/konradkrahl/Library/CloudStorage/OneDrive-Highberg/Desktop/Beck/Output/Merge_History.xlsx")

final_rows = [{"Super_Module": name, "Publikation": p} for name, pubs in current_modules.items() for p in sorted(pubs)]
pl.DataFrame(final_rows).write_excel("/Users/konradkrahl/Library/CloudStorage/OneDrive-Highberg/Desktop/Beck/Output/Final_SuperModules.xlsx")


#%%




# Build pub lookup per supermodule from merge_history
super_pubs = {}

# Reconstruct publication sets for each SuperModule using merge history
module_pubs_snapshot = {k: set(v) for k, v in modul_to_pubs.items()}

for i, m in enumerate(merge_history):
    name = f"SuperModule_{i+1}"
    merged_pubs = module_pubs_snapshot.get(m["module_a"], set()) | module_pubs_snapshot.get(m["module_b"], set())
    module_pubs_snapshot[name] = merged_pubs
    super_pubs[name] = list(merged_pubs)

# Also keep originals
for mod, pubs in modul_to_pubs.items():
    super_pubs[mod] = list(pubs)

# All modules that were ever consumed as children in a merge
all_children_in_merges = set()
for m in merge_history:
    all_children_in_merges.add(m["module_a"])
    all_children_in_merges.add(m["module_b"])

# SuperModule roots = created by merging but never consumed by a later merge
super_module_roots = [
    f"SuperModule_{i+1}"
    for i, m in enumerate(merge_history)
    if f"SuperModule_{i+1}" not in all_children_in_merges
]

# Original modules that were never touched by any merge
untouched_originals = [
    mod for mod in modul_to_pubs.keys()
    if mod not in all_children_in_merges
]

# Each is its own independent tree — no virtual "All Modules" wrapper
forest_roots = super_module_roots + untouched_originals

data = {
    "merges": merge_history,
    "pubs": super_pubs,
    "forest_roots": forest_roots,
    "untouched_originals": untouched_originals,
}
html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: Segoe UI, sans-serif; margin: 0; background: #fff; color: #626262; }}
  #tooltip {{
    position: absolute; background: #fff; border: 0.5px solid #ccc;
    border-radius: 8px; padding: 12px; font-size: 12px; max-width: 280px;
    max-height: 300px; overflow-y: auto; pointer-events: none; display: none;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  }}
  #tooltip h4 {{ margin: 0 0 6px; font-size: 13px; color: #1C0D45; }}
  #tooltip p {{ margin: 0 0 4px; color: #626262; }}
  #tooltip ul {{ margin: 4px 0 0; padding-left: 16px; }}
  #tooltip li {{ margin-bottom: 2px; }}
  svg text {{ font-family: Segoe UI, sans-serif; }}
</style>
</head>
<body>
<div id="tooltip"></div>
<div id="chart"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script>
const data = {json.dumps(data)};

const merges = data.merges;
const pubsMap = data.pubs;
const forestRoots = data.forest_roots;

const nodeMap = {{}};

function getOrCreate(name) {{
  if (!nodeMap[name]) nodeMap[name] = {{ name, children: [], pubs: pubsMap[name] || [] }};
  return nodeMap[name];
}}

merges.forEach((m, i) => {{
  const newName = "SuperModule_" + (i + 1);
  const parent = getOrCreate(newName);
  parent.jaccard = m.jaccard;
  parent.iteration = m.iteration;
  parent.pub_count = m.pub_count;
  parent.children = [getOrCreate(m.module_a), getOrCreate(m.module_b)];
  parent.pubs = pubsMap[newName] || [];
}});

const width = 960;
const rowHeight = 22;
const labelPad = 320;

let totalLeaves = 0;
const hierarchies = forestRoots.map(r => {{
  const h = d3.hierarchy(getOrCreate(r));
  totalLeaves += h.leaves().length;
  return h;
}});

const totalHeight = Math.max(totalLeaves * rowHeight, 400);
const svg = d3.select("#chart").append("svg")
  .attr("width", width)
  .attr("height", totalHeight + 40)
  .append("g").attr("transform", "translate(20,20)");

const tooltip = d3.select("#tooltip");

let yOffset = 0;
hierarchies.forEach(root => {{
  const leaves = root.leaves().length;
  const treeHeight = Math.max(leaves * rowHeight, 40);
  const cluster = d3.cluster().size([treeHeight, width - labelPad]);
  cluster(root);

  root.each(d => d.x += yOffset);

  svg.selectAll(null)
    .data(root.links())
    .join("path")
    .attr("fill", "none")
    .attr("stroke", "#B5D4F4")
    .attr("stroke-width", 1)
    .attr("d", d3.linkHorizontal().x(d => d.y).y(d => d.x));

  svg.selectAll(null)
    .data(root.descendants())
    .join("circle")
    .attr("cx", d => d.y)
    .attr("cy", d => d.x)
    .attr("r", d => d.data.children && d.data.children.length ? 5 : 3)
    .attr("fill", d => d.data.children && d.data.children.length ? "#0078A4" : "#1D5F94")
    .attr("stroke", "#fff")
    .attr("stroke-width", 1)
    .style("cursor", "pointer")
    .on("mouseover", function(event, d) {{
      const pubs = d.data.pubs || [];
      tooltip.style("display", "block")
        .html(`
          <h4>${{d.data.name}}</h4>
          ${{d.data.jaccard ? `<p>Jaccard: ${{d.data.jaccard}} | Iteration: ${{d.data.iteration}}</p>` : ""}}
          <p>${{pubs.length}} publications</p>
          <ul>${{pubs.slice(0, 50).map(p => `<li>${{p}}</li>`).join("")}}${{pubs.length > 50 ? `<li>... and ${{pubs.length - 50}} more</li>` : ""}}</ul>
        `);
    }})
    .on("mousemove", function(event) {{
      tooltip.style("left", (event.pageX + 12) + "px").style("top", (event.pageY - 20) + "px");
    }})
    .on("mouseout", () => tooltip.style("display", "none"));

  svg.selectAll(null)
    .data(root.leaves())
    .join("text")
    .attr("x", d => d.y + 8)
    .attr("y", d => d.x + 4)
    .attr("font-size", 10)
    .attr("fill", "#626262")
    .text(d => d.data.name.length > 40 ? d.data.name.slice(0, 40) + "…" : d.data.name);

  yOffset += treeHeight + 20;
}});
</script>
</body>
</html>
"""

tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8")
tmp.write(html)
tmp.close()
webbrowser.open(f"file://{tmp.name}")
print(f"Opened: {{tmp.name}}")


#Idee: 1. Schritt underperformer raus aus den Modulen
#2 Schritt Mergen: hier brauchen wir einen coefficent: Ähnlickeit * Umsatz? Wie gewichten wir das?
#3 Überprüfung


###oder der Jaqardt Index wird nach clicks einer Pub einem Modul und damit Umsatz gewichtet
###wenn also 2 module sehr ähnlich, aber bestimmte pubs in einem modul nicht genutzt oder fast keinen umsatz erzielen, dann streiche diese
###das modul wird dann zu einem neuen modul und nicht gemer
