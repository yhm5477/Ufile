from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class TaskLog(Base):
    #작업 이력 관리 task_log 테이블 모델
    __tablename__ = "task_log"

    task_id = Column(String(50), primary_key=True, index=True, comment="비동기 작업 고유 ID")
    start_time = Column(DateTime, nullable=False, comment="작업 시작 일시")
    total_files = Column(Integer, nullable=False, comment="총 이미지 파일 수")
    job_status = Column(String(20), nullable=False, comment="현재 상태 (queued, processing, completed)")
    applied_threshold = Column(Float, nullable=False, comment="작업 시 적용된 임계값(Threshold)")
    memo = Column(Text, nullable=True, comment="작업 메모")

    # FileHistory 테이블과 1:N 관계 설정 (하나의 작업에 여러 파일 이력 존재)(그냥 그 알케미 기능)
    files = relationship("FileHistory", back_populates="task")

class FileHistory(Base):
    #파일 상세 이력 관리 file_history 테이블 모델
    __tablename__ = "file_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="고유 식별 이력 ID")
    task_id = Column(String(50), ForeignKey("task_log.task_id"), nullable=False, comment="작업 고유 ID (FK)")
    file_original_name = Column(String(255), nullable=False, comment="원본 파일명")
    file_new_name = Column(String(255), nullable=False, comment="정제 및 일련번호 적용된 새 파일명")
    file_label = Column(String(50), nullable=False, comment="CLIP AI가 확정한 분류 라벨")
    file_confidence = Column(Float, nullable=False, comment="AI 신뢰도 점수 (0.0 ~ 1.0)")
    file_status = Column(String(20), nullable=False, comment="3단계 분기 결과 상태 (success, review, unknown)")
    file_mode = Column(String(20), nullable=False, comment="파일 작업 모드")
    file_save_path = Column(Text, nullable=False, comment="최종 저장 격리 폴더 절대 경로")
    timestamp = Column(DateTime, server_default=func.now(), comment="기록 생성 시점")

    # TaskLog와 관계 설정
    task = relationship("TaskLog", back_populates="files")