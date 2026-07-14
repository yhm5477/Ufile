# test/test_service.py
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import logging
from app.scanner import Scanner

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".jfif"}


logger = logging.getLogger(__name__)
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".jfif"}

@dataclass
class ItemResult: #포멧선언
    index: int
    total: int
    filename: str
    src_path: str
    raw_label: Optional[str] = None
    score: float = 0.0
    final_label: Optional[str] = None
    decision_reason: Optional[str] = None
    saved_name: Optional[str] = None
    status: str = "fail"
    error: Optional[str] = None

class ClassificationService:
    def __init__(self, scanner_module, saver_module,
                 high_threshold: float = 0.75, mid_threshold: float = 0.55,
                 review_label: str = "review", unknown_label: str = "unknown"):
        self.scanner = scanner_module
        self.saver = saver_module
        self.high = float(high_threshold)
        self.mid = float(mid_threshold)
        self.review_label = review_label
        self.unknown_label = unknown_label

    def run_folder(self, input_dir: str, output_dir: str, dry_run: bool = False) -> List[ItemResult]:
        files = self._collect_images(input_dir)
        total = len(files)

        results: List[ItemResult] = []
        for i, img in enumerate(files, start=1):
            res = ItemResult(index=i, total=total, filename=img.name, src_path=str(img))
            step = "init"
            try:
                step = "scan"
                raw_label, score = self.scanner.scan(str(img))
                res.raw_label = raw_label
                res.score = float(score)

                step = "decide"
                final_label, reason = self._decide_label(raw_label, res.score)
                res.final_label = final_label
                res.decision_reason = reason

                step = "save"
                saved_name = self.saver.test_saver(
                    src_path=str(img),
                    output_dir=output_dir,
                    label=final_label,
                    confidence=res.score,
                    dry_run=dry_run
                )
                res.saved_name = saved_name
                res.status = "success"

            except Exception as e:
                res.status = "fail"
                res.error = f"[{step}] {type(e).__name__}: {e}"
                logger.error(f"Fail at step={step} | file={img} | error={e}", exc_info=True)

            results.append(res)
        return results

    def _collect_images(self, input_dir: str) -> List[Path]:
        p = Path(input_dir)
        if not p.exists():
            raise FileNotFoundError(f"INPUT_DIR not found: {input_dir}")
        if not p.is_dir():
            raise NotADirectoryError(f"INPUT_DIR is not a directory: {input_dir}")
        files = [f for f in p.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTS]
        return sorted(files)

    def _decide_label(self, raw_label: str, score: float) -> Tuple[str, str]:
        if score >= self.high:
            return raw_label, "high_conf_ok"
        if score >= self.mid:
            return self.review_label, "mid_conf_to_review"
        return self.unknown_label, "low_conf_to_unknown"

    def run_folder(self, input_dir: str, output_dir: str, dry_run: bool = False) -> List[ItemResult]:
        files = self._collect_images(input_dir)
        total = len(files)

        results: List[ItemResult] = []
        for i, img in enumerate(files, start=1):
            res = ItemResult(index=i, total=total, filename=img.name, src_path=str(img))
            step = "init"

            try:
                # 1) AI 분류
                step = "scan"
                raw_label, score = self.scanner.scan(str(img))
                res.raw_label = raw_label
                res.score = float(score)

                # 2) 정책 결정
                step = "decide"
                final_label, reason = self._decide_label(raw_label, res.score)
                res.final_label = final_label
                res.decision_reason = reason

            # 3) 저장
                step = "save"
                saved_name = self.saver.save_classified(
                    src_path=str(img),
                    output_dir=output_dir,
                    label=final_label,
                    confidence=res.score,
                    dry_run=dry_run
                )

                res.saved_name = saved_name
                res.status = "success"

            except Exception as e:
                res.status = "fail"
                res.error = f"[{step}] {type(e).__name__}: {e}"

                logger.error(
                    f"Fail at step={step} | file={img} | error={e}",
                    exc_info=True
                )

            results.append(res)

        return results

    def _collect_images(self, input_dir: str) -> List[Path]:
        p = Path(input_dir)
        if not p.exists():
            raise FileNotFoundError(f"INPUT_DIR not found: {input_dir}")
        if not p.is_dir():
            raise NotADirectoryError(f"INPUT_DIR is not a directory: {input_dir}")

        files = [
            f for f in p.iterdir()
            if f.is_file() and f.suffix.lower() in IMAGE_EXTS
        ]
        return sorted(files)

    def _decide_label(self, raw_label: str, score: float) -> Tuple[str, str]:
        """
        분기 정책:
        - score >= high : raw_label 그대로 저장(자동 분류)
        - mid <= score < high : review 폴더로 보냄
        - score < mid : unknown 폴더로 보냄

        ※ 지금은 CLIP 후보 라벨을 raw_label로 받고 있으니,
          high 구간에서는 raw_label(cat/dog/wild animal...)을 그대로 final로 써도 안전함.
        """
        if score >= self.high:
            return raw_label, "high_conf_ok"
        if score >= self.mid:
            return self.review_label, "mid_conf_to_review"
        return self.unknown_label, "low_conf_to_unknown"
