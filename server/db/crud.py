from sqlalchemy.orm import Session
from server.db.database import engine, SessionLocal
from server.db.models import User, Votes

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def update_votes(my_symbol,user,up,down):
    my_symbol = my_symbol.upper()
    session = SessionLocal()
    u = session.query(User).filter(User.email==user)
    if u.count() == 0:
        u = create_user(user)
    else:
        u = u.first()
    v = session.query(Votes).filter(Votes.user_email==u.email).filter(Votes.symbol==my_symbol)
    if v.count() == 0:
        v = create_vote(my_symbol,u.email)
    else:
        v = v.first()
    v.upvote = v.upvote+up
    v.downvote = v.downvote+down
    session.commit()


def get_votes(symbol):
    symbol = symbol.upper()
    session = SessionLocal()
    s = session.execute(f"select (upvote-downvote) from votes where symbol='{symbol}'")
    c = s.fetchone()
    if c:
        return {'votes':c[0]}
    else:
        return {'votes':0}


def create_user(user_email,pwd="whateves"):
    u = User(email=user_email, hashed_password=pwd)
    session = SessionLocal()
    session.add(u)
    session.commit()
    session.refresh(u)
    return u

def create_vote(my_symbol,email):
    my_symbol = my_symbol.upper()
    v = Votes(user_email=email, symbol=my_symbol)
    session = SessionLocal()
    session.add(v)
    session.commit()
    session.refresh(v)
    return v
    

