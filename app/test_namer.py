"""
namer.py - 파일명 생성 규칙
분류된 이미지의 새 파일명을 생성합니다.
"""

from pathlib import Path
#from scaaner import scan_result
#더미 스캔값 한 개분
scan_result = {
    "label": "dog",
    "confidence": 0.74,
    "keywords": ["animal", "pet"]
} 

def generate_name(label, original_filename, include_confidence=False, confidence=None):
    """
    새 파일명 생성
    
    include_confidence=False: dog_photo.jpg
    include_confidence=True:  dog_95_photo.jpg
    """
    path = Path(original_filename)
    stem = path.stem
    suffix = path.suffix.lower()
    
    if include_confidence and confidence is not None:
        conf_percent = int(confidence * 100)
        new_filename = f"{label}_{conf_percent}_{stem}{suffix}"
    else:
        new_filename = f"{label}_{stem}{suffix}"
    
    return new_filename
    
def unique_path(dst):
    """중복 시 _1, _2... 자동 추가"""
    if not dst.exists():
        return dst
    
    stem, suffix = dst.stem, dst.suffix
    i = 1
    while True:
        cand = dst.with_name(f"{stem}_{i}{suffix}")
        if not cand.exists():
            return cand
        i += 1
# 나중에 추가할 함수들 (필요시 작성)
# def generate_name_with_timestamp(label, original_name):
#     """날짜/시간 포함 버전"""
#     pass
#
# def generate_name_with_index(label, original_name, index):
#     """순번 포함 버전"""
#     pass
