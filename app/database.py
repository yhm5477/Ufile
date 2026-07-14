from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ufile.db 파일로 생성 및 연결
SQLALCHEMY_DATABASE_URL = "sqlite:///./ufile.db"

# SQLite는 멀티스레드 환경에서 세션 공유를 위해 check_same_thread=False 설정 필수
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# DB랑 상호작용을 위한 세션 생성용
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 모델들이 상속받을 기본 클래스
Base = declarative_base()

# 의존성 주입을 위한 DB 세션 생성 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()