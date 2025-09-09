---
MSA 1.0 – Kompletní specifikace

Kontekst & platforma: Implementace v Python + Django jako součást fax_browseru (MSA = jedna z aplikací/stránek). 
 Admin režim: Veškeré změny dat (úpravy, mazání, generování/přegenerování, plánování, přidávání/odebírání hráčů, potvrzování kvaldy/MD, změny výsledků atd.) jsou povoleny jen při Admin Mode = ON. 
 Public: veřejné zobrazení je živé (bez publish gate). 
 fax_calendar: všechny datumy/pondělní logiky/snapshoty i admin widgety běží nad fax_calendar; kalendářová synchronizace je derivát plánu. 

 (Tohle je interní nástroj jen pro můj fiktivní svět FAX – nikoli pro veřejnou federaci. Předpokládá jediného super-admina (mě), důraz na deterministické losování, rychlé sandboxování „co kdyby“, a exporty do FAX Browser/OnGlass/Wiki. Cíl: pohodlně tvořit kalendář, registrace, kvaldy, MD, výsledky, rolling/season/RtF žebříčky a narativ světa. Všechny „reálné“ politiky (antidoping, disciplinárky, RBAC) jsou volitelné simulační přepínače, ne povinnost.)

 (Jsou to stránky MSA - Men’s Professional Squash Association) 

ZÁKLADNÍ KONCEPTY & REGISTRACE 
Seeding source: SNAPSHOT / CURRENT / NONE. 
SNAPSHOT & CURRENT → registrace se řadí vzestupně dle WR. 
NONE → celý seznam je free-drag (jako by všichni byli NR). 
Manual reordering (registrace): je povolen jen v rámci stejného rank-bucketu a uvnitř bloku NR. 
Seeds (S): mocnina 2 (garantuje pořadatel). 
Cutline (D): D = draw_size − qualifiers_count. 
Q pole: Q_draw_size = qualifiers_count × 2^qual_rounds. 
Skupiny (Players): Seeds → DA → Q → Reserve (ALT). Hráč nad čarou s WC zůstává v DA jako „DA (WC)“. 
Top čítače (Players): S / D / Q_draw_size / WC used/limit. 
Oddělovače (Players): 
po posledním seedu (oddělí Seeds od DA), 
za D (Direct cutline: oddělí DA od Q), 
mezi Q a Reserve. 
Licence hráčů: licenses = [seasons…]. Hráč smí nastoupit pouze s licencí pro sezónu turnaje. 
Gating: pokud některý aktivní hráč nemá licenci, jsou blokovány Continue/Confirm Qualification i Confirm Main Draw (inline akce „přiřadit licenci“). 

WILD CARDS 
WC (hlavní pole): 
   hráč nad čarou → jen štítek „DA (WC)“ (nečerpá limit), 
   hráč pod čarou → WC ho zvedne do Direct, čerpá wc_slots, poslední DA padá do Q. 
 Snížení wc_slots pod aktuální využití blokuje uložení, dokud se nepřebývající WC neodstraní. 
QWC (kvalifikace): QWC vytáhne hráče z Reserve do Q (čerpá q_wc_slots). U hráče už v Q je QWC jen label. 

RECALCULATE & PARAMETRY 
Recalculate placements: změny S/K/R/draw_size ani změna seeding source se neaplikují hned; admin spustí Recalculate, uvidí diff, potvrdí. 
Zachová se ruční pořadí uvnitř stejného rank-bucketu a v bloku NR; kdo přejde přes čáru/bucket, tomu se lokální pořadí resetne. 
Brutální reset: (změna snapshotu nebo S/K/R/draw_size) → návrat do registrace. Předtím uložíme ARCHIVNÍ SNAPSHOT (hráči, kvalda, MD, plán, výsledky). Undo/Redo se vyčistí, archiv zůstává. 

KVALIFIKACE — FLOW & SEEDING 
Flow: Recalculate → Continue to Qualification (možné přidat QWC) → Confirm Qualification (Auto generate / Manual; po generaci dovolena ruční editace). 
Seedy v kvaldě (na 1 kvalifikaci): pro R kol 2^(R−2) (R=1→0; R=2→TOP; R=3→TOP+BOTTOM; R=4→TOP+BOTTOM+2×MIDDLE; …). 
Rozdělení seedů mezi K = qualifiers_count kvalifikací: globální pořadí Q-seedů rozděl na tiery po K kusech: Tier1→TOP, Tier2→BOTTOM, Tier3→MIDDLE A, Tier4→MIDDLE B …; seedy na odpovídající kotvy, nenasazení náhodně. 
Editace po generaci: seedy jen mezi kotvami svého tieru (i napříč kvalifikacemi); nenasazení jen na nenasazené sloty (také napříč). 
Remove & Replace: při odstranění hráče se okamžitě dosadí další z Reserve na jeho místo (včetně seed kotvy). 
BYE v kvaldě: neřešíme; pořadatel garantuje plná pole. 

LUCKY LOSERS (LL) 
Vznik: poražení finalisté kvalifikace po uložení finále → LL fronta. 
Pořadí: dle WR snapshotu (ties ručně), NR na konci. 
Nasazení do MD: 
vznikne díra a LL nejsou → slot PENDING, automaticky ho obsadí LL #1 jakmile vznikne, 
admin může „Use Reserve now“, 
jakmile LL existují, mají přednost; dojdou-li, padá se na Reserve. 
Prefix invariant: LL v MD tvoří vždy prefix LL fronty. Reinstat původního hráče je možný jen od nejhoršího právě nasazeného LL směrem nahoru. Odebrat LL úplně → jeho místo ihned bere další v pořadí. 

OFFICIAL SEEDING (po kvaldě) 
Bloky: Seeding → DA → WC (ti, co vešli díky WC) → Q (vítězové kvaldy) → LL (ti, co jsou v MD). 
Řazení uvnitř bloků dle WR snapshotu (ties ručně), NR na konci. 
„DA (WC)“ zůstává v bloku DA. 

MAIN DRAW (MD) 
Seed kotvy (kanonické; seed se hýbe jen v rámci svého bandu/kotvy): 
MD16: 1→{1}, 2→{16}, 3–4→{9,8}, 5–8→{4,5,12,13}, 9–16→{2,3,6,7,10,11,14,15}. 
MD32: 1→{1}, 2→{32}, 3–4→{17,16}, 5–8→{8,9,24,25}, 9–16→{4,5,12,13,20,21,28,29}. 
MD64: 1→{1}, 2→{64}, 3–4→{33,32}, 5–8→{16,17,48,49}, 9–16→{8,9,24,25,40,41,56,57}, 17–32→{4,5,12,13,20,21,28,29,36,37,44,45,52,53,60,61}. 
MD128+: obecné pravidlo „end-pointy zmenšujících se segmentů“ po bandech (3/4, 5/8, 9/16, 17/32, 33/64, 65/128…). 
Kvalifikanti v MD: vždy nenasazení. 
MD po kvaldě: vítězové kvaldy se deterministicky náhodně rozlosují na unseeded pozice. 
MD dřív než kvalda: každá K# dostane zamčený unseeded slot „Winner K#“; po finále se vítěz auto-doplní (mapping je zamčený). 
Nepower-of-two (např. 24/48): embed do nejbližší vyšší šablony (32/64). Zápasy se single-BYE nevytváříme; dotyčný seed čeká v dalším kole. 
Povolené přesuny: 
MD: nenasazení napříč celým MD mezi unseeded sloty; seedy jen uvnitř svého bandu/kotvy. 
Qual: nenasazení mezi kvalifikacemi (jen na nenasazené sloty); seedy jen mezi kotvami svého tieru. 
Confirm/Remove constraints: po Confirm MD lze hráče odebrat jen pokud jeho R1 nemá výsledek; jinak je nutné výsledek smazat či vyřešit přes „Needs review“. 
Third place: pokud third_place_enabled, vzniká auto po obou SF a je součástí stavu Complete. 
Reopen Main Draw: 
Bez výsledků → plný návrat do editační fáze. 
S výsledky → nabídni Hard (smazat výsledky v zápasech, kde se mění dvojice) / Soft (přelosovat/posunout jen R1 bez výsledku) / Cancel. 

GENEROVÁNÍ / RE-GENEROVÁNÍ (MD & QUAL) 
Deterministická náhoda: každá (re)generace ukládá rng_seed; UI ukáže v Preview diff, k dispozici Reroll; seed jde do historie (Undo/Redo). 
Preview diff: vždy ukázat změny kotev/slotů, přesuny seedů (bandy), nenasazených, seznam dotčených zápasů a použitý rng_seed. 
Operace: 
Regenerate Draw: kompletní přelosování (MD: seedy drží band/anchor; Qual: seedy drží tier-kotvy; nenasazení se losují znovu). 
Regenerate Unseeded (MD): přehází jen nenasazené (DA/WC/Q/LL) v MD. 
Regenerate by band/anchor: cílené přelosování vybraného bandu/vrstvy (MD: 3/4, 5/8, 9/16, 17/32, Unseeded; Qual: TOP/BOTTOM/MIDDLE A/B/…/Unseeded). 
Existující výsledky: 
Soft: mění/přelosuje jen R1 bez výsledku; ostatní zůstává. 
Hard: smaže výsledky ve všech zápasech, kde změna ruší stávající dvojici; ostatní výsledky zůstanou. 
Cancel: nic se nemění. 

PLÁNOVÁNÍ (MVP) 
Model: společná denní fronta pro Q i MD; unikát (tournament, play_date, order). 
Operace: 
Swap = výměna (play_date, order) (i napříč dny). 
Insert = vyjmutí ze starého dne, kompaktování dne, vložení na cílové (play_date, order) a přečíslování 1..N. 
Clear, Normalize Day, Undo/Redo (každá operace = 1 krok). 
Soft Regenerate dopad: pokud se změní dvojice zápasu, jeho plán (play_date/order) se vymaže; ostatní plán zůstává. 
Kalendář sync (feature-flag): calendar_sync_enabled = false (default). Po zapnutí Režim C: 1 celodenní „Day Order“ event na den; popis = očíslovaný seznam zápasů. Změny pořadí/přesuny přepisují popis; přesun mezi dny přesune řádek mezi day-eventy. (Později přechod na per-match eventy.) 

VÝSLEDKY & VSTUP SKÓRE 
Best-of (defaulty): turnaj definuje q_best_of ∈ {3,5} a md_best_of ∈ {3,5}. Nové zápasy přebírají best_of dle fáze (Qual/MD). Změna defaultů nemění existující zápasy. 
Override per match: „Use default (BO{best_of}) / BO5 / BO3 / Win only“. Win only vyžaduje jen vítěze (volitelná poznámka) a ignoruje sety. 
Sady & odemykání: BO5 zobrazuje 5 řádků (4–5 zamčené), BO3 3 (3 zamčený). Odemkni #4 při 1:1, #5 při 2:2. Po dosažení potřebných výher se zbytek zamkne. 
Auto-scoring: points_to_win 11 (default); win_by_two ON/OFF per turnaj/match. 
ON: winner = max(points_to_win, loser+2); OFF: winner = points_to_win, loser ≤ points_to_win−1. 
Manuální override je povolen, pokud je kompatibilní s vybraným best-of; RET/DQ/WO mohou porušit win-by-two. 
Speciální výsledky: WO/RET/DQ kdykoli; vítěz dle pravidel, zbývající sety zůstanou prázdné/zamčené. 
Edit vítěze (bez kaskády): změna vítěze nevymaže downstream. Systém propaguje nového hráče do navazujících kol a označí dotčené zápasy „Needs review“ (vykřičník). U každého lze kliknout a uprav/potvrď; po potvrzení vykřičník zmizí. Do vyřešení může být progrese z těchto uzlů pozastavena. Plán zůstává, pokud admin nezvolí přeplánování. 
Provisional: lze uložit i bez (obou) známých hráčů; neprogresuje. Po dosazení obou nutné rychlé potvrzení vítěze (volitelně mapping setů). 
Bulk best-of tools: hromadné nastavení BO3/BO5/Win-only na neodehrané zápasy (kolo/sekce). 
BYE zápasy nevznikají: pokud by pairing měl jediného hráče, zápas se nevytvoří a hráč postoupí. 

SCORING & CATEGORY/SEASON 
CategorySeason (unikát): (category, season, draw_size) je unikátní. 
Ukládá: md_seeds_count, md_seed_levels (info), qualifiers_count, qual_rounds, qual_seeds_per_bracket = 2^(R−2), qual_seed_levels, wc_slots_default, q_wc_slots_default, a tabulky scoring_md (Winner, Runner-Up, Third, Fourth, SF, QF, R16, R32, …) a scoring_qual_win (body za výhry v kvaldě per round). 
Turnaj odkazuje na CategorySeason a při vytvoření si snapshne scoring (pozdější změny CS nemění hotové turnaje). 
Scoring politika: 
Qualifier = Q-wins body + MD body. 
Lucky Loser si ponechá Q-wins a přidává MD za postup v MD. 
BYE pravidlo: prohra v prvním odehraném zápase po BYE → body za předchozí kolo; po první výhře bodování standardně. 
Void/cancellation: „Award up to last fully completed round“ (částečné kolo = 0; third-place body jen pokud zápas odehrán; Q-wins jen za reálně vyhrané kvalifikační výhry). 

ŽEBŘÍČKY (JEDNA TABULKA, DVA MÓDY) + ROLLING 
Season mode (Sezonní standings): bere turnaje s end_date uvnitř sezóny; pro každého hráče sčítá top min(N, played), N = Season.best_N. Zobrazuje COUNTED / DROPPED a „Season TOTAL“. 
Ties: 1) vyšší průměr (total / counted), 2) stále shoda → sdílené místo (competition ranking). 
RtF mode (Road to Finals): stejné body jako Season mode, ale vítězové adminem určených „auto-TOP“ kategorií jsou připíchnuti nahoře v pořadí těchto kategorií; uvnitř auto-TOP se třídí podle bodů. Počet finálových slotů je konfigurovatelný per Season. Po Finals je RtF zmražen do konce sezóny. 
Rolling ranking (hlavní): 
Aktivace: body z turnaje vstoupí do Rolling na první pondělí striktně po end_date (končí-li v pondělí, aktivace je následující pondělí). 
Expirace: body vypadnou na začátku pondělí přesně po 61 týdnech od aktivačního pondělí. 
Weekly snapshots: každé pondělí 00:00 uložíme neměnný snapshot; lze explicitně Rebuild snapshot(s). 
Best-N v Rolling: použij best_N té sezóny, do níž spadá datum snapshotu; pokud datum neleží v žádné sezóně, použij best_N z poslední dostupné sezóny (fallback). Inkluze turnajů v Rolling je čistě dle 61týdenního okna (nezávisle na sezónních hranicích). 
Adjustments (body/penále): 
Admin může přidat POINTS ±X se start_monday a duration_weeks (např. +1000 na 61 týdnů) a BEST_N_PENALTY (např. −1 turnaj na 50 týdnů). 
Scope: ROLLING_ONLY / SEASON=YYYY / BOTH. 
Vše je auditováno (povinný zápis do audit logu). 

ARCHIV / HISTORIE / LIMITY 
Undo/Redo: cca 300 kroků nebo ~8 MB historie (co nastane dřív). 
Archivní snapshoty: při Confirm/Generate/Regenerate/Manual commit/Reopen/Brutal reset; limit 50 snapshotů nebo 50 MB na turnaj (co nastane dřív); admin může mazat. 
Country protection: žádná (ani soft). 

AUDIT & DUPLICITY HRÁČŮ 
Pořadí registrace (audit): seznam přihlášek se renderuje v pořadí snapshotu/CURRENT; při NONE je free-drag. 
Primární mapování importů: podle (source, external_key); dvojice je unique. 
Fuzzy návrhy: pokud klíče chybí, UI nabídne jméno+země (a další hinty). 
„Quick add“ s varováním: při vysoké podobnosti zobrazíme výrazné varování; admin může propojit na existujícího nebo vědomě vytvořit nového. 
Merge Players: nouzová admin akce; přenese účasti/výsledky a duplicitní záznam uzamkne. 
Ranking audit na turnaji: vždy ukazujeme režim nasazování a snapshot label/datum. 
