# 🤖 Local AI Assistant - Phase 1

Assistant IA personnel local sur serveur Ubuntu, hebergé en Docker.

**Status**: Phase 1 - Infrastructure Core ✅

---

## 📋 Spécifications

| Composant | Valeur |
|-----------|--------|
| **Hardware** | AMD Ryzen 7 3700X, RTX 2060 6 Go, 16 Go RAM |
| **OS** | Ubuntu Server 24 LTS |
| **Modèle IA** | Qwen 2.5 7B (Q4 GGUF) |
| **Framework Inférence** | llama.cpp |
| **API** | FastAPI + Uvicorn |
| **Mémoire** | SQLite (conversations + metadata) |
| **Orchestration** | Docker Compose |

---

## 🚀 Quick Start

### Prérequis

```bash
# Vérifier Docker installé
docker --version
docker compose --version

# Cloner/copier le repo
cd /chemin/vers/local-ai-assistant
```

### 1️⃣ Configuration

```bash
# Copier template env
cp .env.example .env

# Éditer .env si besoin (optionnel, defaults OK)
nano .env
```

### 2️⃣ Build & Start

```bash
# Build image Docker
docker compose build

# Lancer le service (sera long première fois = téléchargement modèle)
docker compose up -d

# Vérifier status
docker compose ps
docker compose logs -f local-ai
```

**Première démarrage** : 
- ⏳ Téléchargement modèle Qwen (3-4 Go) : ~2-5 minutes
- ⏳ Chargement modèle VRAM : ~20-30 secondes
- ✅ Service prêt après

### 3️⃣ Premier test

```bash
# Health check
curl -X GET http://localhost:8000/health

# Inférence simple
curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Bonjour, comment tu t'\''appelles ?",
    "max_tokens": 256
  }'
```

✅ Si tu vois une réponse JSON avec le texte IA, c'est bon !

---

## 📡 API Endpoints (Phase 1)

### Health & Info

```bash
# Health check (statut services, VRAM)
GET /health

# Infos application
GET /info
```

### Inférence ⭐

```bash
# Lancer inférence
POST /infer

# Payload:
{
  "prompt": "Ta question ici",
  "max_tokens": 1024,              # Default: 1024
  "include_context": true,          # Include historique conversation
  "system_prompt": null,            # Custom system prompt (optionnel)
  "user_id": "default",             # User identifier
  "stream": false                   # Streaming (Phase 2)
}

# Response:
{
  "text": "Réponse IA",
  "tokens_used": 42,
  "model": "qwen-2.5-7b",
  "latency_ms": 3200,
  "timestamp": "2024-06-01T12:00:00",
  "user_id": "default"
}
```

### Mémoire

```bash
# Récupère historique conversations
GET /history?user_id=default&limit=50

# Efface historique utilisateur ⚠️
DELETE /history?user_id=default
```

---

## 📚 Documentation Interactive

API Swagger auto-générée :
- **Docs** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

Tester endpoints directement dans le navigateur !

---

## 🛠️ Gestion Container

```bash
# Voir logs en temps réel
docker compose logs -f local-ai

# Arrêter service
docker compose down

# Redémarrer
docker compose restart

# Entrer dans container
docker compose exec local-ai bash

# Nettoyer (supprimer containers + images)
docker compose down --rmi all
```

---

## 📊 Monitoring

### Vérifier utilisation ressources

```bash
# Dans container
docker compose exec local-ai python -c "
from config import settings, setup_logging
from inference import VRAMMonitor
import json
print(json.dumps(VRAMMonitor.get_vram_usage(), indent=2))
"

# VRAM doit être ~5.5-5.8 Go (modèle + inférence)
```

### Logs

```bash
# Application logs
docker compose logs local-ai

# Logs fichier (dans container)
docker compose exec local-ai tail -f /app/logs/app.log
```

---

## 🔧 Architecture Fichiers

```
local-ai-assistant/
├── main.py              # FastAPI application (core)
├── inference.py         # llama.cpp integration + modèle
├── memory.py            # SQLite ORM + conversation storage
├── config.py            # Configuration centralisée
├── Dockerfile           # Image Docker
├── docker-compose.yml   # Orchestration
├── requirements.txt     # Dépendances Python
├── .env.example         # Template variables env
├── .env                 # Actual config (à créer)
│
├── models/              # (Volume Docker) Modèles GGUF
├── data/                # (Volume Docker) SQLite DB + metadata
├── documents/           # (Volume Docker) Docs locales (Phase 3)
└── logs/                # (Volume Docker) Application logs
```

---

## 🎯 Performance Expectations (RTX 2060)

### Avec GPU/CPU Offloading (Recommandé)

| Métrique | Valeur | Notes |
|----------|--------|-------|
| **Temps chargement modèle** | 20-30s (une fois) | RAM + VRAM |
| **Latence inférence** | 20-40s (réponse complète) | GPU + CPU hybrid |
| **Speed** | ~20-35 tokens/sec | Ralenti par CPU layers |
| **VRAM utilisée** | 3.0-3.5 Go | Seulement ~20 layers sur GPU |
| **RAM utilisée** | 4-6 Go | Layers CPU offloadés |
| **Batch size** | 1 (pas de concurrence) | Sequential seulement |
| **Stabilité** | ✅ Très stable | Pas de CUDA OOM |

### Configuration par défaut (N_GPU_LAYERS=20)

```
Qwen-2.5-7B (33 layers total)
├── Layers 0-19 : GPU (VRAM ~3.0 Go, rapide)
└── Layers 20-32: CPU RAM (lent, mais libère VRAM)
```

⚠️ **Comprendre le trade-off** :
- ✅ **Stable** : N_GPU_LAYERS=20 → Pas de crash CUDA
- ⚠️ **Rapide** : N_GPU_LAYERS=25+ → Risque CUDA OOM avec contexte long
- 🐢 **CPU only** : N_GPU_LAYERS=0 → Très lent (~5+ min/réponse)

---

## 🐛 Troubleshooting

### Modèle ne se télécharge pas

```bash
# Vérifier URL modèle
curl -I https://huggingface.co/.../qwen2.5-7b-instruct-q4_k_m.gguf

# Télécharger manuellement et placer dans ./models/
```

### "CUDA out of memory"

**Cause** : RTX 2060 (6 Go VRAM) est au limite. Tous les 33 layers ne peuvent pas tenir en GPU.

**Solutions** (essayer dans l'ordre) :

1. **Réduire N_GPU_LAYERS** (MEILLEURE solution)
   ```bash
   # Dans .env :
   N_GPU_LAYERS=15  # Au lieu de 20
   # Cela offload plus de layers sur CPU RAM (plus lent mais stable)
   ```

2. **Réduire N_CTX** (context window)
   ```bash
   N_CTX=512  # Au lieu de 1024
   # Moins d'historique = moins de VRAM
   ```

3. **Utiliser modèle plus petit**
   ```bash
   # Remplacer Qwen-2.5-7B par Qwen-3B (plus compact)
   # Dans config.py : model_name = "Qwen3B"
   ```

4. **CPU only** (dernier recours)
   ```bash
   N_GPU_LAYERS=0
   # ⚠️ Très lent (~5+ minutes par réponse)
   ```

**Comprendre GPU offloading** :
- N_GPU_LAYERS=33 : Tous les layers sur GPU → Rapide mais CUDA OOM
- N_GPU_LAYERS=20 : 20 GPU + 13 CPU → Équilibré (défaut)
- N_GPU_LAYERS=15 : 15 GPU + 18 CPU → Sûr, plus lent
- N_GPU_LAYERS=0 : CPU seulement → Très lent

### Container crashes

```bash
# Voir error logs
docker compose logs local-ai | tail -50

# Redémarrer avec debug
docker compose up local-ai (sans -d)
```

### VRAM pas détectée

```bash
# Vérifier NVIDIA driver dans container
docker compose exec local-ai nvidia-smi

# Si ne marche pas:
# - NVIDIA drivers sur host non installés
# - Docker sans --gpus flag
```

---

## 📈 Roadmap

- **Phase 1** ✅ : Infrastructure core (api, memory, inférence)
- **Phase 2** : Discord bot integration
- **Phase 3** : RAG + document search + web search
- **Phase 4** : Code analysis + advanced features

---

## 🔐 Sécurité

### Bonnes pratiques en prod

```bash
# Ne jamais commiter .env
echo ".env" >> .gitignore

# Limiter API accès (firewall)
# iptables -A INPUT -p tcp --dport 8000 -j DROP

# Logs contiennent données sensibles
# Nettoyer régulièrement: docker compose exec local-ai rm /app/logs/app.log
```

### Variables sensibles

- Aucune clé API hardcodée en Phase 1
- Discord token → Phase 2

---

## 💡 Développement / Debug

### Mode développement

```bash
# Éditer Dockerfile pour:
# - Ajouter DEBUG=true
# - Ajouter ipython dans requirements.txt
# - Exposer ports supplémentaires (debugger)

docker compose exec local-ai bash
python
>>> from inference import InferenceEngine
>>> engine = InferenceEngine("./models/qwen...")
```

### Tests endpoints

```bash
# Installer tool testing (optionnel)
pip install httpie

# Test :
http POST localhost:8000/infer prompt="Test" max_tokens:=256
```

---

## 📝 Notes importantes

1. **Première démarrage lent** : normal, téléchargement + chargement modèle
2. **Pas de GPU** : setups CPU-only possibles (bien plus lent)
3. **Modèle quantifié** : Q4 = bon trade-off qualité/VRAM
4. **Conversations persistantes** : SQLite `/data/memory.db`

---

## 🤝 Support

- Logs → `/app/logs/app.log` (dans container)
- Swagger UI → http://localhost:8000/docs
- Logs détaillés → `LOG_LEVEL=DEBUG` dans .env

---

## 📄 License

Open Source - Libre d'utilisation personnelle

---

**Phase 1 Ready** ✅ - Infrastructure stablisée, prêt pour Phase 2 (Discord)
