from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
import json
from dotenv import load_dotenv

# Carrega as variáveis do seu arquivo .env no Zerver
load_dotenv()

app = FastAPI(
    title="Investiga Políticos API",
    description="Engine de consulta e triagem de dados investigativos",
    version="0.1.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
DB_USER = os.getenv("DB_USER", "investiga_user")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = "host.docker.internal" 
DB_NAME = "investiga_db"

DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- CONFIGURAÇÃO DATAJUD (FONTE 42) ---
DATAJUD_API_KEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

@app.get("/", tags=["Health"])
def status():
    return {"status": "online", "message": "Zerver FastAPI operante"}

@app.get("/investigar/processo/{numero_processo}", tags=["Investigação"])
def consultar_processo_datajud(numero_processo: str):
    """
    Consulta metadados de um processo específico pelo seu número (Padrão CNJ).
    Baseado na documentação oficial do DataJud.
    """
    # Para o teste em SP, usamos o índice do TJSP
    url = "https://api-publica.datajud.cnj.jus.br/api_publica_tjsp/_search"
    
    headers = {
        "Authorization": f"APIKey {DATAJUD_API_KEY}",
        "Content-Type": "application/json"
    }

    # Estrutura do payload exatamente como na documentação enviada
    payload = {
        "query": {
            "match": {
                "numeroProcesso": numero_processo
            }
        }
    }

    try:
        # Enviando como JSON para seguir o padrão da documentação
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        dados = response.json()
        hits = dados.get("hits", {}).get("hits", [])
        
        if not hits:
            raise HTTPException(status_code=404, detail="Processo não encontrado no tribunal especificado.")

        # Extraindo o _source do primeiro hit encontrado (ID único)
        processo_info = hits[0].get("_source", {})
        
        return {
            "status": "sucesso",
            "dados": {
                "numero": processo_info.get("numeroProcesso"),
                "classe": processo_info.get("classe", {}).get("nome"),
                "tribunal": processo_info.get("tribunal"),
                "data_ajuizamento": processo_info.get("dataAjuizamento"),
                "orgao_julgador": processo_info.get("orgaoJulgador", {}).get("nome"),
                "assuntos": [a.get("nome") for a in processo_info.get("assuntos", [])],
                "ultimas_movimentacoes": processo_info.get("movimentos", [])[:5] # Retorna as 5 últimas
            }
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Erro na comunicação com o DataJud: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# Mantendo suas rotas originais de candidatos para compatibilidade
@app.get("/candidatos", tags=["Dados"])
def listar_candidatos():
    db = SessionLocal()
    try:
        query = text("SELECT * FROM candidatos")
        result = db.execute(query)
        return {"candidatos": [dict(row._mapping) for row in result]}
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4000)