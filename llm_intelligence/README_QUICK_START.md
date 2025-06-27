# 🚀 LLM Intelligence System - Quick Start Guide

## 📋 Avvio Rapido

### 1. Avvia il Server API

```bash
# Opzione A: Usa il launcher script (raccomandato)
cd llm_intelligence
./start_server.sh

# Opzione B: Avvio manuale
python3 test_server.py --port 8055

# Opzione C: Usa una porta diversa se 8055 è occupata
./start_server.sh 8056
```

### 2. Apri la Dashboard

```bash
# Apri nel browser
firefox dashboard/realtime_dashboard.html
# oppure
google-chrome dashboard/realtime_dashboard.html
# oppure visita: http://localhost:8055/
```

### 3. Testa gli Endpoint API

```bash
# Test automatico di tutti gli endpoint
python3 test_api.py

# Test manuale di endpoint specifici
curl http://localhost:8055/rankings
curl http://localhost:8055/recommendations
curl http://localhost:8055/health
```

## 🔗 Endpoint API Disponibili

| Endpoint | Descrizione |
|----------|-------------|
| `GET /` | Informazioni API e lista endpoint |
| `GET /health` | Health check del sistema |
| `GET /rankings` | Ranking modelli con filtri opzionali |
| `GET /rankings/top-free` | Top modelli free tier |
| `GET /rankings/best-value` | Modelli con miglior value (performance/costo) |
| `GET /providers/{model}` | Opzioni provider per modello specifico |
| `GET /recommendations` | Raccomandazioni di ottimizzazione costi |
| `GET /benchmarks` | Punteggi benchmark (HumanEval, MMLU, GSM8K) |

## 🎯 Esempi di Utilizzo

### Ranking Generale
```bash
curl "http://localhost:8055/rankings"
```

### Ranking per Coding
```bash
curl "http://localhost:8055/rankings?use_case=coding&limit=5"
```

### Solo Modelli Free Tier
```bash
curl "http://localhost:8055/rankings?has_free_tier=true"
```

### Provider per Claude 3.5 Sonnet
```bash
curl "http://localhost:8055/providers/claude-3.5-sonnet"
```

### Raccomandazioni per $150/mese
```bash
curl "http://localhost:8055/recommendations?current_usage_usd=150"
```

## 🛠️ Risoluzione Problemi

### Errore: "Port already in use"
```bash
# Trova il processo che usa la porta
lsof -i :8055

# Uccidi il processo se necessario
kill -9 <PID>

# Oppure usa una porta diversa
./start_server.sh 8056
```

### Errore: "Python not found"
```bash
# Installa Python 3
sudo apt update
sudo apt install python3 python3-pip

# Verifica versione
python3 --version
```

### Dashboard non si carica
1. Verifica che il server sia in esecuzione: `curl http://localhost:8055/health`
2. Controlla che la porta nella dashboard sia corretta (8055)
3. Usa un browser moderno con JavaScript abilitato

## 📊 Features della Dashboard

- **🏆 Model Rankings**: Top modelli con punteggi in tempo reale
- **📈 Performance vs Cost**: Grafico scatter per visualizzare valore
- **💡 Cost Optimization**: Raccomandazioni intelligenti per risparmiare
- **🔧 Provider Health**: Status dei provider (Vertex AI, GitHub, OpenRouter)
- **🆓 Free Tier Models**: Lista modelli gratuiti disponibili
- **🎯 Benchmark Leaderboard**: Performance su coding, reasoning, math
- **⚡ Auto Refresh**: Aggiornamento automatico ogni 30 secondi

## 🎮 Dati Mock Disponibili

Il server di test include dati realistici per:
- **5 modelli** (Claude 3.5 Sonnet, GPT-4o, DeepSeek R1, Claude Haiku, Qwen Coder)
- **3 provider** (Anthropic, OpenAI, OpenRouter)
- **3 categorie benchmark** (Coding, Reasoning, Math)
- **2 modelli free tier** (DeepSeek R1, Qwen Coder)
- **Raccomandazioni intelligenti** basate su costi e performance

## 🔄 Integrazione con Sistema Esistente

Per integrare con il rate_limiting_router esistente:

```python
from llm_intelligence.integration.intelligent_routing_enhancement import IntelligentRoutingEnhancement

# Sostituisci il router esistente
router = IntelligentRoutingEnhancement(intelligence_api_url="http://localhost:8055")

# Usa routing intelligente
decision = await router.route_request('claude-3.5-sonnet', request_body)
```

## ✅ Verifica Installazione

```bash
# 1. Test server
python3 test_api.py

# 2. Verifica endpoint
curl -s http://localhost:8055/health | python3 -m json.tool

# 3. Test dashboard
# Apri http://localhost:8055/ nel browser
```

Se tutti i test passano, il sistema è pronto per l'uso! 🎉