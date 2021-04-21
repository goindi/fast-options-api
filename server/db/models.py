
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from server.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

    likes = relationship("Votes", back_populates="owner")


class Ratings(Base):
    __tablename__ = "ratings"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    ratings = Column(Integer, default=0)
    user_email = Column(String, ForeignKey("users.email"))

    owner = relationship("User", back_populates="likes")

#User.__table__.create(bind=engine, checkfirst=True)
#Ratings.__table__.create(bind=engine, checkfirst=True)
#
#session = SessionLocal()
#u = User(email="foo@bar.com", hashed_password="cc")
#session.add(u)
#session.commit()
