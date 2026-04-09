from flask import Flask, jsonify
import os
import time

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({
        "status": "online",
        "agente": "IA Investigativa",
        "database": os.getenv('DB_HOST')
    })

if __name__ == '__main__':
    # '0.0.0.0' faz o Flask ouvir todas as interfaces do container
    app.run(host='0.0.0.0', port=5000)