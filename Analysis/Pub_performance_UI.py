import polars as pl
import json
import pathlib

# ── 1. Load & clean ──────────────────────────────────────────────────────────

df = pl.read_excel("/Users/konradkrahl/Library/CloudStorage/OneDrive-Highberg/Desktop/Beck/Data/Module_Clicks.xlsx")

year_cols = [
    "2019 \nKlicks Gesamtjahr",
    "2020 \nKlicks Gesamtjahr",
    "2021 \nKlicks Gesamtjahr",
    "2022 \nKlicks Gesamtjahr",
    "2023 \nKlicks Gesamtjahr",
    "2024 \nKlicks Gesamtjahr",
    "2025 \nKlicks Gesamtjahr",
]

df_num = df.with_columns([
    pl.col(c)
      .cast(pl.Utf8)
      .str.replace_all(r"[^\d.]", "")
      .replace("", None)
      .cast(pl.Float64)
    for c in year_cols
])

# ── 2. Build publication → module → [year values] structure ──────────────────

YEARS = ["2019", "2020", "2021", "2022", "2023", "2024", "2025"]

pub_map: dict[str, dict[str, list[float | None]]] = {}

for row in df_num.iter_rows(named=True):
    pub = row.get("Publikation")
    mod = row.get("Module")
    if not pub or not mod:
        continue
    if pub not in pub_map:
        pub_map[pub] = {}
    if mod not in pub_map[pub]:
        pub_map[pub][mod] = [None] * 7
    for i, col in enumerate(year_cols):
        v = row.get(col)
        if v is not None:
            current = pub_map[pub][mod][i]
            pub_map[pub][mod][i] = (current or 0) + v

# ── 3. Compute filter ranks ──────────────────────────────────────────────────

def total_clicks(modules: dict) -> float:
    return sum(v for arr in modules.values() for v in arr if v is not None)

def max_yoy_change(modules: dict) -> float:
    max_chg = 0.0
    for arr in modules.values():
        for i in range(1, len(arr)):
            a, b = arr[i - 1], arr[i]
            if a and b and a > 0:
                chg = abs((b - a) / a)
                if chg > max_chg:
                    max_chg = chg
    return max_chg

def module_spread(modules: dict) -> float:
    totals = [sum(v for v in arr if v is not None) for arr in modules.values()]
    return max(totals) - min(totals) if totals else 0.0

ranks = {
    pub: {
        "total":  total_clicks(mods),
        "change": max_yoy_change(mods),
        "spread": module_spread(mods),
    }
    for pub, mods in pub_map.items()
}

# ── 4. Serialise to JSON ─────────────────────────────────────────────────────

data_json = json.dumps({"pub_map": pub_map, "ranks": ranks}, ensure_ascii=False)

# ── 5. HTML dashboard ────────────────────────────────────────────────────────

HTML = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Module Clicks Dashboard</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  :root {{
    --brand:    #0078A4;
    --accent:   #F96E46;
    --dark:     #1C0D45;
    --cobalt:   #1D5F94;
    --text:     #626262;
    --bg:       #ffffff;
    --surface:  #f5f6f7;
    --border:   rgba(0,0,0,0.1);
    --radius:   8px;
  }}
  body {{ font-family: "Segoe UI", system-ui, sans-serif; color: var(--text); background: var(--bg); padding: 24px; }}
  h1 {{ font-size: 20px; font-weight: 600; color: var(--dark); margin-bottom: 20px; }}
  .toolbar {{ display: flex; flex-wrap: wrap; align-items: flex-end; gap: 16px; margin-bottom: 16px; }}
  .field {{ display: flex; flex-direction: column; gap: 4px; }}
  .field label {{ font-size: 11px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; color: var(--text); }}
  select {{
    font-size: 14px; font-family: inherit; padding: 7px 10px;
    border: 1px solid var(--border); border-radius: var(--radius);
    background: var(--bg); color: var(--dark); min-width: 240px; cursor: pointer;
  }}
  select:focus {{ outline: 2px solid var(--brand); outline-offset: 2px; }}
  .filters {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; }}
  .fbtn {{
    font-size: 12px; font-family: inherit; padding: 5px 14px; border-radius: 20px;
    border: 1px solid var(--border); background: transparent; color: var(--text); cursor: pointer;
  }}
  .fbtn.active {{ background: var(--brand); color: #fff; border-color: var(--brand); }}
  .fbtn:hover:not(.active) {{ background: var(--surface); }}
  .metrics {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }}
  .mc {{ background: var(--surface); border-radius: var(--radius); padding: 12px 16px; flex: 1; min-width: 120px; }}
  .mc .lbl {{ font-size: 11px; color: var(--text); margin-bottom: 4px; }}
  .mc .val {{ font-size: 22px; font-weight: 600; color: var(--dark); }}
  .legend {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; font-size: 12px; color: var(--text); }}
  .li {{ display: flex; align-items: center; gap: 5px; }}
  .ld {{ width: 18px; height: 3px; border-radius: 2px; flex-shrink: 0; }}
  .chart-wrap {{ position: relative; width: 100%; height: 360px; }}
  .no-data {{ display: flex; align-items: center; justify-content: center; height: 200px; color: var(--text); font-size: 14px; }}
  hr {{ border: none; border-top: 1px solid var(--border); margin: 0 0 20px; }}
</style>
</head>
<body>
<h1>Module Klick-Analyse</h1>

<div class="toolbar">
  <div class="field">
    <label>Publikation</label>
    <select id="pub-select"></select>
  </div>
</div>

<div class="filters" id="filters">
  <button class="fbtn active" data-f="none">Alle</button>
  <button class="fbtn" data-f="top-volume">↑ Klickvolumen</button>
  <button class="fbtn" data-f="biggest-change">↑ Veränderung YoY</button>
  <button class="fbtn" data-f="module-spread">↑ Modulunterschiede</button>
</div>

<div style="display:flex;gap:8px;margin-bottom:20px;align-items:center;">
  <span style="font-size:11px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--text);">Ansicht</span>
  <button class="fbtn active" id="btn-abs">Absolut</button>
  <button class="fbtn" id="btn-rel">Relativ (%)</button>
  <button class="fbtn" id="btn-diff">Δ Unterschiede</button>
</div>



<hr>

<div class="metrics" id="metrics"></div>
<div class="legend" id="legend"></div>
<div class="chart-wrap"><canvas id="chart" role="img" aria-label="Klicks je Modul über Jahre"></canvas></div>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script>
const RAW = {data_json};
const pub_map = RAW.pub_map;
const ranks   = RAW.ranks;
const YEARS   = ["2019","2020","2021","2022","2023","2024","2025"];

const COLORS = [
  "#0078A4","#F96E46","#1D5F94","#5F0F40","#1C0D45",
  "#3a9e70","#c4872a","#7c3aed","#0d9488","#be185d","#854d0e","#1e40af"
];
const DASHES = [
  []       , [6,3]    , [2,2]    , [8,3,2,3],
  [4,2]    , [1,3]    , [10,4]   , [5,5]
];

let activeFilter = "none";
let chart = null;
let allPubs = Object.keys(pub_map).sort();
let filteredPubs = [...allPubs];

function sortedPubs(filter) {{
  const arr = [...allPubs];
  if (filter === "top-volume")     return arr.sort((a,b) => ranks[b].total  - ranks[a].total).slice(0, 50);
  if (filter === "biggest-change") return arr.sort((a,b) => ranks[b].change - ranks[a].change).slice(0, 50);
  if (filter === "module-spread")  return arr.sort((a,b) => ranks[b].spread - ranks[a].spread).slice(0, 50);
  return arr;
}}

function fillDropdown(pubs, selected) {{
  const sel = document.getElementById("pub-select");
  sel.innerHTML = "";
  pubs.forEach(p => {{
    const o = document.createElement("option");
    o.value = p; o.textContent = p;
    if (p === selected) o.selected = true;
    sel.appendChild(o);
  }});
}}

function renderMetrics(pub) {{
  const mods = pub_map[pub];
  const allVals = Object.values(mods).flat().filter(v => v != null);
  const total   = allVals.reduce((a,b) => a+b, 0);
  const peak    = allVals.length ? Math.max(...allVals) : 0;
  const latest  = Object.values(mods).map(a => a[6] || 0).reduce((a,b) => a+b, 0);
  const modCnt  = Object.keys(mods).length;
  document.getElementById("metrics").innerHTML = `
    <div class="mc"><div class="lbl">Module</div><div class="val">${{modCnt}}</div></div>
    <div class="mc"><div class="lbl">Klicks gesamt</div><div class="val">${{total.toLocaleString("de-DE")}}</div></div>
    <div class="mc"><div class="lbl">Peak (Modul/Jahr)</div><div class="val">${{peak.toLocaleString("de-DE")}}</div></div>
    <div class="mc"><div class="lbl">2025 gesamt</div><div class="val">${{latest.toLocaleString("de-DE")}}</div></div>
  `;
}}

let relativeMode = false;
let diffMode = false;

function toRelative(mods) {{
  const modNames = Object.keys(mods);
  const result = {{}};
  modNames.forEach(m => result[m] = []);
  YEARS.forEach((_, i) => {{
    const yearTotal = modNames.reduce((s, m) => s + (mods[m][i] || 0), 0);
    modNames.forEach(m => {{
      const v = mods[m][i];
      result[m].push(yearTotal > 0 && v != null ? (v / yearTotal) * 100 : null);
    }});
  }});
  return result;
}}

function toDiffArr(mods) {{
  const relMods = toRelative(mods);
  const names = Object.keys(mods);
  const result = {{}};
  names.forEach(m => {{
    result[m] = YEARS.map((_, i) => {{
      if (i === 0) return null;
      const prev = relMods[m][i-1], cur = relMods[m][i];
      if (prev == null || cur == null) return null;
      return parseFloat((cur - prev).toFixed(2));
    }});
  }});
  return result;
}}

function renderChart(pub) {{
  renderMetrics(pub);
  const rawMods = pub_map[pub];

  let mods, labels, chartType, isDiff = false;
  if (diffMode) {{
    mods = toDiffArr(rawMods); labels = YEARS.slice(1); chartType = "bar"; isDiff = true;
  }} else if (relativeMode) {{
    mods = toRelative(rawMods); labels = YEARS; chartType = "line";
  }} else {{
    mods = rawMods; labels = YEARS; chartType = "line";
  }}

  const modNames = Object.keys(mods);
  const datasets = modNames.map((m, i) => {{
    const col = COLORS[i % COLORS.length];
    if (isDiff) return {{
      label: m,
      data: mods[m].slice(1),
      backgroundColor: mods[m].slice(1).map(v => v == null ? "transparent" : v >= 0 ? col+"cc" : col+"55"),
      borderColor: col, borderWidth: 1.5, borderRadius: 3,
    }};
    return {{
      label: m, data: mods[m], borderColor: col, backgroundColor: "transparent",
      borderDash: DASHES[i % DASHES.length], borderWidth: 2, tension: 0.3, pointRadius: 3, spanGaps: true,
    }};
  }});

  document.getElementById("legend").innerHTML = datasets.map((ds, i) => {{
    const col = COLORS[i % COLORS.length];
    const swatch = isDiff
      ? `<span class="ld" style="background:${{col}};height:12px;width:12px;border-radius:2px"></span>`
      : `<span class="ld" style="background:${{col}}"></span>`;
    return `<span class="li">${{swatch}}${{ds.label}}</span>`;
  }}).join("");

  if (chart) {{ chart.destroy(); chart = null; }}
  chart = new Chart(document.getElementById("chart"), {{
    type: chartType,
    data: {{ labels, datasets }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{ callbacks: {{ label: ctx => {{
          const v = ctx.parsed.y;
          if (v == null) return `${{ctx.dataset.label}}: –`;
          if (diffMode) return `${{ctx.dataset.label}}: ${{v > 0 ? "+" : ""}}${{v.toFixed(2)}} pp`;
          if (relativeMode) return `${{ctx.dataset.label}}: ${{v.toFixed(1)}} %`;
          return `${{ctx.dataset.label}}: ${{v.toLocaleString("de-DE")}}`;
        }}}}}}
      }},
      scales: {{
        x: {{ grid: {{ color: "rgba(0,0,0,0.06)" }}, ticks: {{ autoSkip: false }} }},
        y: {{
          grid: {{ color: "rgba(0,0,0,0.06)" }},
          max: relativeMode && !diffMode ? 100 : undefined,
          ticks: {{ callback: v => diffMode
            ? (v > 0 ? "+" : "") + v.toFixed(1) + " pp"
            : relativeMode ? v.toFixed(0) + " %" : (v >= 1000 ? (v/1000).toFixed(0)+"k" : v)
          }}
        }}
      }}
    }}
  }});
}}
document.getElementById("btn-abs").addEventListener("click", () => {{
  relativeMode = false; diffMode = false;
  document.getElementById("btn-abs").classList.add("active");
  document.getElementById("btn-rel").classList.remove("active");
  document.getElementById("btn-diff").classList.remove("active");
  renderChart(document.getElementById("pub-select").value);
}});

document.getElementById("btn-rel").addEventListener("click", () => {{
  relativeMode = true; diffMode = false;
  document.getElementById("btn-rel").classList.add("active");
  document.getElementById("btn-abs").classList.remove("active");
  document.getElementById("btn-diff").classList.remove("active");
  renderChart(document.getElementById("pub-select").value);
}});

document.getElementById("btn-diff").addEventListener("click", () => {{
  diffMode = true; relativeMode = false;
  document.getElementById("btn-diff").classList.add("active");
  document.getElementById("btn-abs").classList.remove("active");
  document.getElementById("btn-rel").classList.remove("active");
  renderChart(document.getElementById("pub-select").value);
}});

// Init
filteredPubs = sortedPubs(activeFilter);
fillDropdown(filteredPubs, filteredPubs[0]);
renderChart(filteredPubs[0]);

document.getElementById("pub-select").addEventListener("change", e => renderChart(e.target.value));

document.getElementById("filters").addEventListener("click", e => {{
  const btn = e.target.closest(".fbtn");
  if (!btn) return;
  document.querySelectorAll("#filters .fbtn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  activeFilter = btn.dataset.f;
  const cur = document.getElementById("pub-select").value;
  filteredPubs = sortedPubs(activeFilter);
  const sel = filteredPubs.includes(cur) ? cur : filteredPubs[0];
  fillDropdown(filteredPubs, sel);
  renderChart(sel);
}});



</script>
</body>
</html>
"""

out = pathlib.Path("/Users/konradkrahl/Library/CloudStorage/OneDrive-Highberg/Desktop/Beck/UI Output/module_clicks_dashboard.html")
out.write_text(HTML, encoding="utf-8")
print(f"Dashboard written → {out.resolve()}")



##Idee:
#Long Format Data Frame Module, Pubs
#KPIS aud Basketanalyse
#Umsatz und Klicks
#dann darüber eine Clusteranalyse