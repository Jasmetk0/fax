# Wiki

## Aktuální stav
- Modely tagů, kategorií, článků a jejich revizí včetně průřezové tabulky `CategoryArticle`.
- CRUD pro články: seznam, detail, vytvoření, úprava, měkké mazání, historie, diff a revert.
- Správa kategorií s pořadím a přiřazováním článků.
- Tagování článků.
- Parser infoboxů se schématy (např. `country`, `city`) a podpora vnitřních odkazů `[[...]]`.
- API pro sugesci článků.
- Datové série (`DataSeries`, `DataPoint`) s kategoriemi (`DataCategory`),
  shortcody `{{data}}`, `{{chart}}`, `{{table}}`, `{{map}}`, REST API a webová
  správa datových sérií a bodů.

## Cíl
Kategorizovat datové série a umožnit generování tabulek a map z kategorií.

## TODO / Roadmapa
- Validace klíčů (rok vs. datum)
- Mapovací tabulka slug↔geo feature
- Více palet a škálování
- Cachování API
- Facety (filter unit, has_value_for_year)

## Poznámky
