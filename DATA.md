# Data guide

## Extracted spectra

Each CSV row is one 12 × 12 px patch of powder (about 8 mm), averaged into one reflectance
spectrum. Every dish gives about 150 patches. Files keep every dish that was scanned; the
notebooks select dishes with the `species` and `role` columns.

| File | Contents |
|---|---|
| `samples_out/training_samples.csv` | Robusta sessions 1 (1 Sep) and 2 (4 Sep). 4,833 patches: robusta calibration (RB100, 3 dishes), robusta + chicory calibration (15), one arabica blend kept out of the series (3), pure chicory for extrapolation checks (3), and unknowns (9) |
| `batch3_out/training_samples.csv` | Robusta session 3 (8 Sep): robusta + chicory, 15 dishes, 2,250 patches |
| `final_results/training_samples_combined.csv` | Robusta sessions combined, used by the earlier robusta notebooks |
| `arabica_out/training_samples.csv` | Arabica + chicory blends from 4 and 8 Sep: 30 dishes, 4,500 patches |
| `arabica_out/arabica_chicory_all_sessions.csv` | The file the arabica models use: the 30 blends, pure arabica AB100 from 1 Sep (3 dishes) and pure chicory (3) |
| `arabica_robusta_out/training_samples.csv` | AR series, all three sessions: 6,740 patches, 45 dishes (AR blends, the 13:30 AR100 dishes, and the J/K/L test samples marked `unknown`) |

### Columns

| Column | Meaning |
|---|---|
| `sample_id` | Patch id |
| `scan`, `day`, `capture` | Source scan file, session number, re-stir (1–3) |
| `label`, `plate`, `group` | Blend label as written in the lab (e.g. `RB[70:30]`); blend within a session (`day2\|RB[70:30]`); dish id, unique per scan (`<scan>\|<label>`) |
| `species` | `robusta`, `arabica`, `chicory`, `robusta_chicory`, `arabica_chicory`, `arabica_robusta` or `unknown` |
| `role` | `calibration` (used for models), `extrapolation_check`, `out_of_series`, `unknown` |
| `robusta_pct`, `arabica_pct`, `chicory_pct` | Composition from the label, % by mass |
| `fold_level`, `fold_plate`, `fold_capture`, `split_holdout` | Fold ids used by the early robusta notebooks |
| `patch_row`, `patch_col`, `n_pixels` | Patch position in the dish and valid pixels in it |
| `source` | (arabica all-sessions file only) `arabica_out (raw counts)` or `samples_out (1 Sep, HySpex radiance)` |
| `952.0` … `2517.0` | Reflectance at each of the 288 bands (nm). Models use 1000–2450 nm, 266 bands |

### Dishes behind each model (33 each)

| Model | Filter |
|---|---|
| Robusta + chicory | `species` in {robusta, robusta_chicory}, `role == calibration`, chicory 0–50 % (both robusta files) |
| Arabica + chicory | Same with {arabica, arabica_chicory} on `arabica_chicory_all_sessions.csv` |
| Arabica + robusta + chicory | `role == calibration` in the AR file, minus the 13:30 `AR[50:50]` dishes (`day == 2`); chicory % is the label's second number (an assumption still to be confirmed from the lab notes) |

## Sessions

| Base | Session 1 | Session 2 | Session 3 |
|---|---|---|---|
| Robusta | 1 Sep, 0 % | 4 Sep, 10–50 % | 8 Sep, 5–45 % |
| Arabica | 1 Sep, 0 % | 4 Sep, 10–50 % | 8 Sep, 5–45 % |
| Arabica + robusta | 4 Sep 12:00, 30–50 % | 4 Sep 13:30, 0–20 % | 7 Sep, 5–45 % |

## Raw scans (not in git)

HySpex SWIR-384, 384 px swath, 9000 µs integration, Labsphere SRT-MS-050 reference strip in every
scan (certificate: `SRT-MS-050__1_.txt`). Robusta files are radiance (`*_raw_rad_float32.img` +
`.hdr`); arabica and AR files are raw counts (`*_raw.hyspex` + `.hdr`) whose dark background is
stored in the binary header. Expected layout:

```
$COFFEE_RAW/arabica/              raw arabica scans
$COFFEE_RAW/arabica+robusta/      raw AR scans
<repository>/*.img, *.hdr         robusta sessions 1–2 radiance
<repository>/batch3_rad/          robusta session 3 radiance
```
