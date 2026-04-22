import argparse

import torch
from PIL import Image

from model import build_model
from train import make_transforms


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--weights", default="weights.pt")
    p.add_argument("--image", required=True)
    args = p.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(args.weights, map_location=device, weights_only=False)
    classes = ckpt.get("classes", ["animals", "humans"])

    model = build_model(pretrained=False).to(device)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()

    tfm = make_transforms(train=False)
    img = Image.open(args.image).convert("RGB")
    x = tfm(img).unsqueeze(0).to(device)

    with torch.no_grad():
        logits = model(x)
        probs = torch.softmax(logits, dim=1)[0]
        idx = int(probs.argmax())

    label = classes[idx]
    print(f"{args.image} -> {label} (p={probs[idx].item():.3f})")
    for c, pr in zip(classes, probs.tolist()):
        print(f"  {c}: {pr:.3f}")


if __name__ == "__main__":
    main()
