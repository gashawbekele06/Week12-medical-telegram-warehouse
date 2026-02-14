
"""
YOLOv8 Object Detection Enrichment – Task 3
FINAL WORKING VERSION – PyTorch 2.6+ safe deserialization compatible
"""

import csv
import logging
from pathlib import Path
import importlib

# ────────────────────────────────────────────────────────────────────────────────
# PYTORCH 2.6+ SAFE DESERIALIZATION
# We add all likely Ultralytics classes *and* wrap the actual torch.load call
# (triggered inside YOLO(...)) with torch.serialization.safe_globals([...]).
# ────────────────────────────────────────────────────────────────────────────────
import torch

_HAS_ADD_SAFE_GLOBALS = hasattr(torch.serialization, "add_safe_globals")
_HAS_SAFE_GLOBALS_CTX = hasattr(torch.serialization, "safe_globals")

def _resolve_classes(fqns):
    """Return a list of class objects for fully-qualified names present in env."""
    out = []
    for fqn in fqns:
        try:
            mod_name, cls_name = fqn.rsplit(".", 1)
            mod = importlib.import_module(mod_name)
            cls = getattr(mod, cls_name)
            out.append(cls)
        except Exception:
            # Not present in this ultralytics build — ignore
            pass
    return out

# Ultralytics classes that appear inside YOLOv8 checkpoints across versions
ULTRA_FQNS = [
    # Task wrapper
    "ultralytics.nn.tasks.DetectionModel",

    # Backbone/neck blocks (different packages across releases)
    "ultralytics.nn.modules.Conv",
    "ultralytics.nn.modules.Bottleneck",
    "ultralytics.nn.modules.C3",
    "ultralytics.nn.modules.RepC3",
    "ultralytics.nn.modules.C3Ghost",
    "ultralytics.nn.modules.C2f",
    "ultralytics.nn.modules.SPPF",
    # Alternate module paths found in other builds
    "ultralytics.nn.modules.conv.Conv",
    "ultralytics.nn.modules.block.C2f",
    "ultralytics.nn.modules.pooling.SPPF",

    # Head & loss
    "ultralytics.nn.modules.head.Detect",
    "ultralytics.nn.modules.loss.DFL",
]

# Always include common torch.nn classes that show up in graphs
from torch.nn import (
    Identity, ModuleList, ModuleDict, Linear, Conv2d, BatchNorm2d, SiLU, Sigmoid
)
from torch.nn.modules.container import Sequential
from torch.nn.modules.pooling import MaxPool2d

COMMON_TORCH_CLASSES = [
    Identity, ModuleList, ModuleDict, Linear, Conv2d, BatchNorm2d,
    SiLU, Sigmoid, Sequential, MaxPool2d
]

# We resolve Ultralytics classes now, but the key is to apply them *during* load.
ULTRA_CLASSES = _resolve_classes(ULTRA_FQNS)

# Optionally register them globally (helps other later loads)
if _HAS_ADD_SAFE_GLOBALS and ULTRA_CLASSES:
    try:
        torch.serialization.add_safe_globals(ULTRA_CLASSES + COMMON_TORCH_CLASSES)
    except Exception:
        pass

# ─── NORMAL IMPORTS ─────────────────────────────────────────────────────────────
from ultralytics import YOLO
from tqdm import tqdm

# ─── CONFIG ─────────────────────────────────────────────────────────────────────
IMAGES_ROOT = Path("data/raw/images")
OUTPUT_CSV = Path("data/yolo_detections.csv")
CONFIDENCE_THRESHOLD = 0.25

# ─── LOGGING ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# ─── CLASSIFICATION LOGIC ───────────────────────────────────────────────────────
def classify_image(boxes, names) -> str:
    has_person = False
    has_product = False

    product_keywords = {
        "bottle", "cup", "bowl", "cell phone", "book", "vase", "scissors",
        "teddy bear", "hair drier", "toothbrush", "remote", "keyboard", "mouse",
        "laptop", "tv", "microwave", "oven", "toaster", "sink", "refrigerator"
    }

    if boxes is None or boxes.cls is None:
        return "other"

    for i in range(len(boxes)):
        conf = float(boxes.conf[i].item())
        if conf < CONFIDENCE_THRESHOLD:
            continue
        cls_id = int(boxes.cls[i].item())
        cls_name = names.get(cls_id, str(cls_id))

        if cls_name == "person":
            has_person = True
        elif cls_name in product_keywords:
            has_product = True

    if has_person and has_product:
        return "promotional"
    elif has_product:
        return "product_display"
    elif has_person:
        return "lifestyle"
    else:
        return "other"

# ─── MAIN ───────────────────────────────────────────────────────────────────────
def main():
    IMAGES_ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Loading YOLOv8 nano model (yolov8n.pt)...")

    # >>> CRUCIAL PART: ensure the allowlist is active *during* torch.load <<<
    if _HAS_SAFE_GLOBALS_CTX:
        from contextlib import ExitStack
        with ExitStack() as stack:
            # Add both Ultralytics and common torch classes into the safe context
            allowed = ULTRA_CLASSES + COMMON_TORCH_CLASSES
            if allowed:
                stack.enter_context(torch.serialization.safe_globals(allowed))
            model = YOLO("yolov8n.pt")  # torch.load happens inside this call
    else:
        # Older PyTorch (no safe_globals ctx): just load normally
        model = YOLO("yolov8n.pt")

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "image_path", "message_id", "channel",
            "detected_objects", "confidence_scores", "image_category"
        ])

        image_files = []
        for ext in ("*.jpg", "*.jpeg", "*.JPG", "*.JPEG", "*.png", "*.PNG"):
            image_files.extend(IMAGES_ROOT.rglob(ext))

        logger.info(f"Found {len(image_files)} images")

        for img_path in tqdm(image_files, desc="Detecting"):
            try:
                channel = img_path.parent.name
                message_id = img_path.stem

                results = model(img_path, verbose=False)[0]
                boxes = results.boxes
                names = results.names  # dict: class_id -> class_name

                detected, confidences = [], []
                if boxes is not None and boxes.cls is not None:
                    for i in range(len(boxes)):
                        cls_id = int(boxes.cls[i].item())
                        conf = float(boxes.conf[i].item())
                        if conf >= CONFIDENCE_THRESHOLD:
                            detected.append(names.get(cls_id, str(cls_id)))
                            confidences.append(f"{conf:.3f}")

                category = classify_image(boxes, names)

                writer.writerow([
                    str(img_path.relative_to(Path("data/raw"))),
                    message_id,
                    channel,
                    ";".join(detected) if detected else "",
                    ";".join(confidences) if confidences else "",
                    category
                ])

            except Exception as e:
                logger.error(f"Failed on {img_path}: {e}")

    logger.info(f"Results saved to {OUTPUT_CSV}")
    logger.info(f"Processed {len(image_files)} images")

if __name__ == "__main__":
    main()
