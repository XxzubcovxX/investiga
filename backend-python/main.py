import time
import os

print("--- AGENTE DE IA INVESTIGATIVA ---")
print(f"Target DB: {os.getenv('DB_HOST')}")

try:
    # Aqui depois entrará a lógica dos Agentes (CrewAI/Gemini)
    while True:
        print("Agente Python em modo de escuta...")
        time.sleep(30)
except KeyboardInterrupt:
    print("Desligando agente...")
    