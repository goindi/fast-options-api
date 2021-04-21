from sqlalchemy.orm import Session
from server.db.database import engine, SessionLocal
from server.db.models import User, Ratings

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def update_ratings(my_symbol,user,user_ratings):
    my_symbol = my_symbol.upper()
    session = SessionLocal()
    u = session.query(User).filter(User.email==user)
    if u.count() == 0:
        u = create_user(user)
    else:
        u = u.first()
    v = session.query(Ratings).filter(Ratings.user_email==u.email).filter(Ratings.symbol==my_symbol)
    if v.count() == 0:
        v = create_vote(my_symbol,u.email)
    else:
        v = v.first()
    v.ratings = v.ratings+user_ratings
    session.commit()


def get_ratings(symbol):
    symbol = symbol.upper()
    session = SessionLocal()
    s = session.execute(f"select average(ratings) from ratings where symbol='{symbol}'")
    c = s.fetchone()
    if c:
        return {'Ratings':c[0]}
    else:
        return {'Ratings':0}


def create_user(user_email,pwd="whateves"):
    u = User(email=user_email, hashed_password=pwd)
    session = SessionLocal()
    session.add(u)
    session.commit()
    session.refresh(u)
    return u

def create_vote(my_symbol,email):
    my_symbol = my_symbol.upper()
    v = Ratings(user_email=email, symbol=my_symbol)
    session = SessionLocal()
    session.add(v)
    session.commit()
    session.refresh(v)
    return v
