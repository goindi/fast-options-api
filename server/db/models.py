from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from server.db.database import engine, SessionLocal
from server.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    avatar = Column(String, default="")

    likes = relationship("Rating", back_populates="owner")
    #settings = relationship("Setting", back_populates="owner")


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    ratings = Column(Integer, default=0)
    ratings_change = Column(Integer, default=0)
    curr_value = Column(Float, default=0)
    user_email = Column(String, ForeignKey("users.email"))
    time_created = Column(DateTime(timezone=False), server_default=func.now())
    is_hidden = Column(Boolean, default=False)

    owner = relationship("User", back_populates="likes")

# class Setting(Base):
#     __tablename__ = "user_settings"
#
#     id = Column(Integer, primary_key=True, index=True)
#     avatar = Column(String, default="")
#     user_email = Column(String, ForeignKey("users.email"))
#
#     owner = relationship("User", back_populates="likes")
#User.__table__.create(bind=engine, checkfirst=True)
#Rating.__table__.create(bind=engine, checkfirst=True)
#Setting.__table__.create(bind=engine, checkfirst=True)
#
#session = SessionLocal()
#u = User(email="foo@bar.com", hashed_password="cc")
#session.add(u)
#session.commit()
