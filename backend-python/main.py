from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Investiga Políticos API")

# --- CONFIGURAÇÃO DATAJUD (FONTE 42) ---
# Certifique-se de que esta chave não tem espaços extras
DATAJUD_API_KEY = "cVp6S2o0Ym02Ym1wM21wM21wM21wM21wM21wM21wM21wM21wM21wM21w"

@app.get("/investigar/processo/{numero_processo}", tags=["Investigação"])
def consultar_processo_datajud(numero_processo: str):
    # 1. Limpeza do número para garantir que o Elasticsearch encontre (apenas dígitos)
    numero_limpo = "".join(filter(str.isdigit, numero_processo))
    
    url = "https://cnj.jus.br"
    
    headers = {
        "Authorization": f"APIKey {DATAJUD_API_KEY}",
        "Content-Type": "application/json"
    }

    # 2. Query usando 'match' para maior flexibilidade ou 'term' para exatidão
    payload = {
        "query": {
            "match": {
                "numeroProcesso": numero_limpo
            }
        }
    }

    print(f"\n--- DEBUG: Iniciando consulta para o processo: {numero_limpo} ---")
    print(f"Payload enviado: {json.dumps(payload)}")

    try:
        response = requests.post(url, json=payload, headers=headers)
        
        # Log do status da resposta
        print(f"Status Code da API CNJ: {response.status_code}")
        
        response.raise_for_status()
        dados = response.json()
        
        # Log do JSON bruto retornado (Isso aparecerá no seu terminal/console)
        print("JSON Bruto recebido do DataJud:")
        print(json.dumps(dados, indent=2))

        # 3. Extração correta: hits -> hits (lista)
        lista_hits = dados.get("hits", {}).get("hits", [])
        
        if not lista_hits:
            print(f"AVISO: A lista de hits veio vazia para o número {numero_limpo}")
            raise HTTPException(status_code=404, detail=f"Processo {numero_limpo} não encontrado ou é sigiloso no TJSP.")

        # O primeiro item da lista contém o '_source' com os dados
        processo_info = lista_hits[0].get("_source", {})
        
        # 4. Mapeamento seguro dos campos
        resultado = {
            "status": "sucesso",
            "dados": {
                "numero": processo_info.get("numeroProcesso"),
                "classe": processo_info.get("classe", {}).get("nome", "Não informada"),
                "tribunal": processo_info.get("tribunal"),
                "data_ajuizamento": processo_info.get("dataAjuizamento"),
                "orgao_julgador": processo_info.get("orgaoJulgador", {}).get("nome", "Não informado"),
                "assuntos": [a.get("nome") for a in processo_info.get("assuntos", []) if a.get("nome")],
                "ultimas_movimentacoes": processo_info.get("movimentos", [])[:5]
            }
        }
        
        print("Processamento concluído com sucesso.")
        return resultado

    except requests.exceptions.HTTPError as e:
        print(f"ERRO HTTP: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Erro na API DataJud: {e.response.text}")
    except Exception as e:
        print(f"ERRO INTERNO: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno no servidor: {str(e)}")

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