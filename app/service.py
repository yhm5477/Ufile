# app/service.py
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import logging

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".jfif"}
logger = logging.getLogger(__name__)

@dataclass
class ItemResult: 
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

    def run_folder(self, input_dir: str, output_dir: str, task_id: str = None, db = None, dry_run: bool = False) -> List[ItemResult]:
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

                # 3) 파일 시스템 물리 이동 저장[cite: 6]
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

                # [★ 공백 3 해결] 데이터 분석 완료 시 SQLite DB file_history 테이블에 실시간 로그 적재
                if db and task_id:
                    from .models import FileHistory
                    
                    # 3단계 정책에 따른 최종 상태값 매핑
                    if final_label == self.review_label:
                        f_status = "review"
                    elif final_label == self.unknown_label:
                        f_status = "unknown"
                    else:
                        f_status = "success"


                    web_accessible_path = f"/output/{final_label}/{saved_name}"
                    
                    new_history = FileHistory(
                        task_id=task_id,
                        file_original_name=img.name,
                        file_new_name=saved_name,
                        file_label=final_label,
                        file_confidence=res.score,
                        file_status=f_status,
                        file_mode="dry-run" if dry_run else "normal",
                        file_save_path=web_accessible_path  # 👈 웹 주소로 바인딩 변경
                    )
                    db.add(new_history)
                    db.commit() # 원자적 물리 저장 확정

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

        files = [
            f for f in p.iterdir()
            if f.is_file() and f.suffix.lower() in IMAGE_EXTS
        ]
        return sorted(files)

    def _decide_label(self, raw_label: str, score: float) -> Tuple[str, str]:
        if score >= self.high:
            return raw_label, "high_conf_ok"
        if score >= self.mid:
            return self.review_label, "mid_conf_to_review"
        return self.unknown_label, "low_conf_to_unknown"