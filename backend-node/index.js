const express = require('express');
const app = express();

app.get('/', (req, res) => {
  res.json({ status: "online", message: "API Investigativa pronta para rodar!" });
});

app.listen(4000, '0.0.0.0', () => {
  console.log('🚀 Backend Node rodando na porta 4000');
});