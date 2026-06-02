# 🚀 Quick Deploy Guide - Ubuntu Server → Phase 1 Live

**TL;DR** : 30 minutes pour aller de serveur vierge à Phase 1 operational.

---

## 📋 Vérification rapide (5 min)

```bash
# Sur ton serveur Ubuntu 24 LTS vierge

# Check GPU
lspci | grep NVIDIA
# Expected: RTX 2060

# Check disque
df -h /  # Besoin 50+ Go

# Check internet
ping google.com
```

---

## 🔧 Installation rapide (20 min)

### **Copier ce exactement en terminal** (une commande à la fois) :

```bash
# 1. Update système
sudo apt update && sudo apt upgrade -y

# 2. Installer packages critiques
sudo apt install -y curl wget git build-essential gnupg lsb-release python3

# 3. Ajouter repo Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 4. Installer Docker
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 5. Configurer Docker pour user courant
sudo usermod -aG docker $USER
newgrp docker

# 6. Vérifier Docker
docker --version
docker compose version

# 7. ⚠️ NVIDIA drivers (va rebooter!)
sudo apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/3bf863cc.pub
sudo add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/ /"
sudo apt update
sudo apt install -y nvidia-driver-550
sudo reboot
```

**Après reboot, vérifier GPU** :

```bash
nvidia-smi
# Expected: RTX 2060, driver 550+

# Test Docker + GPU
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
```

---

## 📦 Copier et lancer code (5 min)

```bash
# 1. Créer répertoire
mkdir -p ~/ai-assistant
cd ~/ai-assistant

# 2. Créer structure répertoires
mkdir -p models data documents logs

# 3. COPIER FICHIERS (depuis ta machine locale)
# ============================================
# OPTION A: Via SCP (SSH copy)
# Sur ta machine locale:
scp -r /Users/bullestico/Documents/42/RANK05/MIA/local-ai-assistant/* user@IP_SERVEUR:~/ai-assistant/

# OPTION B: Via SFTP/Filezilla
# - Transfer les fichiers .py, docker-compose.yml, requirements.txt, etc

# OPTION C: Via Git
git clone <repo> ~/ai-assistant

# 4. Sur serveur, vérifier fichiers copiés
cd ~/ai-assistant
ls -la *.py *.yml

# 5. Setup .env
cp .env.example .env
# Vérifier N_GPU_LAYERS=20 et N_CTX=1024

# 6. Build image
docker compose build

# 7. Lancer
docker compose up -d

# 8. Vérifier
sleep 5
docker compose ps
curl http://localhost:8000/health

# 9. ⏳ Première inférence (va télécharger modèle ~3-4 Go, 2-5 min)
curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Bonjour"}' | python3 -m json.tool

# 10. Monitor while downloading
docker compose logs -f local-ai
```

---

## ✅ Checklist déploiement

- [ ] Ubuntu 24 LTS installé
- [ ] `nvidia-smi` affiche RTX 2060
- [ ] `docker --version` OK
- [ ] Code copié dans `~/ai-assistant/`
- [ ] `.env` créé avec N_GPU_LAYERS=20
- [ ] `docker compose build` réussi
- [ ] `docker compose ps` affiche container UP
- [ ] `curl /health` répond 200
- [ ] Modèle téléchargé et premier `/infer` OK

---

## 📊 Monitoring

```bash
# Logs en temps réel
docker compose logs -f local-ai

# GPU usage
nvidia-smi -l 1

# Container stats
docker stats local-ai

# API Test
curl http://localhost:8000/health | python3 -m json.tool
curl http://localhost:8000/info | python3 -m json.tool
```

---

## 🐛 Dépannage rapide

| Problème | Solution |
|----------|----------|
| GPU non détecté | Vérifier BIOS, reconnecter GPU physiquement |
| nvidia-smi fail | Redémarrer après driver install : `sudo reboot` |
| Docker permission denied | `newgrp docker` ou logout/login |
| Docker build fail | `docker compose build --no-cache` |
| CUDA out of memory | Réduire N_GPU_LAYERS=15 dans .env |
| API not responding | `docker compose logs local-ai` |
| Model won't download | Vérifier internet : `ping huggingface.co` |

---

## 🎉 Succès!

Si tu vois:
- ✅ `docker compose ps` → **Up**
- ✅ `curl /health` → **healthy**
- ✅ `nvidia-smi` → **3.0-3.5 Go VRAM utilisé**
- ✅ `/infer` → **réponse JSON**

**Phase 1 is LIVE!** 🚀

---

## 📖 Documentation complète

- **INSTALL.md** : Guide détaillé complet
- **README.md** : API endpoints + troubleshooting
- **FIRST_RUN.md** : Explications pour développeurs

---

**Prêt?** 🚀 Go sur ton serveur!
