from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from . import models

def create_task_log(db: Session, task_id: str, total_files: int):
    db_task = models.TaskLog(
        task_id=task_id, 
        total_files=total_files, 
        job_status="queued",
        start_time=func.now()
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def get_task_by_id(db: Session, task_id: str):
    return db.query(models.TaskLog).filter(models.TaskLog.task_id == task_id).first()