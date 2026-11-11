"""Arabica + robusta model search WITHOUT the 13:30 'AR 50-50' dishes (session 2, the one dish type that looked chicory-free).
Runs the setup and model-search cells of arabica_robusta_models_and_classifier.ipynb unchanged, with that one exclusion."""
import os
import json
from pathlib import Path
os.environ.setdefault("COFFEE_DATA", str(Path(__file__).resolve().parents[1]))
HERE = Path(__file__).parent
nb = json.loads((HERE.parent / "arabica_robusta_models_and_classifier.ipynb").read_text())
cell = lambda i: "".join(nb["cells"][i]["source"])
setup = cell(2).replace('DATA = AR[AR.role == "calibration"].reset_index(drop=True)',
                        'DATA = AR[(AR.role == "calibration") & ~((AR.day == 2) & (AR.label == "AR[50:50]"))].reset_index(drop=True)')
assert setup != cell(2)
import matplotlib; matplotlib.use("Agg")
g = {}
exec(setup.replace('OUT = BASE / "arabica_robusta_models"', f'OUT = Path(r"{HERE}")'), g)
assert str(g["OUT"]) == str(HERE)
exec(cell(6), g)          # nested leave-one-session-out, 11 models
exec(cell(7), g)          # figure -> 01_model_search.png
