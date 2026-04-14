from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
import json
import pymysql
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Investiga Políticos API")

# Configuração de CORS para o seu Front em React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- FUNÇÃO DE CONEXÃO COM O BANCO ---
def get_db_connection():
    # Ele vai puxar automaticamente as variáveis do seu Docker Compose / .env
    return pymysql.connect(
        host=os.getenv("DB_HOST", "host.docker.internal"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", ""),
        database=os.getenv("DB_NAME", "investiga_db"),
        cursorclass=pymysql.cursors.DictCursor
    )

# --- ENDPOINT INVESTIGAÇÃO POLÍTICO (O NOVO) ---
@app.get("/investigar/politico/{nome}", tags=["Investigação"])
def investigar_politico(nome: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. BUSCA UMA LISTA DE CANDIDATOS (Aumentamos o limite e tiramos o fetchone)
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
        LIMIT 10;
        """
        cursor.execute(query_geral, (f"%{nome}%",))
        candidatos_encontrados = cursor.fetchall() # Agora pegamos TODOS (fetch ALL)

        if not candidatos_encontrados:
            raise HTTPException(status_code=404, detail="Nenhum candidato encontrado.")

        # 2. MONTAR O RESULTADO FINAL
        lista_final = []

        for cand in candidatos_encontrados:
            sq_cand = cand['SQ_CANDIDATO']
            sq_prestador = cand['SQ_PRESTADOR_CONTAS']

            # TOP 5 DOADORES para ESTE candidato específico
            cursor.execute("""
                SELECT NM_DOADOR, SUM(CAST(REPLACE(VR_RECEITA, ',', '.') AS DECIMAL(15,2))) as Total_Doado
                FROM receitas_candidatos_2022
                WHERE SQ_CANDIDATO = %s
                GROUP BY NM_DOADOR ORDER BY Total_Doado DESC LIMIT 5;
            """, (sq_cand,))
            top_doadores = cursor.fetchall()

            # TOP 5 DESPESAS para ESTE candidato específico
            cursor.execute("""
                SELECT DS_DESPESA, COUNT(*) as Quantidade_Vezes
                FROM despesas_pagas_2022
                WHERE SQ_PRESTADOR_CONTAS = %s
                GROUP BY DS_DESPESA ORDER BY Quantidade_Vezes DESC LIMIT 5;
            """, (sq_prestador,))
            top_despesas = cursor.fetchall()

            # Monta o objeto de cada candidato
            item = {
                "perfil": {
                    "nome": cand['Nome'],
                    "cpf": cand['CPF'],
                    "partido": cand['Partido'],
                    "cargo": cand['Cargo'],
                    "situacao": cand['Situacao'],
                    "estado": cand['Estado'],
                    "sq_candidato": cand['SQ_CANDIDATO']
                },
                "financeiro": {
                    "patrimonio_declarado": float(cand['Valor_Total_Bens'] or 0),
                    "total_gasto_campanha": float(cand['Gasto_Total'] or 0),
                    "investimento_proprio_originario": float(cand['Total_Doador_Originario'] or 0)
                },
                "top_5_doadores": top_doadores,
                "top_5_gastos": top_despesas
            }
            lista_final.append(item)

        return {
            "status": "sucesso",
            "total_encontrado": len(lista_final),
            "resultados": lista_final
        }

    except Exception as e:
        print(f"ERRO: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# --- CONFIGURAÇÃO DATAJUD (MANTIDO) ---
DATAJUD_API_KEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

@app.get("/investigar/processo/{numero_processo}", tags=["Investigação"])
def consultar_processo_datajud(numero_processo: str):
    numero_limpo = "".join(filter(str.isdigit, numero_processo))
    url = "https://api-publica.datajud.cnj.jus.br/api_publica_tjsp/_search" # Exemplo TJSP
    
    headers = {
        "Authorization": f"APIKey {DATAJUD_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {"query": {"term": {"numeroProcesso": numero_limpo}}}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Erro no DataJud")

        dados = response.json()
        hits = dados.get("hits", {}).get("hits", [])
        
        if not hits:
            raise HTTPException(status_code=404, detail="Processo não encontrado.")

        processo_info = hits[0].get("_source", {})
        
        return {
            "status": "sucesso",
            "metadados": {
                "numero": processo_info.get("numeroProcesso"),
                "classe": processo_info.get("classe", {}).get("nome"),
                "tribunal": processo_info.get("tribunal"),
                "assuntos": [a.get("nome") for a in processo_info.get("assuntos", [])],
                "ultimas_movimentacoes": processo_info.get("movimentos", [])[:3]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4000)