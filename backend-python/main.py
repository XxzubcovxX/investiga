from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Investiga Políticos API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURAÇÃO DATAJUD ---
# Chave pública padrão atualizada do CNJ
DATAJUD_API_KEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

@app.get("/investigar/processo/{numero_processo}", tags=["Investigação"])
def consultar_processo_datajud(numero_processo: str):
    # 1. Limpa o número para garantir que tenha apenas dígitos (Padrão para a busca 'term')
    numero_limpo = "".join(filter(str.isdigit, numero_processo))
    
    # Endpoint específico para o TJSP
    url = "https://cnj.jus.br"
    
    headers = {
        "Authorization": f"APIKey {DATAJUD_API_KEY}",
        "Content-Type": "application/json"
    }

    # 2. Query usando 'term' para busca exata no campo keyword
    payload = {
        "query": {
            "term": {
                "numeroProcesso": numero_limpo
            }
        }
    }

    print(f"\n--- DEBUG: Consultando {numero_limpo} ---")

    try:
        # Timeout de 10s para evitar que sua API trave se o CNJ demorar
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        # Log preventivo: Se não for 200, imprime o que o CNJ mandou (mesmo que seja HTML)
        if response.status_code != 200:
            print(f"Erro do CNJ (Status {response.status_code}): {response.text}")
            raise HTTPException(
                status_code=response.status_code, 
                detail=f"DataJud retornou erro {response.status_code}. Verifique a API Key."
            )

        # 3. Validação do JSON para evitar o erro "char 0"
        try:
            dados = response.json()
        except json.JSONDecodeError:
            print("Erro Crítico: O DataJud não retornou um JSON válido.")
            print(f"Conteúdo recebido: {response.text[:200]}") # Primeiros 200 caracteres
            raise HTTPException(status_code=502, detail="Resposta do DataJud não é um JSON válido.")

        # 4. Extração segura dos dados
        hits = dados.get("hits", {}).get("hits", [])
        
        if not hits:
            raise HTTPException(
                status_code=404, 
                detail=f"Processo {numero_limpo} não encontrado no TJSP (pode ser sigiloso ou físico)."
            )

        # O dado real está no _source do primeiro resultado
        processo_info = hits[0].get("_source", {})
        
        return {
            "status": "sucesso",
            "metadados": {
                "numero": processo_info.get("numeroProcesso"),
                "classe": processo_info.get("classe", {}).get("nome"),
                "tribunal": processo_info.get("tribunal"),
                "data_ajuizamento": processo_info.get("dataAjuizamento"),
                "orgao_julgador": processo_info.get("orgaoJulgador", {}).get("nome"),
                "assuntos": [a.get("nome") for a in processo_info.get("assuntos", []) if a.get("nome")],
                "ultimas_movimentacoes": processo_info.get("movimentos", [])[:3] # Reduzi para 3 para teste
            }
        }

    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="O servidor do DataJud demorou muito para responder.")
    except Exception as e:
        print(f"Erro inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4000)