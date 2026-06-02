# 🎬 First Run Guide

Guide détaillé pour premier démarrage Phase 1.

---

## 📋 Avant de Commencer

### Vérifications système
```bash
# Vérifier Docker
docker --version
docker compose --version

# Vérifier GPU NVIDIA
nvidia-smi

# Vérifier espace disque (besoin 50 Go)
df -h .
```

### Fichiers nécessaires
```
local-ai-assistant/
├── Dockerfile               ✓
├── docker-compose.yml       ✓
├── main.py                  ✓
├── inference.py             ✓
├── memory.py                ✓
├── config.py                ✓
├── requirements.txt         ✓
└── .env.example             ✓
```

Tous fournis ✅

---

## 🚀 Phase 1 : Configuration initiale (5 min)

### Étape 1.1 : Créer répertoires

```bash
mkdir -p models data documents logs
ls -la
```

Expected output :
```
drwxr-xr-x  models/
drwxr-xr-x  data/
drwxr-xr-x  documents/
drwxr-xr-x  logs/
```

### Étape 1.2 : Configurer .env

```bash
# Copier template
cp .env.example .env

# Vérifier (defaults sont OK)
cat .env | grep -v ^#
```

Si tu veux tweaker :
```bash
# Éditer
nano .env

# Ou directement :
export DEBUG=true
export LOG_LEVEL=DEBUG
```

### Étape 1.3 : Build Docker

```bash
# Build image
docker compose build

# Cela va :
# 1. Télécharger Ubuntu 24.04 base image
# 2. Installer Python 3.11, CUDA support
# 3. Installer dépendances (pip install -r requirements.txt)
# 4. Préparer application

# Time: ~3-5 minutes (dépend connection internet)
```

---

## 🔧 Phase 2 : Démarrage container (30-45 sec)

### Étape 2.1 : Lancer service

```bash
# Démarrer en background
docker compose up -d

# Ou en foreground pour voir les logs :
# docker compose up

# Wait ~10 sec pour stabilisation
```

### Étape 2.2 : Vérifier status

```bash
# Voir containers en cours
docker compose ps

# Expected :
# NAME          STATUS
# local-ai      Up X seconds
```

### Étape 2.3 : Voir les logs

```bash
# Derniers 50 lignes
docker compose logs local-ai -n 50

# Follow en temps réel
docker compose logs -f local-ai
```

Expected logs :
```
INFO: ========== STARTING LOCAL AI ASSISTANT ==========
INFO: ✓ Memory manager initialized
INFO: ✓ Inference engine initialized (lazy load)
INFO: ========== ✓ APPLICATION READY ==========
INFO: ✓ API listening on 0.0.0.0:8000
```

---

## 🧠 Phase 3 : Model Loading (20-40 sec, une fois seulement)

⚠️ **Premier `infer` trigger le téléchargement modèle**

### Étape 3.1 : Health check

```bash
# Vérifier que API respond
curl -s http://localhost:8000/health | python -m json.tool

# Expected :
{
  \"status\": \"healthy\",
  \"services\": {
    \"memory\": true,
    \"inference\": true,
    \"gpu\": true
  },
  \"resources\": {
    \"vram_used_mb\": 100,
    \"vram_total_mb\": 6144
  }
}
```

### Étape 3.2 : Trigger model download (optionnel)

```bash
# Première inférence chargera le modèle
# Cela peut prendre 2-5 minutes (dépend connection)
# Modèle ~3-4 Go

curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Bonjour"}'

# Voir logs pendant téléchargement
docker compose logs -f local-ai
```

Expected logs :
```
INFO: Downloading model: https://huggingface.co/...
INFO: Destination: ./models/qwen2.5-7b-instruct-q4_k_m.gguf
INFO: Model file found
INFO: ✓ Model loaded successfully in 28.5s
```

### Étape 3.3 : Vérifier téléchargement

```bash
# Check fichier dans container
docker compose exec local-ai ls -lh /app/models/

# Ou directement :
ls -lh models/

# Expected : ~5 Go
# -rw-r--r-- 4.9G qwen2.5-7b-instruct-q4_k_m.gguf
```

---

## ✅ Phase 4 : First Inference (15-30 sec)

### Étape 4.1 : Test simple

```bash
# Requête basique
curl -X POST http://localhost:8000/infer \\
  -H \"Content-Type: application/json\" \\
  -d '{
    \"prompt\": \"Salut, comment ca va?\",
    \"max_tokens\": 256
  }' | python -m json.tool
```

Expected response :
```json
{
  \"text\": \"Bonjour! Je vais bien, merci de demander. Comment puis-je t'aider aujourd'hui?\",
  \"tokens_used\": 28,
  \"model\": \"qwen-2.5-7b\",
  \"latency_ms\": 18200,
  \"timestamp\": \"2024-06-01T12:34:56\",
  \"user_id\": \"default\"
}
```

### Étape 4.2 : Test avec contexte

```bash
# Première question
curl -X POST http://localhost:8000/infer \\
  -H \"Content-Type: application/json\" \\
  -d '{\"prompt\": \"Qu est-ce que Python?\", \"max_tokens\": 512}'

# Deuxième question (contexte inclus)
curl -X POST http://localhost:8000/infer \\
  -H \"Content-Type: application/json\" \\
  -d '{\"prompt\": \"Est-ce difficile à apprendre?\", \"max_tokens\": 512}'

# La deuxième réponse contient le contexte de la première
```

### Étape 4.3 : Vérifier mémoire

```bash
# Historique conversations
curl -s http://localhost:8000/history | python -m json.tool

# Expected : les 2 messages stockés
```

---

## 🌐 Phase 5 : Access API Documentation

**Ouvrir navigateur** :

- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

Tu peux tester tous les endpoints directement dans le navigateur!

---

## 📊 Phase 6 : Monitoring (optionnel)

### Vérifier ressources

```bash
# VRAM usage
nvidia-smi

# Expected : ~5.5-5.8 Go utilisé après model load

# RAM usage
docker stats local-ai

# Expected : ~3-4 Go

# Logs application
docker compose logs local-ai | tail -20
```

### Stats application

```bash
curl -s http://localhost:8000/info | python -m json.tool

# Voir :
# - memory stats (conversations stored)
# - inference stats (model info)
# - gpu stats (VRAM usage)
```

---

## 🎯 Success Criteria

✅ Phase 1 réussi si :

- [x] `docker compose ps` montre container UP
- [x] `curl http://localhost:8000/health` répond 200
- [x] `/infer` endpoint génère réponses
- [x] Conversations sont stockées en SQLite
- [x] VRAM ~5.5-5.8 Go
- [x] Latence ~15-30 sec (acceptable)

---

## ⚠️ Troubleshooting

### Container ne démarre pas

```bash
# Voir erreur
docker compose logs local-ai

# Relancer avec debug
docker compose down
DEBUG=true docker compose up local-ai
```

### Model download échoue

```bash
# Vérifier connection internet
ping huggingface.co

# Vérifier URL modèle
curl -I https://huggingface.co/.../qwen2.5-7b-instruct-q4_k_m.gguf

# Télécharger manuellement :
cd models
curl -L -o qwen2.5-7b-instruct-q4_k_m.gguf \\
  \"https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf\"
```

### VRAM error

```bash
# Si \"CUDA out of memory\"
# RTX 2060 est au limite (6 Go)

# Option 1 : Réduire context size
export N_CTX=1024  # was 2048

# Option 2 : Utiliser modèle plus petit
# Qwen-3B instead of 7B

docker compose down
docker compose build
docker compose up -d
```

### API timeout

```bash
# Inférence peut prendre 20-40s
# C'est normal (RTX 2060 est lent)

# Augmenter timeout curl :
curl --max-time 60 http://localhost:8000/health
```

---

## 🎉 Prochaines étapes

Une fois Phase 1 stable :

1. ✅ **Phase 1 OK?** Continue à tester endpoints
2. 📖 **Lire README.md** pour API details
3. 🏗️ **Lire ARCHITECTURE.md** pour design decisions
4. 🔧 **Lire DEVELOP.md** pour dev/debug tips
5. 🚀 **Phase 2** : Discord bot integration

---

## 📞 Help

Si tu as des questions:

1. Check logs : `docker compose logs local-ai`
2. Check config : `cat .env | grep -v ^#`
3. Check API : `http://localhost:8000/docs`
4. Check hardware : `nvidia-smi` + `free -h`

---

**Ready to deploy Phase 1!** 🚀
