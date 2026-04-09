from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

# Libera o React para falar com a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "Engenharia de Dados Ativa", "engine": "Python 3.10"}

@app.get("/investigar/{cpf}")
async def investigar_politico(cpf: str):
    # Aqui vai entrar a lógica das 79 fontes + Gemini
    return {"buscando": cpf, "msg": "Em breve aqui o grafo de conexões"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4000)