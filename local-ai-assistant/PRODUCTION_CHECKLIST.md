# 📋 DEPLOYMENT CHECKLIST - Final Verification

Avant de lancer Phase 1 en production, vérifier tous ces points.

---

## 🔍 PRE-DEPLOYMENT CHECKS

### Système hôte (Ubuntu Server)

- [ ] Ubuntu 24.04 LTS installé
- [ ] Espace disque ≥ 50 Go libres (`df -h /`)
- [ ] Connexion internet stable
- [ ] Utilisateur a accès sudo

### Hardware (RTX 2060)

- [ ] GPU NVIDIA détecté (`lspci | grep NVIDIA`)
- [ ] Drivers NVIDIA 550+ installés (`nvidia-smi` fonctionne)
- [ ] GPU visible dans Docker (`docker run --gpus all nvidia/cuda nvidia-smi`)

### Logiciels

- [ ] Docker installé (`docker --version`)
- [ ] Docker Compose installé (`docker compose version`)
- [ ] Git installé (`git --version`)
- [ ] Python 3.11 en download (sera dans Docker)

---

## 📦 CODE & CONFIGURATION

### Fichiers critiques présents

- [ ] `Dockerfile`
- [ ] `docker-compose.yml`
- [ ] `main.py`
- [ ] `inference.py`
- [ ] `memory.py`
- [ ] `config.py`
- [ ] `requirements.txt`
- [ ] `.env.example`
- [ ] `README.md`
- [ ] `INSTALL.md`

### Configuration

- [ ] `.env` créé (copié de `.env.example`)
- [ ] `N_GPU_LAYERS=20` (safe pour RTX 2060)
- [ ] `N_CTX=1024` (stable)
- [ ] Autres variables OK

### Répertoires

- [ ] `models/` créé (modèles GGUF)
- [ ] `data/` créé (SQLite DB)
- [ ] `documents/` créé (docs Phase 3)
- [ ] `logs/` créé (application logs)

---

## 🐳 DOCKER BUILD

### Build phase

- [ ] `docker compose build` réussi sans erreur
- [ ] Image built: `docker images | grep local-ai`
- [ ] Image size reasonable (~2-3 GB)

### Runtime phase

- [ ] `docker compose up -d` démarre
- [ ] Container visible: `docker compose ps` → **Up**
- [ ] Logs clean: `docker compose logs local-ai` (pas d'erreur)
- [ ] Container accessible: `docker exec local-ai ls /app/main.py` OK

---

## 🧪 API TESTING

### Health & Info

- [ ] Health check répond:
  ```bash
  curl http://localhost:8000/health
  # → {"status": "healthy", ...}
  ```

- [ ] Info endpoint répond:
  ```bash
  curl http://localhost:8000/info
  # → {"app": {...}, "config": {...}, ...}
  ```

### Inférence (Critical!)

- [ ] Première inférence OK:
  ```bash
  curl -X POST http://localhost:8000/infer \
    -d '{"prompt": "test"}'
  # → {"text": "...", "tokens_used": ..., ...}
  ```

- [ ] Modèle téléchargé:
  ```bash
  ls -lh models/qwen2.5-7b-instruct-q4_k_m.gguf
  # → ~5 Go file
  ```

- [ ] Deuxième inférence rapide (~20-40s):
  ```bash
  curl -X POST http://localhost:8000/infer \
    -d '{"prompt": "test2"}'
  # → Répond rapidement
  ```

### Memory

- [ ] History endpoint OK:
  ```bash
  curl http://localhost:8000/history
  # → [{"role": "user", "content": ...}, ...]
  ```

- [ ] Database créée:
  ```bash
  ls -lh data/memory.db
  # → SQLite file exists
  ```

---

## 🖥️ RESOURCES MONITORING

### VRAM

- [ ] After model load:
  ```bash
  nvidia-smi
  # → ~3.0-3.5 Go utilisé (20 layers GPU)
  ```

- [ ] No CUDA errors in logs
- [ ] Temperature normal (< 75°C)

### RAM

- [ ] System RAM utilization < 50%
- [ ] Container RAM < 10 Go

### CPU

- [ ] CPU usage reasonable during inference
- [ ] No overheating

---

## 🔄 OPERATIONS

### Start/Stop

- [ ] Start: `docker compose up -d` ✓
- [ ] Stop: `docker compose down` ✓
- [ ] Restart: `docker compose restart` ✓
- [ ] Logs: `docker compose logs -f` ✓

### Data Persistence

- [ ] Data survives restart:
  ```bash
  curl http://localhost:8000/history  # Get count
  docker compose restart
  curl http://localhost:8000/history  # Same count
  ```

---

## 🔐 SECURITY & BEST PRACTICES

- [ ] `.env` NOT committed to git
- [ ] `.gitignore` includes `models/`, `data/`, `logs/`, `.env`
- [ ] API not exposed to internet (firewall)
- [ ] SSH key auth only (no passwords)
- [ ] Logs contain no credentials
- [ ] Database backups planned (Phase 2)

---

## 📊 DOCUMENTATION

- [ ] README.md up-to-date
- [ ] INSTALL.md covers all steps
- [ ] DEPLOY_QUICK.md available
- [ ] Endpoint documentation clear
- [ ] Troubleshooting section complete

---

## ✅ FINAL APPROVAL

### Sign-off

- [ ] All checks passed
- [ ] API responding correctly
- [ ] GPU properly offloading
- [ ] No crashes or memory leaks
- [ ] Ready for Phase 2

### Go-Live Decision

- **Date**: ___________________
- **Verified by**: ___________________
- **Notes**: ___________________

---

## 📞 EMERGENCY CONTACTS

If issues occur:

1. Check logs first:
   ```bash
   docker compose logs local-ai | tail -100
   ```

2. Check GPU:
   ```bash
   nvidia-smi
   ```

3. Check network:
   ```bash
   curl http://localhost:8000/health
   ```

4. Full restart:
   ```bash
   docker compose down
   docker compose up -d
   sleep 10
   docker compose ps
   ```

---

## 📋 COPY THIS CHECKLIST

Print or copy this checklist and go through each item before declaring Phase 1 production-ready.

**Phase 1 Status**: [ ] Development [ ] Testing [ ] Production ✅

---

**Last Updated**: Phase 1 Complete (June 1, 2026)
