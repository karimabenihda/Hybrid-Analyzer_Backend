from sqlalchemy.orm import declarative_base
from sqlalchemy import Column,Integer,String,DateTime,Float
# from main import engine

Base=declarative_base()

class User(Base):
    __tablename__="users"
    id=Column(Integer, primary_key=True, index=True)
    firstname = Column(String)
    lastname = Column(String)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    created_at = Column(DateTime)
    

class Historique(Base):
    __tablename__='historiques'
    id=Column(Integer, primary_key=True, index=True)
    text = Column(String)
    classification=Column(String)
    score=Column(Float)
    created_at = Column(DateTime)
    


class Category(Base):
    __tablename__='categories'
    id=Column(Integer, primary_key=True, index=True)
    name = Column(String)