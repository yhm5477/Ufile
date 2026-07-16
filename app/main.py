# app/main.py
####################################################
# uvicorn app.main:app --reload 
####################################################터미널에 입력
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends
from sqlalchemy.orm import Session
from typing import List
import uuid
import shutil
from pathlib import Path

from .database import engine, Base, SessionLocal
from .models import TaskLog, FileHistory


from app.config import INPUT_DIR, OUTPUT_DIR
from app.service import ClassificationService # service.py에서 정의한 인스턴스
from app.scanner import Scanner  # 휘민 학생이 작성한 AI 스캐너 모듈
from app import saver    # 선우 팀원이 작성한 물리 저장 모듈

# [1단계] 서버 구동 시 SQLite 데이터베이스 파일(ufile.db) 및 테이블 자동 생성[cite: 9, 10]
Base.metadata.create_all(bind=engine)

# [2단계] FastAPI 핵심 서버 인스턴스 단 한 번만 생성[cite: 10]
app = FastAPI(title="U-File 온디바이스 AI 파일 분류 시스템")

# [3단계] 브라우저 통신용 CORS 미들웨어 안전하게 등록
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# [4단계] API 라우터 선언 구역 (★ 무조건 static 마운트보다 위에 있어야 정상 작동합니다)

# 1. AI 스캐너 기계를 메모리에 조립합니다.
clip_scanner_instance = Scanner()

# 2. 조립된 clip_scanner_instance 기계를 서비스에 부품으로 주입(Injection)합니다.
classification_service = ClassificationService(
    scanner_module = clip_scanner_instance,
    saver_module = saver
)
# 1) 데이터베이스 및 서버 연결 상태 검증용 API (Health Check)
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "message": "On-Device U-File 서버 및 SQLite 데이터베이스가 정상 구동 중입니다."
    }

# 2) 이미지 다중 업로드 수신 및 비동기 작업 ID(task_id) 즉시 발급 통로 (설계서 제3장 기준)
@app.post("/api/upload")
async def upload_images(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    task_id = f"task_{uuid.uuid4().hex[:8]}"

    Path(INPUT_DIR).mkdir(parents=True, exist_ok=True)
    for file in files:
        file_path = Path(INPUT_DIR) / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    # TODO: 향후 류휘민 개발자님이 완성할 핵심 AI 추론 엔진(service.py) 연동 영역
    # background_tasks.add_task(classification_v.)
    background_tasks.add_task(
        classification_service.run_folder, 
        input_dir=INPUT_DIR, 
        output_dir=OUTPUT_DIR
    )
    
    return {
        "task_id": task_id,
        "status": "queued",
        "total_files": len(files),
        "message": "AI 분류 작업이 비동기 큐에 접수되었습니다."
    }
# DB 세션을 열고 닫아줄 의존성 주입 함수 선언 (main.py 상단이나 내부에 선언)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
# 3) 실시간 진행률 및 분석 상태 반환 통로 (조장이 DB를 다 붙이기 전까지 UI를 띄워줄 가짜 명세)
@app.get("/api/status")
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    # 1. DB에서 마스터 작업 로그(task_log) 조회
    task = db.query(TaskLog).filter(TaskLog.task_id == task_id).first()
    if not task:
        return {"status": "failed", "message": "존재하지 않는 작업 ID입니다."}

    # 2. 이 task_id에 묶여 실제 AI 연산이 완료된 상세 파일 이력(file_history) 전부 쿼리
    completed_records = db.query(FileHistory).filter(FileHistory.task_id == task_id).all()
    
    total = task.total_files  # 업로드할 때 저장했던 실제 총 파일 개수
    current_index = len(completed_records)  # 현재까지 AI 분류 및 저장이 완료된 파일 개수
    
    # 실시간 백분율 계산
    progress_percent = (current_index / total) * 100.0 if total > 0 else 0.0
    
    # 3단계 임계값 분기 결과별 상태 카운트 계산
    success_count = len([f for f in completed_records if f.file_status == "success"])
    fail_count = len([f for f in completed_records if f.file_status == "fail"])

    # 3. [★ 핵심 수혈] 프론트엔드가 화면 갤러리에 동적으로 카드를 그릴 수 있도록 진짜 상세 리스트 동봉
    files_data = []
    for record in completed_records:
        files_data.append({
            "id": record.id,
            "original_name": record.file_original_name,
            "new_name": record.file_new_name,
            "label": record.file_label,
            "confidence": record.file_confidence,
            "status": record.file_status,
            "save_path": record.file_save_path
        })

    return {
        "task_id": task_id,
        "total": total,
        "current_index": current_index,
        "progress_percent": round(progress_percent, 1),
        "success_count": success_count,
        "fail_count": fail_count,
        "status": "completed" if current_index >= total else "processing",
        "files": files_data  # 👈 범석이가 화면에 카드를 그릴 진짜 원천 소스 데이터 주입!
    }

# [5단계] 최범석 팀원의 프론트엔드 정적 파일 호스팅 마운트 (★ 무조건 최하단 고정)[cite: 10]
app.mount("/", StaticFiles(directory="static", html=True), name="static")