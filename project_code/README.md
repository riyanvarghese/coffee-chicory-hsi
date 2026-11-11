# Chicory in robusta coffee: SWIR hyperspectral imaging, all code to date

Every notebook and script used in the project, from the raw HySpex scans to the final model and the slides,
collected on 4 October 2026. The files here are **copies**; the originals are still in `coffee data/`
(one notebook came from the home folder). Folders are numbered in the order the work runs.

## Run order

```
raw scans (*.hdr / *.img)
   │  01  reflectance_training_samples.ipynb  (sessions 1–2)   → samples_out/
   │      reflectance_training_samples_batch3.ipynb (session 3) → batch3_out/
   ▼
patch spectra (training_samples.csv)
   │  03  robusta_chicory_nested_loso.ipynb                     → final_regression/   ← final results
   │      result_images.ipynb                                   → final_regression/images/
   ▼
04 checks  →  05 slide figures  →  06 deck builders
```

The `02_early_models` notebooks are the earlier analysis (mid-semester deck). They are kept for the record;
the final model and every reported number come from `03_final_model`.

## Contents

### 01_reflectance_and_patches: from raw radiance to patch spectra
| File | Date | What it does | Writes |
|---|---|---|---|
| `radiance_to_reflectance.ipynb` | 16 Sep | First pass: finds the white strip and the dishes automatically, converts radiance to reflectance, one mean spectrum per dish (sessions 1–2). | `reflectance_out/` |
| `reflectance_training_samples.ipynb` | 16 Sep | **Used for the data.** Strip and dishes drawn by hand (OpenCV window), per-column white reference, dish masks (rim, shadow, glare, 4 px edge removed), 12 × 12 px patches. Sessions 1–2. Original file name: `reflectance_training_samples (1).ipynb`. | `samples_out/` (`training_samples.csv`, `rois.json`, mask images) |
| `reflectance_training_samples_draft.ipynb` | 16 Sep | Earlier draft of the notebook above (no stir/capture column). Not used for the final data. | — |
| `reflectance_training_samples_batch3.ipynb` | 18 Sep | Same pipeline for session 3 (8 Sep scans). | `batch3_out/` |
| `swir_inspect.ipynb` | 17 Sep | Inspection of the cubes and spectra before modelling. | `inspect_out/` |

### 02_early_models: the analysis behind the mid-semester deck
| File | Date | What it does | Writes |
|---|---|---|---|
| `chicory_regression.ipynb` | 17 Sep | First regression attempt (was `~/chicory_regression.ipynb`). | `model_out/` |
| `robusta_chicory_regression.ipynb` | 17 Sep | PLSR with patch trimming and super-patches, leave-one-concentration-out, permutation test, applicability domain (sessions 1–2). | `rb_ch_model/` |
| `validation_and_recalibration.ipynb` | 19 Sep | External test on session 3 (5-LV model, 1.16 % RMSEP) and recalibration on all sessions. | `final_results/` |
| `final_model_and_maps.ipynb` | 19 Sep | Saved 6-LV model and chicory / homogeneity maps. | `final_model/` |
| `complete_results.ipynb` | 19 Sep | All figures and tables of the first deck: preprocessing comparison, latent variables, 9 methods, permutation test, literature. | `figures/`, `results.json` |

### 03_final_model: the reported results
| File | Date | What it does | Writes |
|---|---|---|---|
| `session_wise_models.ipynb` | 2 Oct | One model per session vs leave-one-session-out; predictions for the unknowns A, B, C. | `session_results/` |
| `robusta_chicory_nested_loso.ipynb` | 2 Oct | **Final.** Nested leave-one-session-out for 8 methods (settings tuned inside each round), PLSR selected, final 6-LV model refitted on all sessions, figures 01–05 (05 = training vs validation curve). Mean error 0.79 ± 0.28 % on unseen sessions. | `final_regression/` (incl. `robusta_chicory_model.pkl`, `summary.json`) |
| `result_images.ipynb` | 2 Oct | Slide-ready result images, one figure per file. | `final_regression/images/` |

### 04_checks
| File | What it does |
|---|---|
| `preprocessing_check_nested_loso.py` | Puts all 8 preprocessing options through the final model's nested leave-one-session-out, with a paired bootstrap against absorbance + offset. Read-only on the project data. |
| `prep_folds.csv` | Its output: error per option and held-out session. Absorbance + offset 0.79 %, absorbance + SG1 0.75 % (statistical tie), raw 1.86 %. |

### 05_presentation_figures
| File | Makes |
|---|---|
| `deck_result_figures.py` | Latent-variable curve, method comparison, performance on unseen sessions, error per blend. |
| `mask_figure_labelled.py` | Detailed dish mask, every masked pixel class coloured (v2 deck). |
| `mask_figure_simple.py` | Mask vs petri dish, used on the "Data acquisition" slide. |
| `preprocessing_figures.py` | "Why the spectra need correcting" demonstration and the 8-option preprocessing chart (needs `../04_checks/prep_folds.csv`). |
| `spectra_bands_figure.py` | Spectra with bold band labels for "Why hyperspectral imaging?". |
| `pipeline_block_diagram.py` | The two-row pipeline block diagram (`final_regression/images/09_pipeline_block_diagram.png`). |
| `pipeline_flowchart.html` | The detailed pipeline flow chart page (open in a browser). |

Each script runs as `python <script> <output path>`; the header of every file says what it reads.

### 06_slide_building
| File | What it does |
|---|---|
| `build_deck_v2.py` | Builds `Additives_in_Coffee_HSI_v2.pptx` from the original deck by editing the slide XML. Also holds the shape/notes/table helpers. |
| `build_deck_v4_to_draft2.py` | Builds v4 → v8 and `midsem_coffee_draft2.pptx` from the team's v3 deck; each round of slide changes was added on top of the last. |

These expect the deck unpacked next to them (see each file's header) and the figures from folder 05. They are a
record of exactly how the slides were made; editing the decks in PowerPoint is simpler for further changes.

## Environment

Python 3.14 with the packages in `requirements.txt` (the project used the `~/Fabric_Project/.venv`
environment, Jupyter kernel "Fabric HSI"). The ROI drawing in the 01 notebooks needs `opencv-python`, not the
headless build.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter notebook            # or open the notebooks in VS Code
```

## Before running on another computer

- The notebooks use absolute paths to the project folder, e.g.
  `BASE = Path("/run/media/riyanvarghese/RIYAN HDD/coffee data")`, or relative output folders such as
  `./samples_out`. Change `BASE` (and run from the project folder) if the data lives elsewhere.
- The raw cubes (`*_raw_rad_float32.img`, about 0.8 GB each), the Spectralon certificate `SRT-MS-050__1_.txt`
  and the output folders listed above are **not** copied here; they stay in `coffee data/`.
- Re-running the final notebook reproduces `final_regression/summary.json` exactly; only the Random Forest
  numbers can differ in the 15th decimal place (parallel arithmetic).
