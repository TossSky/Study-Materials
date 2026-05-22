import io
import os

import torch
import torch.nn as nn
from PIL import Image
from torchvision.models import resnet18, ResNet18_Weights

WEIGHTS = os.environ.get("WEIGHTS", "weights.pt")
_DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
_LABEL_RU = {"humans": "Человек", "animals": "Животное"}

_model = None
_classes = ["animals", "humans"]
_tfm = ResNet18_Weights.IMAGENET1K_V1.transforms()


def _build_model() -> nn.Module:
    m = resnet18(weights=None)
    m.fc = nn.Linear(m.fc.in_features, 2)
    return m


def _ensure_loaded() -> None:
    global _model, _classes
    if _model is not None:
        return
    ckpt = torch.load(WEIGHTS, map_location=_DEVICE, weights_only=False)
    _classes = ckpt.get("classes", _classes)
    m = _build_model().to(_DEVICE)
    m.load_state_dict(ckpt["state_dict"])
    m.eval()
    _model = m


def predict_image(image_bytes: bytes) -> str:
    _ensure_loaded()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    x = _tfm(img).unsqueeze(0).to(_DEVICE)
    with torch.no_grad():
        probs = torch.softmax(_model(x), dim=1)[0]
        idx = int(probs.argmax())
    return _LABEL_RU.get(_classes[idx], _classes[idx])
