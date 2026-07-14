# test/test_main.py
import test_scanner
import test_saver
from service import ClassificationService

INPUT_DIR = "input"
OUTPUT_DIR = "output"

def main():
    service = ClassificationService(
        scanner_module=test_scanner,
        saver_module=test_saver,
        high_threshold=0.75,
        mid_threshold=0.55,
        review_label="review",
        unknown_label="unknown",
    )

    results = service.run_folder(INPUT_DIR, OUTPUT_DIR, dry_run=False)

    print(f"📁 {len(results)}개 이미지 발견\n")

    ok = 0
    for r in results:
        if r.status == "success":
            ok += 1
            print(f"[{r.index}/{r.total}] {r.filename}")
            print(f"   → {r.raw_label} ({int(r.score*100)}%)")
            print(f"   ✅ {r.final_label}/{r.saved_name} ({r.decision_reason})\n")
        else:
            print(f"[{r.index}/{r.total}] {r.filename}")
            print(f"   ❌ FAIL: {r.error}\n")

    print(f"✅ 완료! 성공 {ok}/{len(results)}")

if __name__ == "__main__":
    main()
