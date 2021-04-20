
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

    likes = relationship("Votes", back_populates="owner")


class Votes(Base):
    __tablename__ = "votes"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    upvote = Column(Integer, default=0)
    downvote = Column(Integer, default=0)
    user_email = Column(String, ForeignKey("users.email"))

    owner = relationship("User", back_populates="likes")

#User.__table__.create(bind=engine, checkfirst=True)
#Votes.__table__.create(bind=engine, checkfirst=True)
#
#session = SessionLocal()
#u = User(email="foo@bar.com", hashed_password="cc")
#session.add(u)
#session.commit()

