# Souhrn
Implementace nyní ukládá deterministické pondělní snapshoty se sjednoceným tie-break řetězem a striktní seeding vazbou na oficiální Rolling žebříček.
Celkové počty: ✅ 11 / ⚠️ 0 / 🟨 0 / ❌ 0
Stručný verdikt: Všechny rankingové požadavky MSA jsou pokryty kódem a testy.

## Compliance Matrix
| SPEC-ID | Název | Stav | Důkaz (kód) | Důkaz (test) |
|---------|-------|------|-------------|--------------|
| MSA-R02 | Pondělní snapshot + hash | ✅ | `msa/services/standings_snapshot.py` L58-L74 | `tests/test_ranking_snapshots.py::test_build_and_confirm_monday_snapshot_is_stable` |
| MSA-R03 | Preview/Confirm s ETag | ✅ | `msa/services/standings_snapshot.py` L77-L109 | `tests/test_ranking_snapshots.py::test_confirm_fails_on_stale_preview` |
| MSA-R06 | Sjednocený tie-break chain | ✅ | `msa/services/ranking_common.py` L1-L26; `msa/services/standings.py` L228,L304,L418 | `tests/test_ranking_tiebreaks.py::test_unified_chain_orders_equal_points_consistently_for_all_modes` |
| MSA-R08 | Seeding baseline z Official Monday | ✅ | `msa/services/standings_snapshot.py` L148-L156; `msa/services/recalculate.py` L300-L309 | `tests/test_seeding_official_baseline.py::test_ensure_seeding_baseline_sets_previous_monday_if_missing` |
| MSA-R09 | TZ/DST Europe/Prague | ✅ | `msa/services/standings_snapshot.py` L26-L45 | `tests/test_ranking_prague_cutoff.py::test_activation_monday_across_dst_changes` |
| MSA-R10 | Alias & retence snapshotů | ✅ | `msa/services/standings_snapshot.py` L86-L101,L122-L145 | `tests/test_ranking_snapshots.py::test_no_change_week_creates_alias_not_payload` |

## Co je správně
- Snapshoty se ukládají jen jako pondělní data s deterministickým SHA256 hashem.
- Potvrzení snapshotu vyžaduje shodu hashů a chrání proti stale datům.
- Tie-break klíč sjednocuje pořadí podle bodů, best-N, eventů a nejlepšího výsledku.
- Seeding baseline nastaví nejbližší předchozí pondělí a vyžaduje existenci oficiálního snapshotu.
- Aktivace pondělí respektuje časovou zónu Europe/Prague i při přechodu na DST.

## Mezery / chyby
Žádné nalezené.

## Determinismus & stabilita
- Hash pondělního snapshotu je deterministický.
- Best-N, tie-breaky i penalizace jsou součástí snapshot pipeline.
- Confirm je chráněn expected_hash.
- Seeding čte jen snapshot.
- Cut-off používá Europe/Prague; DST pokryto testy.

## Důkazy
Viz tabulka výše.

## Appendix A – Mapování modulů → testy
- `msa/services/standings_snapshot.py` → `tests/test_ranking_snapshots.py`, `tests/test_ranking_prague_cutoff.py`
- `msa/services/ranking_common.py` → `tests/test_ranking_tiebreaks.py`
- `msa/services/recalculate.py` → `tests/test_seeding_official_baseline.py`

## Appendix B – Co spustit
```bash
pytest -q -k "standing or ranking or rtf or seed or snapshot or monday"
```
