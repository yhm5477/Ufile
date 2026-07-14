import os
os.environ["TRANSFORMERS_NO_TF"] = "1"  # 불필요한 경고 억제
from transformers import pipeline
from app.config import INPUT_DIR

def run_smoke_test():
    img_path = INPUT_DIR / "test.jpg"
    if not img_path.exists():
        print(f"❌ '{img_path}' 경로에 테스트용 이미지(test.jpg)가 없습니다! 사진을 넣어주세요.")
        return

    print("🔄 On-Device CLIP 모델 로딩 중... (최초 실행 시 다운로드로 인해 2~3분 소요됩니다.)")
    # 로컬 메모리에 모델 가공 적재
    classifier = pipeline(
        task="zero-shot-image-classification",
        model="openai/clip-vit-base-patch32"
    )
    print("✅ AI 모델 로드 완료!")

    # 테스트 추론 진행
    candidates = ["cat", "dog", "car", "building"]
    print(f"📷 이미지 분석 시작: {img_path.name}")
    
    out = classifier(str(img_path), candidate_labels=candidates)
    
    top_result = out[0]
    print("\n[🎯 AI 분석 결과]")
    print(f"라벨: {top_result['label']}")
    print(f"신뢰도 점수: {round(top_result['score'], 4)} ({int(top_result['score']*100)}%)")

if __name__ == "__main__":
    run_smoke_test()