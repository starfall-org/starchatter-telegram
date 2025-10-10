from config import TURSO_DB_URL, TURSO_AUTH_TOKEN
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base

engine = create_engine(TURSO_DB_URL, connect_args={"auth_token": TURSO_AUTH_TOKEN})
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)
