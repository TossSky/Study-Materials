import torch.nn as nn
from torchvision.models import resnet18, ResNet18_Weights

NUM_CLASSES = 2
CLASSES = ["animals", "humans"]


def build_model(pretrained: bool = True) -> nn.Module:
    weights = ResNet18_Weights.IMAGENET1K_V1 if pretrained else None
    model = resnet18(weights=weights)
    model.fc = nn.Linear(model.fc.in_features, NUM_CLASSES)
    return model


def preprocess():
    return ResNet18_Weights.IMAGENET1K_V1.transforms()
