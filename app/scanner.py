import os
import logging
from pathlib import Path
from transformers import pipeline

# TF 경고 억제 및 로컬 가속 환경 세팅
os.environ["TRANSFORMERS_NO_TF"] = "1"
logger = logging.getLogger(__name__)

class Scanner:
    _instance = None

    def __new__(cls, *args, **kwargs):
        """서버 메모리 폭주를 방지하기 위한 싱글톤 패턴 캡슐화"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        if self._initialized:
            return
        
        logger.info("🔄 On-Device CLIP 모델 로컬 메모리 적재 시작...")
        # 최초 1회만 432MB 가중치 파일을 로드하여 인메모리 상주 시킴
        self.classifier = pipeline(
            task="zero-shot-image-classification",
            model=model_name
        )
        # 설계서 제2장 2.2.2절: 기본 타깃 도메인 사전 정의
        self.default_candidates = ["cat", "dog", "bird", "wild animal", "document", "scenery", "other"]
        self._initialized = True
        logger.info("✅ AI 모델 로드 및 싱글톤 인스턴스 빌드 완료!")

    def scan(self, image_path: str, custom_candidates: list = None) -> tuple[str, float]:
        """
        [설계서 기능 #1 구현 명세]
        입력: 이미지 절대 경로, 사용자 정의 후보 키워드 배열
        처리: 도메인 텍스트 클래스 사전 필터링 및 코사인 유사도 소프트맥스 확률 연산
        출력: Top-1 매핑 라벨 명칭, 신뢰도 점수 (0.0 ~ 1.0)
        """
        if not Path(image_path).exists():
            raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")

        # 사전 필터링(Context Filtering) 메커니즘: 값이 없으면 기본 사전 사용
        candidates = custom_candidates if custom_candidates else self.default_candidates

        # CLIP 멀티모달 텐서 연산 실행
        outputs = self.classifier(image_path, candidate_labels=candidates)
        
        # 유사도 행렬 중 가장 확률이 높은 최상위 밀집 벡터(Top-1) 추출
        top_result = outputs[0]
        label = top_result["label"]
        confidence = float(top_result["score"])
        
        return label, confidence

# 조장 및 서비스 레이어가 주입받아 사용할 단일 전역 스캔 객체 노출
clip_scanner = Scanner()