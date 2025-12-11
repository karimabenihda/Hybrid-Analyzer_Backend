from pydantic import BaseModel
from datetime import datetime 


class UserRegister(BaseModel):
    firstname :str
    lastname :str
    username :str
    password :str
    created_at :datetime=None
    
    
class UserLogin(BaseModel):
    username :str
    password :str
    

class HistoriqueInDB(BaseModel):
    text :str
  

class CategoryInDB(BaseModel):
    name:str

class AnalyzeRequest(BaseModel):
    text: str
    categories: list[str]
    
class AnalyzeResponse(BaseModel):
    text: str
    best_category: str
    score: float

class ClassifyRequest(BaseModel):
    text: str
    best_category: str
    score: float

class ClassifyText(BaseModel):
    category: str
    score: float
    summary: str
    tone: str
    