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
# --- ENDPOINT INVESTIGAÇÃO POLÍTICO ---
@app.get("/investigar/politico/{nome}", tags=["Investigação"])
def investigar_politico(nome: str):
    try:
        # Use o seu método de conexão atual aqui (ex: conn = sua_funcao_db())
        conn = get_db_connection() 
        cursor = conn.cursor()

        # 1. BUSCA INFORMAÇÕES GERAIS E IDS (Query Master)
        # O %s garante que a busca por nome funcione sem SQL Injection
        query_geral = """
        SELECT 
            c.SQ_CANDIDATO,
            r.SQ_PRESTADOR_CONTAS,
            c.NM_CANDIDATO as Nome,
            c.NR_CPF_CANDIDATO as CPF,
            c.SG_PARTIDO as Partido,
            c.DS_CARGO as Cargo,
            c.DS_SITUACAO_CANDIDATURA as Situacao,
            c.SG_UF as Estado,
            (SELECT SUM(CAST(REPLACE(b.VR_BEM_CANDIDATO, ',', '.') AS DECIMAL(15,2)))
             FROM bens_candidatos_2022 b WHERE b.SQ_CANDIDATO = c.SQ_CANDIDATO) as Valor_Total_Bens,
            (SELECT SUM(CAST(REPLACE(do.VR_RECEITA, ',', '.') AS DECIMAL(15,2)))
             FROM receitas_candidatos_doador_originario_2022 do WHERE do.NR_CPF_CNPJ_DOADOR_ORIGINARIO = c.NR_CPF_CANDIDATO) as Total_Doador_Originario,
            (SELECT SUM(CAST(REPLACE(dx.VR_PAGTO_DESPESA, ',', '.') AS DECIMAL(15,2)))
             FROM despesas_pagas_2022 dx WHERE dx.SQ_PRESTADOR_CONTAS = r.SQ_PRESTADOR_CONTAS) as Gasto_Total
        FROM candidatos_2022 c
        INNER JOIN (
            SELECT DISTINCT SQ_CANDIDATO, SQ_PRESTADOR_CONTAS FROM receitas_candidatos_2022
        ) r ON c.SQ_CANDIDATO = r.SQ_CANDIDATO
        WHERE c.NM_CANDIDATO LIKE %s
        LIMIT 1;
        """
        cursor.execute(query_geral, (f"%{nome}%",))
        geral = cursor.fetchone()

        if not geral:
            conn.close()
            raise HTTPException(status_code=404, detail="Candidato não encontrado.")

        sq_cand = geral['SQ_CANDIDATO']
        sq_prestador = geral['SQ_PRESTADOR_CONTAS']

        # 2. TOP 5 DOADORES (Receitas)
        query_doadores = """
        SELECT NM_DOADOR, SUM(CAST(REPLACE(VR_RECEITA, ',', '.') AS DECIMAL(15,2))) as Total_Doado
        FROM receitas_candidatos_2022
        WHERE SQ_CANDIDATO = %s
        GROUP BY NM_DOADOR ORDER BY Total_Doado DESC LIMIT 5;
        """
        cursor.execute(query_doadores, (sq_cand,))
        top_doadores = cursor.fetchall()

        # 3. TOP 5 DESPESAS (Gasto Frequente)
        query_despesas = """
        SELECT DS_DESPESA, COUNT(*) as Quantidade_Vezes
        FROM despesas_pagas_2022
        WHERE SQ_PRESTADOR_CONTAS = %s
        GROUP BY DS_DESPESA ORDER BY Quantidade_Vezes DESC LIMIT 5;
        """
        cursor.execute(query_despesas, (sq_prestador,))
        top_despesas = cursor.fetchall()

        conn.close()

        # Retorno Limpo para o seu Front-end
        return {
            "status": "sucesso",
            "perfil": {
                "nome": geral['Nome'],
                "cpf": geral['CPF'],
                "partido": geral['Partido'],
                "cargo": geral['Cargo'],
                "situacao": geral['Situacao'],
                "estado": geral['Estado'],
                "sq_candidato": geral['SQ_CANDIDATO'] # Importante para o link da foto no front
            },
            "financeiro": {
                "patrimonio_declarado": float(geral['Valor_Total_Bens'] or 0),
                "total_gasto_campanha": float(geral['Gasto_Total'] or 0),
                "investimento_proprio_originario": float(geral['Total_Doador_Originario'] or 0)
            },
            "top_5_doadores": top_doadores,
            "top_5_gastos": top_despesas
        }

    except Exception as e:
        if 'conn' in locals(): conn.close()
        raise HTTPException(status_code=500, detail=f"Erro interno no servidor: {str(e)}")

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