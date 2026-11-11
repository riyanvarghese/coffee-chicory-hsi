# Chicory in coffee by SWIR hyperspectral imaging

Non-destructive quantification of chicory in ground coffee with a HySpex SWIR-384 camera
(288 bands, 1000–2450 nm used). B.Tech project, Department of Electrical Engineering, NIT Calicut,
in collaboration with NTNU and the Coffee Board of India. Guide: Dr. Shihabudheen K V.

**Private repository.** Access is managed by the repository owner. Do not copy data, notebooks or
results outside the team without asking.

## Results

Error is the mean RMSE per dish (% chicory) over three held-out scanning sessions
(nested leave-one-session-out: no session ever helps train the model that predicts it).

| Coffee base | Final model | S1 | S2 | S3 | Mean |
|---|---|---|---|---|---|
| Robusta + chicory | PLSR on absorbance + offset, 6 LV | 0.61 | 0.64 | 1.11 | **0.79** |
| Arabica + chicory | EMSC + PLSR, 4 LV | 0.38 | 1.28 | 0.68 | **0.78** |
| Arabica + robusta + chicory | SG1 on 1650–1800 + 2150–2400 nm, PLSR, 5 LV | 1.04 | 0.90 | 0.88 | **0.94** |

A PCA-LDA classifier names the coffee base first (balanced accuracy 0.95 on unseen days).
A final check of 14 preprocessings × 5 linear models per base (210 combinations,
`final_model_check/`) found nothing significantly better. Random forest, gradient boosting and
RBF-SVR were 4–11 times worse in every base.

The full story, decisions and open questions are in [`docs/project_record.html`](docs/project_record.html)
(download and open it in a browser).

## Repository layout

The layout mirrors the original project folder, because the notebooks find each other and their
data by these relative paths.

| Path | What it is |
|---|---|
| `radiance_to_reflectance.ipynb`, `reflectance_training_samples*.ipynb`, `swir_inspect.ipynb` | Robusta scans → reflectance → 12 × 12 px patch spectra |
| `arabica_reflectance_samples.ipynb` | Arabica raw counts (dark signal from the file header) → patches |
| `arabica_robusta_reflectance_samples.ipynb` | Arabica + robusta (AR) scans → patches |
| `samples_out/`, `batch3_out/`, `arabica_out/`, `arabica_robusta_out/` | **Extracted spectra**, one CSV row per patch (see [`DATA.md`](DATA.md)) |
| `robusta_chicory_nested_loso.ipynb` → `final_regression/` | Final robusta model (midsem result) |
| `robusta_chicory_regression.ipynb`, `session_wise_models.ipynb`, `complete_results.ipynb`, `validation_and_recalibration.ipynb`, `final_model_and_maps.ipynb`, `result_images.ipynb`, `advanced_models_nested_loso.ipynb` | Earlier robusta stages, checks and figures (`model_out/`, `rb_ch_model/`, `final_model/`, `final_results/`, `session_results/`, `advanced_models/`, `figures/`) |
| `arabica_chicory_nested_loso.ipynb` → `arabica_regression/` | Arabica model search |
| `arabica_advanced_models_nested_loso.ipynb` → `arabica_advanced_models/` | EMSC + PLSR found here |
| `arabica_preprocessing_check.ipynb` → `arabica_preprocessing/` | 9 preprocessings × 5 models on arabica |
| `new_methods_nested_loso_{robusta,arabica}.ipynb` → `new_methods_*/` | Literature methods (SO-PLS, EPO, VIP, joint model) |
| `arabica_robusta_models_and_classifier.ipynb` → `arabica_robusta_models/` | AR series read as arabica vs robusta (did not work) |
| `arabica_robusta_models_excl_1330_5050/run.py` | Three-way model search without the 13:30 AR 50:50 set |
| `arc_chicory_models.ipynb` → `arc_chicory_models/` | AR series read as coffee base + chicory |
| `three_mixture_classifier.ipynb` → `three_mixture_classifier/` | Coffee-base classifier |
| `final_model_check/` | `run.py RBCH\|ABCH\|ARC` and `compare.py`: the 210-combination check |
| `coffee_app/` | Browser app: `train_app_models.py` → `models.json`/`models.js`, `core.js` engine, `index.html` (built by `build_site.py`) |
| `presentations/` | Midsem deck and end-semester drafts |
| `endsem_ppt/` | Figures and build scripts for the end-semester deck |
| `project_code/` | Organised archive of the robusta (midsem) stage, with figure and slide scripts. The live copies of these notebooks are at the top level. |
| `docs/project_record.html` | Project record for the team |

## Setup

```bash
git clone https://github.com/riyanvarghese/coffee-chicory-hsi.git
cd coffee-chicory-hsi
python -m venv .venv && source .venv/bin/activate      # Python 3.12 or newer
pip install -r requirements.txt
jupyter lab
```

### Two settings

All paths go through two environment variables. You only need them if the defaults do not suit you.

| Variable | Meaning | Default |
|---|---|---|
| `COFFEE_DATA` | The project folder | This repository (found from the notebook's or script's location) |
| `COFFEE_RAW` | Folder holding the raw `arabica/` and `arabica+robusta/` scans | The original external drive path |

Robusta raw scans (`*.img`, `batch3_rad/`) belonged inside the project folder: place them in the
repository root and in `batch3_rad/`. Git ignores them.

### Google Colab

```python
from google.colab import drive; drive.mount("/content/drive")
!git clone https://github.com/riyanvarghese/coffee-chicory-hsi.git /content/drive/MyDrive/coffee-chicory-hsi
%env COFFEE_DATA=/content/drive/MyDrive/coffee-chicory-hsi
%cd /content/drive/MyDrive/coffee-chicory-hsi
```

Cloning a private repository in Colab needs a GitHub personal access token in the URL or a
credential helper.

## What is not in the repository

Raw camera files (`.img`, `.hyspex`, raw `.hdr`, about 7 GB on the project drive plus the arabica
and AR scans). Everything downstream of them is here: the extracted patch spectra, every model
result and every figure. Ask the owner for raw scans if you need to re-extract spectra or test the app.

## Working together

- Work on a branch and open a pull request into `main`; describe what changed and why.
- Never commit raw scans or other files over 50 MB. `.gitignore` already blocks the raw formats.
- Notebooks with heavy outputs make large diffs. Clear outputs you do not need before committing.
- Use issues for tasks and questions so the team can see who is doing what.

## Re-running the main results

```bash
# final model check, about 15 minutes per base (run the three in parallel)
cd final_model_check
for F in RBCH ABCH ARC; do python -u run.py $F > ${F}_log.txt 2>&1 & done; wait
python compare.py

# app models after retraining
cd ../coffee_app && python train_app_models.py
```
