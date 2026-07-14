import os
os.environ["TRANSFORMERS_NO_TF"] = "1"
from transformers import pipeline

# 로컬 메모리에 CLIP 모델 파이프라인 싱글톤 적재[cite: 5, 7]
_classifier = pipeline(
    task="zero-shot-image-classification",
    model="openai/clip-vit-base-patch32"
)

def scan_image(image_path: str, candidates: list[str]) -> tuple[str, float]:
    """
    [기능 #1] 이미지 1장 경로와 후보 자연어 클래스를 받아 Top-1 결과를 반환합니다.[cite: 5, 7]
    """
    out = _classifier(image_path, candidate_labels=candidates)
    top = out[0]
    return top["label"], float(top["score"])