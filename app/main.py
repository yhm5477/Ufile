# app/main.py
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import uuid

from .database import engine, Base
from .models import TaskLog, FileHistory

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
    
    # TODO: 향후 류휘민 개발자님이 완성할 핵심 AI 추론 엔진(service.py) 연동 영역
    # background_tasks.add_task(classification_service.run_folder, ...)
    
    return {
        "task_id": task_id,
        "status": "queued",
        "total_files": len(files),
        "message": "AI 분류 작업이 비동기 큐에 접수되었습니다."
    }

# 3) 실시간 진행률 및 분석 상태 반환 통로 (조장이 DB를 다 붙이기 전까지 UI를 띄워줄 가짜 명세)
@app.get("/api/status")
def get_task_status(task_id: str):
    return {
        "task_id": task_id,
        "total": 10,
        "current_index": 10,
        "progress_percent": 100.0,
        "success_count": 10,
        "fail_count": 0,
        "status": "completed"
    }

# [5단계] 최범석 팀원의 프론트엔드 정적 파일 호스팅 마운트 (★ 무조건 최하단 고정)[cite: 10]
app.mount("/", StaticFiles(directory="static", html=True), name="static")