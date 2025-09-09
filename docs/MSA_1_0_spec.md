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
Seed kotvy (kanonické…)  [ponech celý tvůj text]
… (ponech celý tvůj text až do konce specifikace)
---
