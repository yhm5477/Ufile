# app/config.py
from pathlib import Path

# 물리적 디렉터리 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
LOG_DIR = BASE_DIR / "logs"

# 3단계 정책 판단 기준 임계값 (Threshold)
HIGH_THRESHOLD = 0.75
MID_THRESHOLD = 0.55

# 시스템 예약 특수 폴더명
REVIEW_LABEL = "review"
UNKNOWN_LABEL = "unknown"

# 허용 이미지 확장자 매트릭스
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".jfif"}