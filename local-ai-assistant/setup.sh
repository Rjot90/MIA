#!/usr/bin/env bash

# ==============================================================================
# SETUP.SH - Installation automatisée Phase 1 sur Ubuntu Server 24 LTS
# ==============================================================================
#
# Utilisation:
#   curl https://raw.githubusercontent.com/yourrepo/setup.sh | bash
#   ou localement:
#   bash setup.sh
#
# Ce script automatise:
# 1. Vérifications système (GPU, disque, etc)
# 2. Installation Docker
# 3. Configuration utilisateur pour Docker
# 4. Build image
# 5. Lancement service
#
# ⚠️ MANUAL STEPS STILL REQUIRED:
# - NVIDIA drivers (nécessite reboot)
# - CUDA toolkit (optionnel)
#
# ==============================================================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
    echo ""
}

check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "${GREEN}✓${NC} $2"
        return 0
    else
        echo -e "${RED}✗${NC} $2"
        return 1
    fi
}

# ==============================================================================
# ÉTAPE 0 : VÉRIFICATIONS PRÉALABLES
# ==============================================================================

print_header "ÉTAPE 0: Vérifications système"

# Check sudo
if ! sudo -n true 2>/dev/null; then
    echo -e "${RED}✗${NC} Sudo password required. Run: sudo bash setup.sh"
    exit 1
fi
echo -e "${GREEN}✓${NC} Sudo OK"

# Check OS
if [ ! -f /etc/os-release ]; then
    echo -e "${RED}✗${NC} /etc/os-release not found"
    exit 1
fi

source /etc/os-release
if [[ "$VERSION_ID" != "24.04" ]]; then
    echo -e "${YELLOW}⚠${NC} Ubuntu 24.04 recommended (found $VERSION_ID)"
fi
echo -e "${GREEN}✓${NC} Ubuntu detected: $PRETTY_NAME"

# Check disk space
DISK_FREE=$(df / | awk 'NR==2 {print $4}' | xargs -I {} bash -c 'echo $(( {} / 1024 / 1024 ))')
if [ "$DISK_FREE" -lt 50 ]; then
    echo -e "${RED}✗${NC} Insufficient disk space ($DISK_FREE GB, need 50 GB)"
    exit 1
fi
echo -e "${GREEN}✓${NC} Disk space OK ($DISK_FREE GB)"

# Check GPU
if lspci | grep -i nvidia > /dev/null; then
    echo -e "${GREEN}✓${NC} NVIDIA GPU detected"
else
    echo -e "${YELLOW}⚠${NC} NVIDIA GPU not detected (will still install Docker)"
fi

echo ""
echo -e "${YELLOW}Manual steps still required:${NC}"
echo "1. NVIDIA drivers (reboot after): INSTALL.md Étape 3.2"
echo "2. NVIDIA CUDA toolkit (optional): INSTALL.md Étape 3.3"
echo ""

# ==============================================================================
# ÉTAPE 1 : UPDATE SYSTÈME
# ==============================================================================

print_header "ÉTAPE 1: Mise à jour système"

echo "Updating package lists..."
sudo apt update -qq
sudo apt upgrade -y -qq
echo -e "${GREEN}✓${NC} System updated"

# ==============================================================================
# ÉTAPE 2 : INSTALLER DÉPENDANCES
# ==============================================================================

print_header "ÉTAPE 2: Installation dépendances"

sudo apt install -y -qq \
    curl wget git build-essential ca-certificates \
    gnupg lsb-release python3

check_command "curl" "curl"
check_command "git" "git"
check_command "python3" "python3"

# ==============================================================================
# ÉTAPE 3 : INSTALLER DOCKER
# ==============================================================================

print_header "ÉTAPE 3: Installation Docker"

# Check if already installed
if check_command "docker" "Docker already installed"; then
    echo "Skipping Docker installation"
else
    echo "Installing Docker..."
    
    # Add Docker repo
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
        sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
        sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    sudo apt update -qq
    sudo apt install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    check_command "docker" "Docker"
fi

# ==============================================================================
# ÉTAPE 4 : CONFIGURE DOCKER POUR UTILISATEUR COURANT
# ==============================================================================

print_header "ÉTAPE 4: Configuration Docker utilisateur"

# Add user to docker group
if id -nG "$USER" | grep -qw "docker"; then
    echo -e "${GREEN}✓${NC} User already in docker group"
else
    echo "Adding $USER to docker group..."
    sudo usermod -aG docker "$USER"
    echo -e "${GREEN}✓${NC} User added to docker group"
    echo -e "${YELLOW}⚠${NC} You may need to logout/login or run: newgrp docker"
fi

# ==============================================================================
# ÉTAPE 5 : PRÉPARER RÉPERTOIRES
# ==============================================================================

print_header "ÉTAPE 5: Préparation répertoires"

if [ ! -d "models" ]; then
    mkdir -p models data documents logs
    echo -e "${GREEN}✓${NC} Directories created"
else
    echo -e "${GREEN}✓${NC} Directories already exist"
fi

# ==============================================================================
# ÉTAPE 6 : VÉRIFIER CODE
# ==============================================================================

print_header "ÉTAPE 6: Vérification code"

REQUIRED_FILES=("Dockerfile" "docker-compose.yml" "main.py" "inference.py" "memory.py" "config.py" "requirements.txt" ".env.example")
MISSING=0

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file"
    else
        echo -e "${RED}✗${NC} $file MISSING"
        ((MISSING++))
    fi
done

if [ $MISSING -gt 0 ]; then
    echo ""
    echo -e "${RED}✗${NC} Missing $MISSING files!"
    echo "Make sure all code files are in current directory"
    exit 1
fi

# ==============================================================================
# ÉTAPE 7 : SETUP .ENV
# ==============================================================================

print_header "ÉTAPE 7: Configuration .env"

if [ -f ".env" ]; then
    echo -e "${GREEN}✓${NC} .env exists"
else
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${GREEN}✓${NC} .env created"
fi

# Verify critical settings
if grep -q "N_GPU_LAYERS=20" .env; then
    echo -e "${GREEN}✓${NC} N_GPU_LAYERS=20 (safe)"
else
    echo -e "${YELLOW}⚠${NC} N_GPU_LAYERS might not be 20"
fi

if grep -q "N_CTX=1024" .env; then
    echo -e "${GREEN}✓${NC} N_CTX=1024 (safe)"
else
    echo -e "${YELLOW}⚠${NC} N_CTX might not be 1024"
fi

# ==============================================================================
# ÉTAPE 8 : BUILD DOCKER IMAGE
# ==============================================================================

print_header "ÉTAPE 8: Build Docker image"

echo "Building Docker image (this may take 5-10 minutes)..."
echo ""

if docker compose build; then
    echo ""
    echo -e "${GREEN}✓${NC} Docker image built successfully"
else
    echo ""
    echo -e "${RED}✗${NC} Docker build failed"
    echo "Try: docker compose build --no-cache"
    exit 1
fi

# ==============================================================================
# ÉTAPE 9 : LANCER SERVICE
# ==============================================================================

print_header "ÉTAPE 9: Lancement service"

echo "Starting service..."
docker compose up -d

# Wait for startup
echo "Waiting for service startup (10 seconds)..."
sleep 10

# Check status
if docker compose ps | grep -q "Up"; then
    echo -e "${GREEN}✓${NC} Service started"
    docker compose ps
else
    echo -e "${RED}✗${NC} Service failed to start"
    docker compose logs local-ai | tail -20
    exit 1
fi

# ==============================================================================
# ÉTAPE 10 : HEALTH CHECK
# ==============================================================================

print_header "ÉTAPE 10: Health check"

HEALTH_RETRIES=10
HEALTH_COUNT=0

while [ $HEALTH_COUNT -lt $HEALTH_RETRIES ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} API responding"
        break
    fi
    echo "Waiting for API... (attempt $((HEALTH_COUNT+1))/$HEALTH_RETRIES)"
    sleep 2
    ((HEALTH_COUNT++))
done

if [ $HEALTH_COUNT -eq $HEALTH_RETRIES ]; then
    echo -e "${YELLOW}⚠${NC} API not responding yet"
    echo "Check logs: docker compose logs -f local-ai"
fi

# ==============================================================================
# RÉSUMÉ FINAL
# ==============================================================================

print_header "✓ INSTALLATION COMPLÉTÉE"

echo -e "${GREEN}Configuration Phase 1 terminée!${NC}"
echo ""
echo "Next steps:"
echo "1. NVIDIA drivers (MANUAL): INSTALL.md Étape 3"
echo "   sudo apt install nvidia-driver-550"
echo "   sudo reboot"
echo ""
echo "2. Vérifier après reboot:"
echo "   nvidia-smi"
echo "   docker compose ps"
echo "   curl http://localhost:8000/health"
echo ""
echo "3. Lancer première inférence:"
echo "   curl -X POST http://localhost:8000/infer \\"
echo "     -d '{\"prompt\": \"Bonjour\"}'"
echo ""
echo "4. Accès API:"
echo "   - API: http://localhost:8000"
echo "   - Swagger: http://localhost:8000/docs"
echo ""
echo "Logs: docker compose logs -f local-ai"
echo ""

# ==============================================================================
