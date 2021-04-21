from sqlalchemy.orm import Session
from server.db.database import engine, SessionLocal
from server.db.models import User, Rating

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
    r = session.query(Rating).filter(Rating.user_email==u.email).filter(Rating.symbol==my_symbol)
    if r.count() == 0:
        r = create_ratings(my_symbol,u.email,user_ratings)
    else:
        r = r.first()
    r.ratings = r.ratings + user_ratings
    session.commit()


def get_ratings(symbol):
    symbol = symbol.upper()
    session = SessionLocal()
    s = session.execute(f"select avg(ratings) from ratings where symbol='{symbol}'")
    c = s.fetchone()
    if c[0]:
        return {'Rating':float(c[0])}
    else:
        return {'Rating':0}


def create_user(user_email,pwd="whateves"):
    u = User(email=user_email, hashed_password=pwd)
    session = SessionLocal()
    session.add(u)
    session.commit()
    session.refresh(u)
    return u

def create_ratings(my_symbol,email,user_ratings=0):
    my_symbol = my_symbol.upper()
    r = Rating(user_email=email, symbol=my_symbol, ratings=user_ratings)
    session = SessionLocal()
    session.add(r)
    session.commit()
    session.refresh(r)
    return r
