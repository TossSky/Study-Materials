"""Собирает датасет для бинарной классификации humans vs animals.

Источники:
  - humans: HuggingFace `logasja/LFW` (зеркало Labeled Faces in the Wild)
  - animals: torchvision CIFAR-10, классы bird/cat/deer/dog/frog/horse

Итоговая структура (ImageFolder):
  data/train/humans/*.jpg
  data/train/animals/*.jpg
  data/val/humans/*.jpg
  data/val/animals/*.jpg
"""
import argparse
import random
from pathlib import Path

from PIL import Image
from datasets import load_dataset
from torchvision.datasets import CIFAR10

ANIMAL_CLASSES = {"bird", "cat", "deer", "dog", "frog", "horse"}


def save_pil(img: Image.Image, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(path, "JPEG", quality=90)


def collect_humans(raw_dir: Path, n: int, seed: int = 0):
    ds = load_dataset("logasja/LFW", "default", split="train",
                      cache_dir=str(raw_dir))
    idx = list(range(len(ds)))
    random.Random(seed).shuffle(idx)
    for i in idx[:n]:
        yield ds[i]["image"]


def collect_animals(raw_dir: Path, n: int, seed: int = 0):
    ds = CIFAR10(root=str(raw_dir), train=True, download=True)
    animal_ids = {ds.class_to_idx[c] for c in ANIMAL_CLASSES}
    idx = [i for i, lab in enumerate(ds.targets) if lab in animal_ids]
    random.Random(seed).shuffle(idx)
    for i in idx[:n]:
        img, _ = ds[i]
        yield img


def dump(images, out_dir: Path, prefix: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, img in enumerate(images):
        save_pil(img, out_dir / f"{prefix}_{i:05d}.jpg")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="data")
    p.add_argument("--raw", default=".cache")
    p.add_argument("--train-per-class", type=int, default=200)
    p.add_argument("--val-per-class", type=int, default=60)
    args = p.parse_args()

    out = Path(args.out)
    raw = Path(args.raw)
    total = args.train_per_class + args.val_per_class

    humans = list(collect_humans(raw, total))
    animals = list(collect_animals(raw, total))

    dump(humans[:args.train_per_class], out / "train" / "humans", "h")
    dump(humans[args.train_per_class:], out / "val" / "humans", "h")
    dump(animals[:args.train_per_class], out / "train" / "animals", "a")
    dump(animals[args.train_per_class:], out / "val" / "animals", "a")

    print(f"готово: {out.resolve()}")
    for split in ("train", "val"):
        for cls in ("humans", "animals"):
            n = len(list((out / split / cls).glob("*.jpg")))
            print(f"  {split}/{cls}: {n}")


if __name__ == "__main__":
    main()
