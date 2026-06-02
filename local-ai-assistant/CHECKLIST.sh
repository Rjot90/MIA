#!/usr/bin/env bash
# ==============================================================================
# DEPLOYMENT CHECKLIST - Phase 1 Pre-Launch
# ==============================================================================
#
# Avant de lancer en production, vérifier tous ces points
#
# ==============================================================================

echo \"🚀 LOCAL AI ASSISTANT - PHASE 1 DEPLOYMENT CHECKLIST\"
echo \"=====================================================\"
echo \"\"

# Color codes
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m'

CHECKS_PASSED=0
CHECKS_FAILED=0

# Helper function
check() {
    if [ $1 -eq 0 ]; then
        echo -e \"${GREEN}✓${NC} $2\"
        ((CHECKS_PASSED++))
    else
        echo -e \"${RED}✗${NC} $2\"
        ((CHECKS_FAILED++))
    fi
}

# ==============================================================================
# SYSTÈME
# ==============================================================================
echo -e \"${YELLOW}SYSTÈME${NC}\"

# Docker
which docker > /dev/null
check $? \"Docker installé\"

which docker-compose > /dev/null
check $? \"Docker Compose installé\"

# Espace disque
DISK_FREE=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
if [ \"$DISK_FREE\" -gt 50 ]; then
    check 0 \"Espace disque suffisant (${DISK_FREE} Go disponible)\"
else
    check 1 \"Espace disque insuffisant (besoin 50 Go, a ${DISK_FREE} Go)\"
fi

# GPU
nvidia-smi > /dev/null 2>&1
check $? \"NVIDIA GPU détecté\"

VRAM_TOTAL=$(nvidia-smi --query-gpu=memory.total --format=csv,nounits,noheader | head -1)
if [ \"$VRAM_TOTAL\" -ge 6000 ]; then
    check 0 \"VRAM suffisante ($VRAM_TOTAL MB)\"
else
    check 1 \"VRAM insuffisante (besoin 6000 MB, a $VRAM_TOTAL MB)\"
fi

echo \"\"

# ==============================================================================
# PROJET
# ==============================================================================
echo -e \"${YELLOW}PROJET${NC}\"

# Fichiers core
[ -f main.py ] && check 0 \"main.py existe\" || check 1 \"main.py manquant\"
[ -f inference.py ] && check 0 \"inference.py existe\" || check 1 \"inference.py manquant\"
[ -f memory.py ] && check 0 \"memory.py existe\" || check 1 \"memory.py manquant\"
[ -f config.py ] && check 0 \"config.py existe\" || check 1 \"config.py manquant\"

# Docker files
[ -f Dockerfile ] && check 0 \"Dockerfile existe\" || check 1 \"Dockerfile manquant\"
[ -f docker-compose.yml ] && check 0 \"docker-compose.yml existe\" || check 1 \"docker-compose.yml manquant\"
[ -f requirements.txt ] && check 0 \"requirements.txt existe\" || check 1 \"requirements.txt manquant\"

# Configuration
[ -f .env ] && check 0 \".env configuré\" || check 1 \".env manquant (copier .env.example)\"

# Documentation
[ -f README.md ] && check 0 \"README.md existe\" || check 1 \"README.md manquant\"
[ -f ARCHITECTURE.md ] && check 0 \"ARCHITECTURE.md existe\" || check 1 \"ARCHITECTURE.md manquant\"

echo \"\"

# ==============================================================================
# CONFIGURATION
# ==============================================================================
echo -e \"${YELLOW}CONFIGURATION${NC}\"

# Vérifier .env
if [ -f .env ]; then
    grep -q \"DEBUG=false\" .env
    check $? \"DEBUG désactivé en production\"
    
    grep -q \"N_GPU_LAYERS=33\" .env
    check $? \"N_GPU_LAYERS configuré (33 pour RTX 2060)\"
    
    grep -q \"N_CTX=2048\" .env
    check $? \"N_CTX configuré (2048 tokens)\"
else
    check 1 \".env doit être configuré\"
fi

echo \"\"

# ==============================================================================
# DIRECTORIES
# ==============================================================================
echo -e \"${YELLOW}RÉPERTOIRES${NC}\"

[ -d models ] && check 0 \"models/ existe\" || check 1 \"models/ manquant\"
[ -d data ] && check 0 \"data/ existe\" || check 1 \"data/ manquant\"
[ -d documents ] && check 0 \"documents/ existe\" || check 1 \"documents/ manquant\"
[ -d logs ] && check 0 \"logs/ existe\" || check 1 \"logs/ manquant\"

# Permissions
[ -w models ] && check 0 \"models/ writable\" || check 1 \"models/ non writable\"
[ -w data ] && check 0 \"data/ writable\" || check 1 \"data/ non writable\"
[ -w logs ] && check 0 \"logs/ writable\" || check 1 \"logs/ non writable\"

echo \"\"

# ==============================================================================
# MODEL DOWNLOAD
# ==============================================================================
echo -e \"${YELLOW}MODÈLE${NC}\"

MODEL_FILE=\"models/qwen2.5-7b-instruct-q4_k_m.gguf\"
if [ -f \"$MODEL_FILE\" ]; then
    SIZE=$(du -h \"$MODEL_FILE\" | awk '{print $1}')
    check 0 \"Modèle téléchargé ($SIZE)\"
else
    check 1 \"Modèle non trouvé (sera téléchargé au premier démarrage)\"
fi

echo \"\"

# ==============================================================================
# RÉSUMÉ
# ==============================================================================
echo -e \"${YELLOW}=====================================================${NC}\"
TOTAL=$((CHECKS_PASSED + CHECKS_FAILED))
echo -e \"Vérifications: ${GREEN}$CHECKS_PASSED/$TOTAL réussies${NC}\"

if [ $CHECKS_FAILED -eq 0 ]; then
    echo \"\"
    echo -e \"${GREEN}✓ PRÊT POUR DÉPLOIEMENT${NC}\"
    echo \"\"
    echo \"Prochaines étapes:\"
    echo \"  1. Vérifier .env: cat .env | grep -v ^#\"
    echo \"  2. Build: docker compose build\"
    echo \"  3. Démarrer: docker compose up -d\"
    echo \"  4. Tests: curl http://localhost:8000/health\"
    echo \"\"
else
    echo \"\"
    echo -e \"${RED}✗ ISSUES À CORRIGER${NC}\"
    echo \"\"
    echo \"Avant de lancer, résoudre les $CHECKS_FAILED issue(s) ci-dessus.\"
    echo \"\"
fi
