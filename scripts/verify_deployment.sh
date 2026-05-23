#!/bin/bash
# ============================================================================
# Verificador de Deployment
# ============================================================================

if [ -z "$1" ]; then
    echo "Error: Debes proporcionar la URL de producción"
    echo "Uso: ./verify_deployment.sh https://tu-url-produccion.com"
    exit 1
fi

BASE_URL=$1

echo "============================================================================"
echo "  VERIFICADOR DE DEPLOYMENT - WhatsApp SAAS"
echo "============================================================================"
echo ""
echo "URL a verificar: $BASE_URL"
echo ""

# Test 1: Health Check
echo "[1/3] Verificando Health Check..."
curl -s "$BASE_URL/health"
echo ""

# Test 2: Demo Menu
echo "[2/3] Verificando API de menú..."
curl -s "$BASE_URL/api/v1/restaurants/demo_restaurant/menu" | head -c 200
echo "..."
echo ""

# Test 3: Loyalty
echo "[3/3] Verificando sistema de puntos..."
curl -s "$BASE_URL/api/v1/loyalty/config/demo_restaurant" | head -c 200
echo "..."
echo ""

echo "============================================================================"
echo "Próximos pasos:"
echo "  1. Actualizar Twilio webhook: $BASE_URL/webhook/whatsapp"
echo "  2. Actualizar variable BASE_URL en tu plataforma"
echo "============================================================================"
