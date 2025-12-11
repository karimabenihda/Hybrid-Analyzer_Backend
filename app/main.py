from fastapi import FastAPI,Depends,HTTPException,Response
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
# from model import User ,Historique,Category
from app.model import User ,Historique,Category
# from schemas import UserLogin, UserRegister ,ClassifyText,CategoryInDB,AnalyzeRequest,ClassifyRequest
from app.schemas import UserLogin, UserRegister ,ClassifyText,CategoryInDB,AnalyzeRequest,ClassifyRequest
from sqlalchemy.orm import sessionmaker,Session
from passlib.context import CryptContext
from datetime import datetime,timedelta
from jose import jwt
# from model import Base
from app.model import Base
from fastapi.middleware.cors import CORSMiddleware
# from hf_model import query
from app.hf_model import query
from google import genai
from google.genai import types
import json

app=FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()

GEMINI_API_KEY=os.getenv("GEMINI_API_KEY")
DB_USER=os.getenv("USER")
DB_PASSWORD=os.getenv("PASSWORD")
DB_NAME=os.getenv("DB_NAME")
DB_HOST=os.getenv("HOST")
DB_PORT=os.getenv("PORT")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))


DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


client =genai.Client(api_key=GEMINI_API_KEY)  


engine=create_engine(DATABASE_URL)


session=sessionmaker(bind=engine,autocommit=False,autoflush=False)

Base.metadata.create_all(bind=engine)


def get_db():
    db=session()
    try:
        yield db
    finally:
        db.close()


pwd_context=CryptContext(schemes=["argon2","bcrypt"],deprecated="auto")
@app.post('/register')
def register(user:UserRegister,db:Session=Depends(get_db)):
    existing_user=db.query(User).filter(User.username==user.username).first()
    if existing_user:
        raise HTTPException(status_code=403, detail="User already exist")    
    
    new_user = User(
        firstname=user.firstname,
        lastname=user.lastname,
        username=user.username,
        password=pwd_context.hash(user.password),
        created_at=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


def create_access_token(data:dict,expires_delta:timedelta=None):
    to_encode=data.copy()
    if expires_delta:
        expire=datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp":expire})
    encoded_jwt=jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)
    return encoded_jwt

@app.post('/login')
def login(user: UserLogin, response: Response, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == user.username).first()
    
    if not existing_user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    if not pwd_context.verify(user.password, existing_user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": existing_user.username, "id": existing_user.id},
        expires_delta=access_token_expires
    )
    
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False
    )
    
    return {
        "message": "Login successful",
        "user": {
            "id": existing_user.id,
            "username": existing_user.username,
            "firstname": existing_user.firstname,
            "lastname": existing_user.lastname
        }
    }

@app.post('/categories')
def add_categories(category:CategoryInDB,db:Session=Depends(get_db)):
    categories=Category(name=category.name)
    db.add(categories)
    db.commit()
    db.refresh(categories)
    return {"categories":categories}


@app.get('/categories')
def get_categories(db:Session=Depends(get_db)):
    categories = db.query(Category).all()
    return {"categories":categories}



@app.post('/analyze',)
def analyze(request: AnalyzeRequest, db: Session = Depends(get_db)):
    try:
        result = query(request.text, request.categories)
        best_category = result[0]["label"]
        best_score = result[0]["score"]
        
        new_historique = Historique(
            text=request.text,
            classification=best_category,
            score=best_score,
            created_at=datetime.now()
        )
        db.add(new_historique)
        db.commit()
        db.refresh(new_historique)
        
        all_labels = [item["label"] for item in result]
        all_scores = [item["score"] for item in result]
        
        return {
            "text": request.text,
            "best_category": best_category,
            "score": best_score,
            "all_results": {
                "labels": all_labels,
                "scores": all_scores
            }
        }
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print("ERROR DETAILS:")
        print(error_details)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    
    
  
def generate_gemini_summary(text:str,best_category:str):
        prompt=f"""
        Tu es un assistant d'analyse très précis.
        Contexte:
        - Catégorie détectée : {best_category}
        
        taches:
        1. Génère un résumé concis et ciblé du texte en prenant la catégorie comme contexte.
        2. Analyse le ton global du texte : positif, négatif ou neutre.

        Format de réponse OBLIGATOIRE (JSON strict) :
        {{
            "summary": "…",
            "tone": "positif|negatif|neutre"
        }}
        Text à analyser:
        {text}
        """
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
              response_mime_type="application/json"
            )
        )
        return json.loads(response.text)
      
      
@app.post('/classify',response_model=ClassifyText)
def classify_text(payload:ClassifyRequest):
    gemini_result = generate_gemini_summary(
    text=payload.text,
    best_category=payload.best_category
        )
    return {
        "category": payload.best_category,
        "score": payload.score,
        "summary": gemini_result["summary"],
        "tone": gemini_result["tone"],
    }