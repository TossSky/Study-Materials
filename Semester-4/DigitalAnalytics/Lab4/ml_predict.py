from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Tuple

import torch
from PIL import Image

_LAB3 = (Path(__file__).resolve().parent.parent / "Lab3").as_posix()
if _LAB3 not in sys.path:
    sys.path.insert(0, _LAB3)

from model import build_model  # noqa: E402
from train import make_transforms  # noqa: E402

WEIGHTS = os.environ.get("WEIGHTS", str(Path(_LAB3) / "weights.pt"))

_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
_model = None
_classes = ["animals", "humans"]
_tfm = make_transforms(train=False)


def _ensure_loaded() -> None:
    global _model, _classes
    if _model is not None:
        return
    ckpt = torch.load(WEIGHTS, map_location=_device, weights_only=False)
    _classes = ckpt.get("classes", _classes)
    _model = build_model(pretrained=False).to(_device)
    _model.load_state_dict(ckpt["state_dict"])
    _model.eval()


def predict_image(path: str) -> Tuple[str, float]:
    _ensure_loaded()
    img = Image.open(path).convert("RGB")
    x = _tfm(img).unsqueeze(0).to(_device)
    with torch.no_grad():
        probs = torch.softmax(_model(x), dim=1)[0]
        idx = int(probs.argmax())
    return _classes[idx], float(probs[idx])
