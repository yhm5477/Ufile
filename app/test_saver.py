# test/test_saver.py
from pathlib import Path
from datetime import datetime
import shutil
import csv

LOG_PATH = Path("logs/results.csv")


def _ensure_log_file():
    if not LOG_PATH.exists():
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "original_name",
                "new_name",
                "label",
                "confidence",
                "status",
                "mode"
            ])


def _write_log(row: list):
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)


def _sanitize_filename(name: str) -> str:
    """
    Windows에서 파일명/폴더명에 못 쓰는 문자 제거
    + 너무 긴 이름 방지
    """
    bad = '<>:"/\\|?*'
    for ch in bad:
        name = name.replace(ch, "_")
    name = name.replace("\n", " ").replace("\r", " ").strip()

    # 길이 너무 길면 잘라내기(폴더/파일명 폭주 방지)
    return name[:80]


def test_saver(
    src_path: str,
    output_dir: str,
    label: str,
    confidence: float,
    dry_run: bool = False
):
    """
    src_path: 원본 이미지 경로
    output_dir: output 기본 폴더 (예: "output")
    label: 분류 결과 라벨 (예: "cat")
    confidence: 점수 (0~1)
    dry_run: True면 파일 복사 안 하고 로그만 남김
    """
    _ensure_log_file()

    src = Path(src_path)
    safe_label = _sanitize_filename(label)

    dst_dir = Path(output_dir) / safe_label
    dst_dir.mkdir(parents=True, exist_ok=True)

    score_pct = int(confidence * 100)
    new_name = f"{safe_label}_{score_pct}_{src.name}" #이름 규칙
    new_name = _sanitize_filename(new_name)

    dst = dst_dir / new_name

    status = "success"
    mode = "dry-run" if dry_run else "normal"

    try:
        shutil.copy2(src, dst)
    except Exception as e:
        _write_log(...)
        raise   # ← 이게 핵심

    _write_log([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        src.name,
        new_name,
        safe_label,
        round(confidence, 4),
        status,
        mode
    ])

    return new_name