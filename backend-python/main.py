from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Carrega as variáveis do seu arquivo .env no Zerver
load_dotenv()

app = FastAPI(
    title="Investiga Políticos API",
    description="Engine de consulta e triagem de dados investigativos",
    version="0.1.0"
)

# Configuração de CORS: Essencial para o seu Frontend React (porta 3001) 
# conseguir consumir esta API (porta 4001) sem ser bloqueado pelo navegador.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
DB_USER = os.getenv("DB_USER", "investiga_user")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = "host.docker.internal"  # Aponta para o MySQL fora do container
DB_NAME = "investiga_db"

DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

# Engine e Session do SQLAlchemy
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@app.get("/", tags=["Health"])
def status():
    """Verifica se a API está online."""
    return {"status": "online", "message": "Zerver FastAPI operante"}

@app.get("/test-db", tags=["Infraestrutura"])
def test_db_connection():
    """Valida se o container alcança o MySQL Bare Metal."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT VERSION()"))
            version = result.fetchone()[0]
            return {
                "conexao": "sucesso",
                "mysql_version": version,
                "database": DB_NAME
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro de conexão: {str(e)}")

@app.get("/candidatos", tags=["Dados"])
def listar_candidatos():
    """
    Busca todos os candidatos cadastrados na tabela do Workbench.
    Útil para testar se a leitura de dados está funcionando.
    """
    db = SessionLocal()
    try:
        # Consulta simples na tabela que você criou
        query = text("SELECT * FROM candidatos")
        result = db.execute(query)
        
        # Converte as linhas do MySQL para uma lista de dicionários (JSON)
        candidatos = [dict(row._mapping) for row in result]
        
        return {
            "total": len(candidatos),
            "candidatos": candidatos
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar candidatos: {str(e)}")
    finally:
        db.close()

# --- MOTOR DO SERVIDOR ---
if __name__ == "__main__":
    import uvicorn
    # Rodando na porta 4000 interna (mapeada para 4001 externa no Docker Compose)
    uvicorn.run(app, host="0.0.0.0", port=4000)