# test/test_scanner.py
import os
os.environ["TRANSFORMERS_NO_TF"] = "1"  # TF 경고/로딩 억제(가능하면)

from pathlib import Path
from transformers import pipeline

_zs = pipeline(
    task="zero-shot-image-classification",
    model="openai/clip-vit-base-patch32",
)

CANDIDATES = ["cat", "dog", "bird", "wild animal", "other"]

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".jfif"}


def scan(image_path: str):
    """이미지 파일 1장 경로 -> (label, confidence)"""
    out = _zs(image_path, candidate_labels=CANDIDATES)

    # ✅ out이 list 형태로 오는 환경 대응
    # 예: [{'label': 'dog', 'score': 0.82}, {'label': 'cat', 'score': 0.12}, ...]
    top = out[0]
    label = top["label"]
    confidence = float(top["score"])
    return label, confidence


def scan_folder(input_dir: str):
    """폴더 경로 -> 이미지 파일 Path 리스트"""
    p = Path(input_dir)
    if not p.exists():
        raise FileNotFoundError(f"INPUT_DIR not found: {input_dir}")

    files = []
    for f in p.iterdir():
        if f.is_file() and f.suffix.lower() in IMAGE_EXTS:
            files.append(f)

    return sorted(files)
