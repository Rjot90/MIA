# 🏗️ Architecture Decisions - Phase 1

Document les choix architecturaux et leurs justifications.

---

## 1. Framework Web : FastAPI vs Django/Flask

### Choix : **FastAPI** ✅

**Justifications** :
- **Async natif** : Support websockets (Discord)
- **Validation auto** : Pydantic (moins de boilerplate)
- **Performance** : Parmi les plus rapides Python
- **Documentation auto** : Swagger/ReDoc
- **Type hints** : Support Python 3.10+
- **Léger** : Pas de dépendances lourdes

**Alternatives évaluées** :
- Django : Trop heavy pour cette use case
- Flask : Manque async, validation faible
- Starlette : Trop bas niveau

---

## 2. Inférence : llama.cpp vs vLLM vs HF Transformers

### Choix : **llama.cpp** ✅

**Justifications** :
- **RTX 2060 compatible** : Conçu pour hardware limité
- **GGUF quantization** : Support natif Q4 (VRAM savings)
- **Standalone** : Pas de dépendances lourdes
- **Fast startup** : Model caching
- **Proven** : Utilisé production-wide
- **Binary executable** : Peut run outside Python

**Comparaisons** :

| Critère | llama.cpp | vLLM | Transformers |
|---------|-----------|------|-------------|
| VRAM minimal | ✅ Excellent | ❌ 8+ Go | ❌ 12+ Go |
| RTX 2060 | ✅ Yes | ❌ Tight | ❌ No |
| Throughput | ⚠️ Low (batch=1) | ✅ High | ✅ Medium |
| Quantization | ✅ Native | ❌ Limited | ⚠️ Plugin |
| Setup | ✅ Simple | ❌ Complex | ⚠️ Medium |

**Verdict** : Pour RTX 2060 + latency OK = llama.cpp optimal

---

## 3. Modèle : Qwen vs Mistral vs Llama vs Phi

### Choix : **Qwen-2.5-7B** ✅

**Justifications** :
- **Français** : Support natif, bien mieux que Mistral
- **Coding** : Exceptionnel pour code Python/JavaScript
- **Architecture efficace** : VRAM-optimized
- **Available Q4** : GGUF quantisé dispo
- **Reasoning** : Excellent pour logique
- **Open source** : Apache 2.0 license

**Modèles évaluées** :

| Modèle | VRAM Q4 | Français | Coding | Remarques |
|--------|---------|----------|--------|-----------|
| Qwen-2.5-7B | 5.5 Go | ✅ Excellent | ✅ Excellent | **BEST** |
| Mistral-7B | 5.0 Go | ⚠️ Ok | ✅ Good | Moins francophone |
| Llama-2-7B | 5.2 Go | ⚠️ Limited | ✅ Good | Dated, non libre |
| Phi-3.5-3.8B | 3.5 Go | ⚠️ Limited | ⚠️ Weak | Trop petit pour code |

**Budget VRAM** :
- Modèle quantifié : 5.5-5.8 Go
- Inférence overhead : +0.2-0.5 Go
- Total margin : ~6.0-6.2 Go (tight mais OK)

---

## 4. Base de Données : SQLite vs PostgreSQL

### Choix : **SQLite Phase 1, PostgreSQL Phase 2+** ✅

**Phase 1 : SQLite**

```
Avantages:
✅ Zéro setup (fichier local)
✅ Embedding facile (Docker volume)
✅ Sufficient pour solo user
✅ Queryable via CLI/Python

Limitations:
❌ Pas multi-writer concurrent (ok pour Phase 1)
❌ Pas networking (ok local)
```

**Phase 2+ : PostgreSQL**

```
Raison:
- Multi-user concurrent
- Network access (maybe API exposed)
- Better scaling
- Advanced features (JSON, full-text search)

Migration strategy:
1. Phase 1: SQLite
2. Phase 2: Dual-write (SQLite + PG)
3. Phase 3: Switch to PG, retire SQLite
```

---

## 5. Persistance Contexte : In-Memory vs Database

### Choix : **Database (SQLite)** ✅

**Justifications** :
- **Durability** : Conversations survivent crashes
- **Analytics** : Stats usage, patterns
- **Privacy** : Contrôle complet données
- **Future** : Easy archival/export
- **Cost** : SQLite free (contrairement OpenAI API)

**Alternative** :
- In-memory (Redis) : Perte données sur crash
- File-based (JSON) : Pas queryable

---

## 6. Streaming vs Buffered Responses

### Choix : **Buffered Phase 1, Streaming Phase 2** ⏳

**Phase 1 : Buffered (simple)**
```json
{
  "text": "Complete response",
  "latency_ms": 3200
}
```

**Phase 2 : Streaming (Discord)**
```
Server-Sent Events (SSE)
ou Websockets
```

**Raison du timing** :
- Phase 1 : API simple, tester logic
- Phase 2 : Discord needs streaming (latency perception)

---

## 7. Docker : Single Container vs Multi-Container

### Choix : **Single Container Phase 1** ✅

```yaml
# Phase 1 (current)
services:
  local-ai:
    - FastAPI
    - llama.cpp
    - SQLite
    - All in one
```

**Phase 2+ Evolution** :
```yaml
# Phase 2 (possible)
services:
  api:       # FastAPI only
  inference: # llama.cpp only
  db:        # PostgreSQL
  redis:     # Cache (optional)
```

**Justification** :
- Phase 1 : Single container = simpler deploy
- No inter-service latency issues
- All on same GPU anyway

---

## 8. Configuration : Environment Variables vs Config Files

### Choix : **Hybrid (both)** ✅

**Hierarchy** :
1. Environment variables (override all)
2. `.env` file (development)
3. Pydantic defaults (fallback)

**Example** :
```bash
# .env
N_GPU_LAYERS=33

# Override:
export N_GPU_LAYERS=20
docker compose up  # Uses 20, not 33
```

---

## 9. Logging : Structured vs Unstructured

### Choix : **Unstructured Phase 1, Structured Phase 2+** 📊

**Phase 1** :
```
[2024-06-01 12:00:00] INFO - Model loaded (5.5 Go)
```

**Phase 2+** :
```json
{
  "timestamp": "2024-06-01T12:00:00Z",
  "level": "INFO",
  "service": "inference",
  "message": "Model loaded",
  "metadata": {"vram_mb": 5500}
}
```

**Tools** : `loguru` (Phase 1), then `python-json-logger` (Phase 2)

---

## 10. Error Handling : Granular vs Generic

### Choix : **Granular** ✅

```python
# ✅ Good
raise HTTPException(
    status_code=503,
    detail="Model failed to load: VRAM insufficient"
)

# ❌ Bad
raise Exception("Error")
```

**Patterns** :
- Custom exceptions for app logic
- HTTPException for API responses
- Logging for debugging

---

## 11. Rate Limiting : Built-in vs External

### Choix : **None Phase 1, FastAPI-Limiter Phase 2** ⏳

**Phase 1** :
- Solo user
- No rate limits needed
- Single inference queue (by nature)

**Phase 2+** :
- Discord bot (many users)
- Need request queuing
- Implement queue with limits

---

## 12. Deployment : Docker Compose vs Kubernetes

### Choix : **Docker Compose (local server)** ✅

**Raison** :
- Single machine (AMD Ryzen 7 + RTX 2060)
- K8s overkill
- Docker Compose sufficient

**If scaling** :
- Multiple servers : K8s
- Multi-GPU : K8s + NVIDIA device plugin

---

## 13. GPU : NVIDIA only vs Multi-vendor

### Choix : **NVIDIA (CUDA) only Phase 1** ✅

**Justification** :
- RTX 2060 is NVIDIA
- llama.cpp has best CUDA support
- AMD ROCM not supported in llama.cpp yet

**Future** :
- If AMD GPU : Switch to HF Transformers or vLLM (ROCM)

---

## 14. Context Window : 2048 vs 4096

### Choix : **2048 (N_CTX=2048)** ✅

**Trade-offs** :

| Paramètre | 2048 | 4096 |
|-----------|------|------|
| VRAM | 5.5 Go | 6.2 Go ❌ |
| Latency | ~20s | ~40s |
| Context quality | Good | Better |

**Verdict** : 2048 = safety margin RTX 2060

---

## 15. Quantization : Q4 vs Q5 vs Q6

### Choix : **Q4 (Q4_K_M)** ✅

**Comparison** :

| Format | VRAM | Quality | Speed |
|--------|------|---------|-------|
| FP32 | 28 Go | Perfect | Slow |
| Q6 | 8 Go | Excellent | OK |
| Q5 | 7 Go | Very Good | Good |
| **Q4** | **5.5 Go** | **Good** | **Best** |

**Verdict** : Q4 = RTX 2060 sweet spot

---

## Architectural Principles

1. **Simplicity first** : YAGNI (You Ain't Gonna Need It)
2. **Hardware aware** : Decisions fit RTX 2060
3. **Open source** : No vendor lock-in
4. **Modular** : Easy to swap components
5. **Offline capable** : No cloud dependency
6. **Measurable** : Monitor latency/memory
7. **Testable** : Unit tests possible

---

## Trade-offs Matrix

| Decision | Latency | VRAM | Complexity | Cost |
|----------|---------|------|-----------|------|
| llama.cpp | Good | ✅ Best | Low | Free |
| Qwen-2.5-7B | Good | ✅ Best | Low | Free |
| Q4 quant. | ✅ Best | ✅ Best | Low | Free |
| SQLite | N/A | ✅ Best | ✅ Low | Free |
| Docker | Minimal | OK | ✅ Low | Free |
| FastAPI | ✅ Best | Low | ✅ Low | Free |
| Lazy load | ✅ | ✅ | Medium | Free |

**Total** : All trade-offs favor RTX 2060 + solo user

---

**Phase 1 Architecture Locked** ✅

Ready for Phase 2 (Discord integration)
