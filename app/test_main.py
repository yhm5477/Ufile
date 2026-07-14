# test/test_main.py (핵심 부분 예시)
from test_scanner import scan, scan_folder
from test_saver import save_classified

INPUT_DIR = "input"
OUTPUT_DIR = "output"

def main():
    image_files = scan_folder(INPUT_DIR)
    print(f"📁 {len(image_files)}개 이미지 발견\n")

    for idx, img in enumerate(image_files, start=1):
        label, conf = scan(str(img))  # ✅ 여기엔 '파일경로'가 들어감

        new_name = save_classified(
            src_path=str(img),
            output_dir=OUTPUT_DIR,
            label=label,
            confidence=conf,
            dry_run=False
        )

        print(f"[{idx}/{len(image_files)}] {img.name}")
        print(f"   → {label} ({int(conf*100)}%)")
        print(f"   ✅ {label}/{new_name}\n")

if __name__ == "__main__":
    main()
