import datetime
import uuid
from sqlalchemy import Column, Integer, String, DateTime, Boolean, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import text as sa_text
import bcrypt
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()

class Database(Base):
    __tablename__ = 'user_databases'

    id = Column(UUID(as_uuid=True), primary_key=True,
                   default=uuid.uuid4, index=True)
    host = Column(String, nullable=True)
    name = Column(String, nullable=False)
    user = Column(String, nullable=False)
    password = Column(String, nullable=False)
    owner_id = Column(UUID(as_uuid=True), index=True)
    date_created = Column(DateTime, default=datetime.datetime.now)
    port = Column(Integer, nullable=True)
    database_flavour_name = Column(String)
    deleted = Column(Boolean, default=False)
    disabled = Column(Boolean, default=False)
    admin_disabled = Column(Boolean, default=False)
    default_storage_kb = Column(BigInteger, nullable=True,)
    allocated_size_kb = Column(BigInteger, nullable=True, default=1048576)
