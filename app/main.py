# app/main.py
####################################################
# uvicorn app.main:app --reload 
####################################################터미널에 입력
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import uuid
import shutil
from pathlib import Path
from datetime import datetime

from .database import engine, Base, SessionLocal
from .models import TaskLog, FileHistory
from app.config import INPUT_DIR, OUTPUT_DIR
from app.service import ClassificationService 
from app.scanner import Scanner  

# [1단계] 서버 구동 시 SQLite 데이터베이스 파일(ufile.db) 및 테이블 자동 생성
Base.metadata.create_all(bind=engine)

# [2단계] FastAPI 핵심 서버 인스턴스 단 한 번만 생성
app = FastAPI(title="U-File 온디바이스 AI 파일 분류 시스템")

# [3단계] 브라우저 통신용 CORS 미들웨어 안전하게 등록
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB 세션을 열고 닫아줄 의존성 주입 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. AI 스캐너 기계를 메모리에 조립합니다.
clip_scanner_instance = Scanner()

# 2. 조립된 clip_scanner_instance 기계를 서비스에 부품으로 주입(Injection)합니다.[cite: 6]
from app import saver  
classification_service = ClassificationService(
    scanner_module = clip_scanner_instance,
    saver_module = saver
)

# [★ 핵심 백그라운드 래퍼 함수 정의]
# 백그라운드 스레드가 돌 때 안전하게 DB 세션을 새로 열어 작업 결과를 저장하고 마스터 상태를 업데이트합니다.
def run_classification_task(task_id: str, input_dir: str, output_dir: str):
    db = SessionLocal()
    try:
        # service.py의 run_folder를 호출하며 task_id와 db 세션을 넘겨줍니다.
        classification_service.run_folder(
            input_dir=input_dir,
            output_dir=output_dir,
            task_id=task_id,
            db=db
        )
        # 모든 작업 완료 시 마스터 장부 상태를 완료(completed)로 변경
        task = db.query(TaskLog).filter(TaskLog.task_id == task_id).first()
        if task:
            task.job_status = "completed"
            db.commit()
    except Exception as e:
        task = db.query(TaskLog).filter(TaskLog.task_id == task_id).first()
        if task:
            task.job_status = "failed"
            db.commit()
        raise e
    finally:
        db.close()

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

    # 로컬 입력 디렉터리 생성 및 다중 이미지 영속성 복사
    Path(INPUT_DIR).mkdir(parents=True, exist_ok=True)
    for file in files:
        file_path = Path(INPUT_DIR) / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
    # [★ 공백 1 해결] SQLite 데이터베이스에 작업 마스터 로그(TaskLog) 먼저 한 줄 적재[cite: 6]
    db = SessionLocal()
    try:
        new_task = TaskLog(
            task_id=task_id,
            start_time=datetime.now(),
            total_files=len(files),
            job_status="processing",
            applied_threshold=0.75,
            memo=""
        )
        db.add(new_task)
        db.commit()
    finally:
        db.close()

    # [★ 공백 2 해결] 비동기 태스크 큐에 작업 등록 (진짜 데이터 쿼리 포함된 래퍼 가동)[cite: 6, 8]
    background_tasks.add_task(
        run_classification_task,
        task_id=task_id,
        input_dir=INPUT_DIR,
        output_dir=OUTPUT_DIR
    )
    
    return {
        "task_id": task_id,
        "status": "queued",
        "total_files": len(files),
        "message": "AI 분류 작업이 비동기 큐에 접수되었습니다."
    }

# 3) 실시간 진행률 및 분석 상태 반환 통로
@app.get("/api/status")
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    # DB에서 마스터 작업 로그(task_log) 조회[cite: 6]
    task = db.query(TaskLog).filter(TaskLog.task_id == task_id).first()
    if not task:
        return {"status": "failed", "message": "존재하지 않는 작업 ID입니다."}

    # 해당 task_id에 묶여 실제 AI 연산이 완료된 상세 파일 이력(file_history) 전부 쿼리[cite: 6]
    completed_records = db.query(FileHistory).filter(FileHistory.task_id == task_id).all()
    
    total = task.total_files  
    current_index = len(completed_records)  
    
    # 실시간 백분율 계산
    progress_percent = (current_index / total) * 100.0 if total > 0 else 0.0
    
    success_count = len([f for f in completed_records if f.file_status == "success"])
    fail_count = len([f for f in completed_records if f.file_status == "fail"])

    # 프론트엔드가 화면 갤러리에 동적으로 카드를 그릴 수 있도록 진짜 상세 리스트 동봉[cite: 6]
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
        "files": files_data  
    }

# [5단계] 최범석 팀원의 프론트엔드 정적 파일 호스팅 마운트 (★ 무조건 최하단 고정)
# 1. [추가] AI가 분류한 output 폴더를 브라우저가 읽을 수 있도록 정적 마운트 추가!
app.mount("/output", StaticFiles(directory="output"), name="output")

# 2. 기존 static 폴더 마운트 (무조건 가장 최하단 고정)
app.mount("/", StaticFiles(directory="static", html=True), name="static")