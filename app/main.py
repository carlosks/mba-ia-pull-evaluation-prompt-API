from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 🔹 Importa o router de projects
from app.routes.projects import router as projects_router

app = FastAPI(
    title="MBA IA - Prompt Evaluation API",
    description="API para geração de User Stories a partir de Bugs",
    version="1.0.0"
)

# 🔹 CORS (útil para frontend futuro)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # em produção, restrinja isso
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔥 REGISTRO DAS ROTAS (ESSENCIAL)
app.include_router(projects_router)


# 🔹 Rota raiz (health check)
@app.get("/")
def root():
    return {"msg": "SaaS rodando 🚀"}


# 🔹 Rota simples de teste
@app.get("/health")
def health():
    return {"status": "ok"}