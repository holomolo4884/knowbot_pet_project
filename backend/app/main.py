from fastapi import FastAPI

# Создаём экземпляр приложения
app = FastAPI(
    title="KnowBot API",
    description="RAG-система для поиска по базе знаний",
    version="0.1.0"
)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "backend"}

@app.get("/")
def root():
    return {"message": "Welcome to KnowBot API"}