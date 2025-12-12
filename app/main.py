from fastapi import FastAPI,Depends,HTTPException,Response
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
from sqlalchemy import select
from model import User ,Historique,Category
# from app.model import User ,Historique,Category
from schemas import UserLogin, UserRegister ,ClassifyText,CategoryInDB,AnalyzeRequest,ClassifyRequest
# from app.schemas import UserLogin, UserRegister ,ClassifyText,CategoryInDB,AnalyzeRequest,ClassifyRequest
from sqlalchemy.orm import sessionmaker,Session
from passlib.context import CryptContext
from datetime import datetime,timedelta
from jose import jwt
from model import Base
# from app.model import Base
from fastapi.middleware.cors import CORSMiddleware
from hf_model import query
# from app.hf_model import query
from google import genai
from google.genai import types
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import time
from google.genai.errors import ServerError, APIError
# from fastapi.security import OAuth2PasswordBearer


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

# DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# DATABASE_URL= os.getenv("DATABASE_URL_DEVELOP")
# DATABASE_URL = os.getenv("DATABASE_URL_PRODUCTION")

ENV = os.getenv("ENV", "development") 
if ENV == "production":
    DATABASE_URL = os.getenv("DATABASE_URL_PRODUCTION")
else:
    DATABASE_URL = os.getenv("DATABASE_URL_DEVELOP")

print(f"Running in {ENV} mode")


# engine=create_engine(DATABASE_URL)
# session=sessionmaker(bind=engine,autocommit=False,autoflush=False)

engine = create_async_engine(DATABASE_URL, echo=True, connect_args={
        "ssl": "require", 
    })
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with async_session() as session:
        yield session


# Base.metadata.create_all(bind=engine)


# def get_db():
#     db=async_session()
#     try:
#         yield db
#     finally:
#         db.close()

client =genai.Client(api_key=GEMINI_API_KEY)  

pwd_context=CryptContext(schemes=["argon2","bcrypt"],deprecated="auto")
@app.post("/register")
async def register(user: UserRegister, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(User).where(User.username == user.username))
    existing = q.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=403, detail="User already exists")

    new_user = User(
        firstname=user.firstname,
        lastname=user.lastname,
        username=user.username,
        password=pwd_context.hash(user.password),
        created_at=datetime.utcnow()
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

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

@app.post("/login")
async def login(user: UserLogin, response: Response, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(User).where(User.username == user.username))
    existing_user = q.scalar_one_or_none()

    if not existing_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not pwd_context.verify(user.password, existing_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = jwt.encode(
        {"sub": existing_user.username, "id": existing_user.id,
         "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)},
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    response.set_cookie("access_token", f"Bearer {token}", httponly=True)

    return {"message": "Login successful"}

# @app.get("/auth/me")
# async def get_current_user_from_cookie(token: str = Depends(oauth2_scheme)):
    # validate JWT from cookie
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    # decode token...
    return {"user": "example"} 


@app.post('/categories')
async def add_categories(category: CategoryInDB, db: AsyncSession = Depends(get_db)):
    categories = Category(name=category.name)
    db.add(categories)
    await db.commit()
    await db.refresh(categories)
    return {"categories": categories}


@app.get('/categories')
async def get_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category))
    categories = result.scalars().all()
    return {"categories": categories}



@app.post('/analyze')
async def analyze(request: AnalyzeRequest, db: AsyncSession = Depends(get_db)):
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
        await db.commit()
        await db.refresh(new_historique)
        
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
        print("ERROR:", e)
        raise HTTPException(500, f"Analysis failed: {e}")

    

def generate_gemini_summary(text: str, best_category: str):
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
        
    
   
    
@app.post('/classify', response_model=ClassifyText)
def classify_text(payload: ClassifyRequest):
    # print(f"Text: {payload.text}")
    # print(f"Category: {payload.best_category}")
    
    try:
        gemini_result = generate_gemini_summary(
            text=payload.text,
            best_category=payload.best_category
        )
        # print(f"✓ Classification successful: {gemini_result}")
        return {
            "category": payload.best_category,
            "score": payload.score,
            "summary": gemini_result["summary"],
            "tone": gemini_result["tone"],
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Classification failed: {str(e)}"
        )