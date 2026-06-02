# 🔧 Development Guide - Phase 1

Guide complet pour développeurs / admins.

---

## 📐 Architecture Détaillée

### Data Flow

```
┌─────────────────────────────────────────────────────────┐
│ Client (curl, Discord bot, etc)                         │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP Request
                     ↓
┌─────────────────────────────────────────────────────────┐
│ FastAPI (main.py)                                       │
│ - Request validation (Pydantic)                         │
│ - Endpoint routing                                      │
│ - Error handling                                        │
└─────────────┬──────────────────────┬────────────────────┘
              │                      │
              ↓                      ↓
    ┌─────────────────┐   ┌──────────────────┐
    │ MemoryManager   │   │ InferenceEngine  │
    │ (memory.py)     │   │ (inference.py)   │
    │                 │   │                  │
    │ - Query history │   │ - Load model     │
    │ - Store results │   │ - Run inference  │
    │ - User metadata │   │ - Monitor VRAM   │
    └────────┬────────┘   └────────┬─────────┘
             │                     │
             ↓                     ↓
    ┌─────────────────┐   ┌──────────────────┐
    │ SQLite DB       │   │ llama.cpp (GPU)  │
    │ memory.db       │   │ Qwen-2.5-7B      │
    └─────────────────┘   └──────────────────┘
```

### Composants Principaux

#### 1. **main.py** (FastAPI Application)

```python
# Lifecycle
startup  → init memory + inference
endpoint → /health, /info, /infer, /history
shutdown → cleanup
```

- **Request/Response Validation** : Pydantic models
- **Error Handling** : HTTPException → JSON
- **Logging** : Chaque endpoint loggé

#### 2. **inference.py** (Moteur IA)

```python
# Lazy Loading Pattern
engine = InferenceEngine(model_path)
# Modèle pas chargé encore
result = engine.infer(prompt)
# ← MAINTENANT, le modèle se charge en VRAM
```

- **VRAM Monitoring** : nvidia-smi query
- **Model Downloading** : curl Hugging Face
- **Prompt Building** : Context + system prompt
- **Token Counting** : Estimation pour stats

**Qwen Format** :
```
[SYSTEM]
Tu es un assistant utile...
[/SYSTEM]

{conversation_context}

User: {prompt}
Assistant:
```

#### 3. **memory.py** (SQLite ORM)

**Tables** :
- `conversations` : Historique messages
- `user_metadata` : Infos utilisateur (language, stats)
- `document_index` : Index docs locales (Phase 3)

**Operandes** :
```python
memory.add_message(role, content, user_id)
memory.get_conversation_history(user_id, limit=50)
memory.get_conversation_context(user_id, max_tokens=2000)
memory.update_user_stats(user_id, tokens_used)
memory.archive_old_conversations(days=30)
```

#### 4. **config.py** (Configuration)

- **Pydantic BaseSettings** : Load from `.env`
- **Type Validation** : Tous les types validés
- **Defaults** : Valeurs par défaut sensibles

---

## 🧪 Testing & Development

### Unit Tests (Future)

```python
# tests/test_memory.py
def test_add_message():
    manager = MemoryManager(":memory:")  # SQLite RAM
    msg_id = manager.add_message("user", "Hello")
    assert msg_id > 0

# tests/test_inference.py
def test_inference():
    engine = InferenceEngine("./models/qwen.gguf")
    result = engine.infer("Test")
    assert "text" in result
```

### Manual Testing

```bash
# 1. Health check
curl -s http://localhost:8000/health | python -m json.tool

# 2. Info
curl -s http://localhost:8000/info | python -m json.tool

# 3. Inference
curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explique Python en 2 lignes",
    "max_tokens": 256,
    "user_id": "test_user"
  }' | python -m json.tool

# 4. History
curl -s "http://localhost:8000/history?user_id=test_user" | python -m json.tool

# 5. Clear history
curl -X DELETE "http://localhost:8000/history?user_id=test_user"
```

### Debug Logging

```bash
# Lancer avec DEBUG=true
docker compose down
DEBUG=true docker compose up local-ai

# Logs détaillés
docker compose logs -f local-ai | grep ERROR
docker compose logs -f local-ai | grep DEBUG
```

---

## 🔍 Monitoring & Performance

### Metrics Clés

```bash
# Depuis container
docker compose exec local-ai python -c "
from config import settings
from memory import init_memory
m = init_memory(settings.db_path)
print(m.get_stats())
"

# Output:
# {
#   'total_messages': 42,
#   'total_users': 1,
#   'total_tokens': 5000,
#   'db_size_mb': 0.5
# }
```

### VRAM Profile

```
Initial: ~0 MB
After model load: 5.5-5.8 Go
During inference: ~5.8 Go (peak)
```

### Latency Profile

```
Load model: 20-30s (une fois)
First inference: ~20s (model cache warm)
Subsequent: ~15-30s (dépend longueur réponse)
```

**Bottleneck** : Inférence GPU (séquentielle)

---

## 🚀 Production Checklist

- [ ] `.env` configured
- [ ] NVIDIA driver working
- [ ] Docker volumes mounted correctly
- [ ] Firewall rules (restrict port 8000 if public)
- [ ] Logging configured (rotation logs)
- [ ] Database backups setup
- [ ] Monitoring/alerting (optional)
- [ ] SSL/TLS (if exposed)

---

## 🔗 Integration Points (Phase 2+)

### Discord Bot

```python
# discord.py will connect to:
POST /infer

# With payload:
{
    "prompt": "user message",
    "user_id": "discord_user_id",
    "max_tokens": 512
}
```

### Web Search (Phase 3)

```python
# Will add to inference.py:
# - DuckDuckGo API calls
# - URL fetching
# - Content parsing

# New endpoint:
POST /search
{
    "query": "search term"
}
```

### Document RAG (Phase 3)

```python
# Will use:
# - LlamaIndex for chunking
# - FAISS for embeddings
# - Local vector store

# New endpoint:
POST /search_documents
{
    "query": "question about docs",
    "top_k": 3
}
```

---

## 📝 Code Style & Standards

### Python

- **Formatting** : Black (optionnel)
- **Linting** : Flake8 (optionnel)
- **Type Hints** : Obligatoire pour nouvelles fonctions
- **Docstrings** : Format numpy ou Google

### Comments

```python
# Commentaires pour logic complexe
# 1-2 lignes par bloc

def complex_function():
    """Docstring pour contexte global."""
    # Explication logique ici
    x = y + z
```

### Git

```bash
git add .
git commit -m "feat: add feature X

- Detail 1
- Detail 2"
```

---

## 🐛 Common Issues & Solutions

### Issue: Model won't download

```bash
# Solution: Manual download
cd models
curl -L -o qwen2.5-7b-instruct-q4_k_m.gguf \
  "https://huggingface.co/.../resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf"
```

### Issue: VRAM OOM

```bash
# Reduce context window in .env
N_CTX=1024  # was 2048

# Or use smaller model
# Use Qwen-3B instead
```

### Issue: Slow inference

```bash
# This is expected (~15-30s)
# Can't optimize much on RTX 2060
# Increase n_batch won't help (VRAM limited)
```

### Issue: Database locked

```bash
# SQLite contention
# Solution: Close all connections
docker compose restart

# Check who locks:
lsof | grep memory.db
```

---

## 📚 Resources

- **llama.cpp** : https://github.com/ggerganov/llama.cpp
- **Qwen Model** : https://huggingface.co/Qwen
- **FastAPI** : https://fastapi.tiangolo.com/
- **SQLAlchemy** : https://docs.sqlalchemy.org/
- **Docker** : https://docs.docker.com/

---

## 🎯 Performance Optimization Roadmap

Phase 1 (Done):
- ✅ GPU acceleration (33 layers)
- ✅ Q4 quantization (VRAM savings)
- ✅ Lazy model loading
- ✅ Single-threaded inference

Phase 2 (Future):
- [ ] Request queuing
- [ ] Response streaming
- [ ] Prompt caching
- [ ] Batch inference (if needed)

Phase 3+ (Advanced):
- [ ] Fine-tuning on custom data
- [ ] Multi-model inference
- [ ] vLLM integration (higher throughput)
- [ ] Distributed inference (multiple GPUs)

---

**Last Updated**: Phase 1 Complete
