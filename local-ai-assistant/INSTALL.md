# 🚀 Installation Ubuntu Server 24 LTS - Serveur vierge

Guide complet pour installer tout depuis zéro sur un serveur sans rien.

**Durée estimée** : 30-45 minutes

---

## 📋 Prérequis

- Ubuntu Server 24 LTS (fresh install)
- Connexion internet
- RTX 2060 (GPU NVIDIA)
- Accès root/sudo

---

## 🎯 Étape 0 : Configuration initiale serveur

```bash
# Mettre à jour système
sudo apt update && sudo apt upgrade -y

# Vérifier architecture
uname -m  # Doit afficher: x86_64

# Vérifier espace disque
df -h /  # Besoin d'au moins 50 Go libres
```

---

## 🎯 Étape 1 : Installer dépendances système

```bash
# Installer packages critiques
sudo apt install -y \
  curl \
  wget \
  git \
  build-essential \
  ca-certificates \
  gnupg \
  lsb-release

# Vérifier
git --version
curl --version
```

---

## 🎯 Étape 2 : Installer Docker

Docker va embarquer Python 3.11 + tout ce qui faut dans le container.

```bash
# Ajouter repo Docker officiel
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Installer Docker + Docker Compose
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Permettre utilisateur courant utiliser Docker
sudo usermod -aG docker $USER
newgrp docker

# Vérifier installation
docker --version
docker compose version
```

---

## 🎯 Étape 3 : Installer NVIDIA drivers + CUDA support

**⚠️ CRITIQUE pour RTX 2060**

### 3.1 Vérifier NVIDIA GPU

```bash
# Lister GPU
lspci | grep NVIDIA

# Expected output:
# 01:00.0 VGA compatible controller: NVIDIA Corporation TU106 [GeForce RTX 2060 ...] (rev a1)
```

Si rien ne s'affiche → **GPU non détecté** (vérifier BIOS ou connexion physique)

### 3.2 Installer NVIDIA drivers

```bash
# Ajouter repo NVIDIA
sudo apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/3bf863cc.pub

sudo add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/ /"

sudo apt update

# Installer drivers (va reboot système)
sudo apt install -y nvidia-driver-550

# Reboot pour appliquer
sudo reboot

# Après reboot, vérifier
nvidia-smi

# Expected: Affiche GPU RTX 2060 + driver version
```

### 3.3 Installer CUDA toolkit (optionnel mais recommandé)

```bash
# Installer CUDA
sudo apt install -y cuda-toolkit

# Ajouter CUDA au PATH
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc

# Vérifier
nvcc --version
```

### 3.4 Test GPU Docker

```bash
# Tester accès GPU depuis Docker
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi

# Expected: Affiche GPU + utilisation (0 Mo utilisé)
```

---

## 🎯 Étape 4 : Préparer dossiers de travail

```bash
# Créer répertoire de travail
mkdir -p ~/ai-assistant
cd ~/ai-assistant

# Créer structure répertoires
mkdir -p models data documents logs

# Vérifier
ls -la

# Expected:
# drwxr-xr-x  data/
# drwxr-xr-x  documents/
# drwxr-xr-x  logs/
# drwxr-xr-x  models/
```

---

## 🎯 Étape 5 : Copier code depuis ta machine locale

**Option A : Via Git** (si repo disponible)

```bash
# Sur serveur
cd ~/ai-assistant
git clone <repo-url> .
```

**Option B : Via SFTP/SCP** (recommandé)

```bash
# Sur ta machine locale (macOS/Linux)
cd /Users/bullestico/Documents/42/RANK05/MIA/local-ai-assistant

# Envoyer tous les fichiers au serveur
scp -r * utilisateur@IP_SERVEUR:~/ai-assistant/

# Exemple concret:
scp -r * user@192.168.1.100:~/ai-assistant/
```

**Option C : Via USB/transfert manuel**

1. Zipper le dossier `local-ai-assistant` sur ta machine
2. Copier le .zip sur USB
3. Sur serveur: `unzip /mnt/usb/local-ai-assistant.zip -d ~/ai-assistant/`

### Vérifier transfert

```bash
# Sur serveur, vérifier fichiers copiés
cd ~/ai-assistant
ls -la

# Expected:
# -rw-r--r--  Dockerfile
# -rw-r--r--  docker-compose.yml
# -rw-r--r--  main.py
# -rw-r--r--  inference.py
# -rw-r--r--  memory.py
# -rw-r--r--  config.py
# -rw-r--r--  requirements.txt
# -rw-r--r--  .env.example
```

---

## 🎯 Étape 6 : Configuration .env

```bash
# Sur serveur
cd ~/ai-assistant

# Copier template
cp .env.example .env

# Éditer si besoin (défaults sont OK)
nano .env

# Vérifier (N_GPU_LAYERS=20 pour safe)
grep -E "N_GPU_LAYERS|N_CTX" .env
```

---

## 🎯 Étape 7 : Build Docker image

```bash
# Sur serveur
cd ~/ai-assistant

# Build (va prendre 5-10 min, beaucoup de output)
docker compose build

# Expected final line:
# Successfully tagged local-ai-assistant:latest
```

---

## 🎯 Étape 8 : Lancer service

```bash
# Démarrer en background
docker compose up -d

# Attendre 10 sec puis vérifier
sleep 10
docker compose ps

# Expected:
# NAME                  STATUS
# local-ai-assistant    Up 8 seconds
```

---

## 🎯 Étape 9 : Première inférence (long!)

```bash
# Health check
curl -s http://localhost:8000/health | python3 -m json.tool

# Expected: JSON avec "status": "healthy"

# ⏳ PREMIÈRE INFÉRENCE (va prendre 2-5 min pour télécharger modèle)
curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Bonjour",
    "max_tokens": 128
  }' | python3 -m json.tool

# Pendant ce temps, monitorer dans autre terminal:
docker compose logs -f local-ai
```

**À attendre** :
```
INFO: Downloading model: https://huggingface.co/...
INFO: Model file found
INFO: ✓ Model loaded successfully in 28.5s
```

Une fois chargé, les inférences futures seront rapides (~20-40s).

---

## ✅ Vérification finale

```bash
# 1. Container running
docker compose ps

# 2. Health check
curl -s http://localhost:8000/health | grep -q "healthy" && echo "✓ Healthy" || echo "✗ Not healthy"

# 3. VRAM usage
nvidia-smi

# Expected: ~3.0-3.5 Go utilisé (après model load)

# 4. Historique
curl -s http://localhost:8000/history | python3 -m json.tool | head -20
```

---

## 📊 Monitoring quotidien

```bash
# Voir logs
docker compose logs -f local-ai

# Arrêter
docker compose down

# Redémarrer
docker compose restart

# Stats ressources
docker stats local-ai

# GPU usage
nvidia-smi -l 1  # Refresh every 1 sec
```

---

## 🐛 Troubleshooting

### GPU non détecté

```bash
# Vérifier
nvidia-smi

# Si erreur:
# - NVIDIA driver pas installé → Étape 3.2
# - GPU pas dans BIOS → Vérifier BIOS/connexion physique
# - Driver incompatible → Réinstaller driver 550 (Étape 3.2)
```

### Docker image build fail

```bash
# Voir erreur
docker compose build --no-cache 2>&1 | tail -50

# Si "cuda compilation error":
# - CUDA toolkit manquant → Étape 3.3
# - GPU memory insufficient → Redémarrer, tuer autres services

# Clear et retry
docker compose down --rmi all
docker compose build --no-cache
```

### CUDA out of memory

```bash
# Réduire N_GPU_LAYERS dans .env
N_GPU_LAYERS=15  # Au lieu de 20

# Redémarrer
docker compose down
docker compose up -d
```

### Modèle ne télécharge pas

```bash
# Vérifier internet
ping huggingface.co

# Vérifier URL
curl -I https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf

# Si timeout, télécharger manuellement:
cd ~/ai-assistant/models
wget https://huggingface.co/.../qwen2.5-7b-instruct-q4_k_m.gguf
```

---

## 🎉 Succès!

Si tu sees:
- ✅ `docker compose ps` → container UP
- ✅ `curl /health` → 200 OK
- ✅ `/infer` → réponse JSON
- ✅ `nvidia-smi` → GPU utilized

**Phase 1 est production-ready** 🚀

---

## 📝 Checklist pré-deployment

- [ ] Ubuntu 24 LTS installé
- [ ] Docker + Docker Compose OK
- [ ] NVIDIA driver 550 installé
- [ ] CUDA toolkit installé
- [ ] GPU détecté (`nvidia-smi`)
- [ ] Code copié sur serveur
- [ ] `.env` configuré (N_GPU_LAYERS=20)
- [ ] Image Docker buildée
- [ ] Container running
- [ ] Health check OK
- [ ] Modèle téléchargé (~5 Go)
- [ ] Première inférence OK

---

## 📞 Support rapide

**Container ne démarre pas**
```bash
docker compose logs local-ai | tail -100
```

**API ne répond pas**
```bash
curl -v http://localhost:8000/health
docker compose exec local-ai ps aux
```

**VRAM error**
```bash
nvidia-smi
# Réduire N_GPU_LAYERS dans .env si > 80% utilisé
```

---

**Prêt pour Phase 2 (Discord) après ✅** 

Dis-moi quand c'est prêt sur le serveur!
