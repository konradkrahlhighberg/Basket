#%%

import polars as pl


#%%

#load and merge data 

df_basket = pl.read_excel("/Users/konradkrahl/Library/CloudStorage/OneDrive-Highberg/Desktop/Beck/Data/module_association_rules.xlsx")
df_click = pl.read_excel("/Users/konradkrahl/Library/CloudStorage/OneDrive-Highberg/Desktop/Beck/Data/Module_Clicks.xlsx")
df_umsatz = pl.read_excel("/Users/konradkrahl/Library/CloudStorage/OneDrive-Highberg/Desktop/Beck/Data/Umsatzentwicklungen (vertraulich)_2026-03-10.xlsx", sheet_name="beck-online Module")

#problem: basket analyse vergelicht modul ählickeiten untereinander
#großer df? zu jedem vergleichpaar alle publikationen? + klicks + umsatz
#können wir über klickstat den anteiligen umsatz pro publikation errechnen?
#dann cluster analyse

#basket analyse 1. Cluster, pubs die z.b. immer hohe redundanz haben z.b.
#eventuell mean redundanz für jede pub?
#dann click und umsatz pro pub
#dann cluster


#step 1 module similariy
#step 2 publication similiarity based on occurence in moduls
#step 3 