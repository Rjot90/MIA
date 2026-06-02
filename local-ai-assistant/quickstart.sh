#!/usr/bin/env bash
# ==============================================================================
# QUICKSTART.SH - Script démarrage rapide Phase 1
# ==============================================================================
#
# Utilisation:
#   bash quickstart.sh
#
# Ce script:
# 1. Crée répertoires nécessaires
# 2. Copie .env
# 3. Build Docker
# 4. Lance le container
# 5. Teste health check
#
# ==============================================================================

set -e  # Exit on error

echo "🚀 Local AI Assistant - Phase 1 Quick Start"
echo "=============================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Docker
echo -e "${YELLOW}[1/5]${NC} Vérification Docker..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker non trouvé${NC}"
    echo "Installer Docker: https://docs.docker.com/install/"
    exit 1
fi
echo -e "${GREEN}✓ Docker trouvé${NC}"

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ docker-compose non trouvé${NC}"
    exit 1
fi
echo -e "${GREEN}✓ docker-compose trouvé${NC}"
echo ""

# Create directories
echo -e "${YELLOW}[2/5]${NC} Création répertoires..."
mkdir -p models data documents logs
echo -e "${GREEN}✓ Répertoires créés${NC}"
echo ""

# Setup .env
echo -e "${YELLOW}[3/5]${NC} Configuration .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ .env créé (defaults OK)${NC}"
else
    echo -e "${GREEN}✓ .env existe déjà${NC}"
fi
echo ""

# Build Docker
echo -e "${YELLOW}[4/5]${NC} Build image Docker (peut prendre ~1-2 min)..."
docker compose build
echo -e "${GREEN}✓ Image buildée${NC}"
echo ""

# Start service
echo -e "${YELLOW}[5/5]${NC} Lancement du service..."
docker compose up -d
echo -e "${GREEN}✓ Service lancé${NC}"
echo ""

# Wait for startup
echo "⏳ Attente démarrage (20-40s)..."
sleep 10

# Health check
echo ""
echo "🔍 Test health check..."
RETRIES=0
while [ $RETRIES -lt 10 ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Service prêt!${NC}"
        break
    fi
    RETRIES=$((RETRIES+1))
    echo "  Tentative $RETRIES/10..."
    sleep 5
done

if [ $RETRIES -eq 10 ]; then
    echo -e "${RED}✗ Service ne répond pas${NC}"
    echo "Vérifier les logs: docker compose logs local-ai"
    exit 1
fi

# Test inference
echo ""
echo "🧪 Test inférence..."
RESPONSE=$(curl -s -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Bonjour, comment ca va?", "max_tokens": 128}')

if echo "$RESPONSE" | grep -q "text"; then
    echo -e "${GREEN}✓ Inférence fonctionnelle!${NC}"
    echo ""
    echo "📝 Réponse test:"
    echo "$RESPONSE" | python3 -m json.tool | head -20
else
    echo -e "${RED}✗ Inférence échouée${NC}"
    echo "Réponse: $RESPONSE"
    exit 1
fi

echo ""
echo "=============================================="
echo -e "${GREEN}✓ SETUP COMPLET${NC}"
echo "=============================================="
echo ""
echo "🌐 Accès:"
echo "  API: http://localhost:8000"
echo "  Docs: http://localhost:8000/docs"
echo "  ReDoc: http://localhost:8000/redoc"
echo ""
echo "📚 Documentation:"
echo "  - Lire README.md"
echo "  - Voir logs: docker compose logs -f local-ai"
echo "  - Tester endpoints: curl http://localhost:8000/health"
echo ""
echo "🎯 Prochaines étapes:"
echo "  1. Consulter README.md pour API usage"
echo "  2. Tester endpoints dans Swagger: /docs"
echo "  3. Phase 2: Discord bot integration"
echo ""
