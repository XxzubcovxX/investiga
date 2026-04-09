from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Investiga Políticos API",
    description="Interface de Engenharia de Dados para triagem investigativa",
    version="0.1.0"
)

# --- CONFIGURAÇÃO DO BANCO ---
DB_USER = os.getenv("DB_USER", "investiga_user")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = "host.docker.internal" 
DB_NAME = "investiga_db"

# String de conexão para o MySQL
DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

@app.get("/", tags=["Health"])
def status():
    return {"status": "online", "message": "Zerver FastAPI está vivo!"}

@app.get("/test-db", tags=["Infraestrutura"])
def test_db_connection():
    """
    Tenta realizar uma consulta simples no MySQL Bare Metal
    para validar a conectividade Docker -> Host.
    """
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            # Executa um comando simples de versão do MySQL
            result = connection.execute(text("SELECT VERSION()"))
            version = result.fetchone()[0]
            return {
                "conexao": "sucesso",
                "mysql_version": version,
                "database": DB_NAME,
                "host": DB_HOST
            }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Falha na conexão com o banco: {str(e)}"
        )