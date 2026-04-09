from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

app = FastAPI(
    title="Investiga Políticos API",
    description="Interface de Engenharia de Dados para triagem investigativa",
    version="0.1.0"
)

# Configuração de CORS para permitir que o seu Frontend (React) fale com a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURAÇÃO DO BANCO ---
# O DB_HOST 'host.docker.internal' aponta para o seu MySQL Bare Metal (fora do Docker)
DB_USER = os.getenv("DB_USER", "investiga_user")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = "host.docker.internal" 
DB_NAME = "investiga_db"

# String de conexão utilizando o driver mysql-connector-python
DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

@app.get("/", tags=["Health"])
def status():
    """Verifica se a API está online."""
    return {"status": "online", "message": "Zerver FastAPI está vivo e operante!"}

@app.get("/test-db", tags=["Infraestrutura"])
def test_db_connection():
    """
    Tenta realizar uma consulta simples no MySQL Bare Metal
    para validar a conectividade Docker -> Host.
    """
    try:
        # Criamos o engine aqui para testar a conexão instantaneamente
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            # Executa um comando simples para pegar a versão do MySQL
            result = connection.execute(text("SELECT VERSION()"))
            version = result.fetchone()[0]
            return {
                "conexao": "sucesso",
                "mysql_version": version,
                "database": DB_NAME,
                "host": DB_HOST
            }
    except Exception as e:
        # Se falhar, retorna o erro exato para facilitar o debug no Swagger
        raise HTTPException(
            status_code=500, 
            detail=f"Falha na conexão com o banco: {str(e)}"
        )

# --- INICIALIZADOR DO SERVIDOR ---
if __name__ == "__main__":
    import uvicorn
    # Rodar em 0.0.0.0 é obrigatório para que o Docker exponha a porta corretamente
    # Usamos a porta 4000 (que no seu compose está mapeada para a 4001 externa)
    uvicorn.run(app, host="0.0.0.0", port=4000)