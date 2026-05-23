#!/bin/bash
################################################################################
# SCRIPT: Actualizar URLs de Cloudflare Automáticamente
################################################################################
# Este script obtiene las URLs actuales de los túneles Cloudflare y
# actualiza automáticamente el archivo .env
################################################################################

set -e  # Exit on error

echo "════════════════════════════════════════════════════════════════════════════"
echo "  ACTUALIZADOR DE URLs DE CLOUDFLARE"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Obtener URLs de los túneles
echo "📡 Obteniendo URLs de Cloudflare Tunnels..."
echo ""

# URL del Customer App
CUSTOMER_APP_URL=$(docker logs proyecto_b_whatsapp_saas_cloudflare_tunnel_customer 2>&1 | grep -o 'https://[a-z0-9-]*.trycloudflare.com' | tail -1)

# URL del Gateway
GATEWAY_URL=$(docker logs proyecto_b_whatsapp_saas_cloudflare_tunnel 2>&1 | grep -o 'https://[a-z0-9-]*.trycloudflare.com' | tail -1)

# Verificar que se obtuvieron las URLs
if [ -z "$CUSTOMER_APP_URL" ]; then
    echo -e "${RED}❌ Error: No se pudo obtener la URL del Customer App${NC}"
    echo "   Verifica que el túnel esté corriendo:"
    echo "   docker ps | grep cloudflare_tunnel_customer"
    exit 1
fi

if [ -z "$GATEWAY_URL" ]; then
    echo -e "${RED}❌ Error: No se pudo obtener la URL del Gateway${NC}"
    echo "   Verifica que el túnel esté corriendo:"
    echo "   docker ps | grep cloudflare_tunnel"
    exit 1
fi

# Mostrar URLs encontradas
echo -e "${GREEN}✅ URLs encontradas:${NC}"
echo ""
echo "  🌐 Customer App:     $CUSTOMER_APP_URL"
echo "  🌐 WhatsApp Gateway: $GATEWAY_URL"
echo ""

# Verificar conectividad
echo "🧪 Verificando conectividad..."
echo ""

# Test Customer App
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$CUSTOMER_APP_URL/")
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "  ${GREEN}✅${NC} Customer App: $HTTP_CODE OK"
else
    echo -e "  ${RED}❌${NC} Customer App: $HTTP_CODE Error"
fi

# Test Gateway
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/health")
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "  ${GREEN}✅${NC} Gateway: $HTTP_CODE OK"
else
    echo -e "  ${RED}❌${NC} Gateway: $HTTP_CODE Error"
fi

echo ""

# Preguntar si actualizar .env
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${YELLOW}¿Deseas actualizar el archivo .env con estas URLs? (y/n)${NC}"
read -p "> " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelado."
    exit 0
fi

# Backup del .env
echo "📦 Creando backup de .env..."
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
echo -e "  ${GREEN}✅${NC} Backup creado"
echo ""

# Actualizar .env
echo "✏️  Actualizando .env..."

# Usar sed para actualizar (compatible con Mac y Linux)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s|^CUSTOMER_APP_URL=.*|CUSTOMER_APP_URL=$CUSTOMER_APP_URL|" .env
    sed -i '' "s|^BASE_URL=.*|BASE_URL=$GATEWAY_URL|" .env
else
    # Linux/Git Bash
    sed -i "s|^CUSTOMER_APP_URL=.*|CUSTOMER_APP_URL=$CUSTOMER_APP_URL|" .env
    sed -i "s|^BASE_URL=.*|BASE_URL=$GATEWAY_URL|" .env
fi

echo -e "  ${GREEN}✅${NC} .env actualizado"
echo ""

# Reiniciar whatsapp-gateway
echo "🔄 Reiniciando whatsapp-gateway para aplicar cambios..."
docker-compose restart whatsapp-gateway > /dev/null 2>&1

echo -e "  ${GREEN}✅${NC} whatsapp-gateway reiniciado"
echo ""

# Verificar variables de entorno en el contenedor
echo "🔍 Verificando variables de entorno en el contenedor..."
sleep 3  # Esperar que el contenedor esté listo

CUSTOMER_APP_URL_CONTAINER=$(docker exec proyecto_b_whatsapp_saas-whatsapp-gateway-1 env | grep "^CUSTOMER_APP_URL=" | cut -d= -f2-)

if [ "$CUSTOMER_APP_URL_CONTAINER" = "$CUSTOMER_APP_URL" ]; then
    echo -e "  ${GREEN}✅${NC} CUSTOMER_APP_URL correctamente configurado en el contenedor"
else
    echo -e "  ${YELLOW}⚠️${NC} CUSTOMER_APP_URL no coincide:"
    echo "     .env:        $CUSTOMER_APP_URL"
    echo "     contenedor:  $CUSTOMER_APP_URL_CONTAINER"
fi

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ ¡URLs actualizadas exitosamente!${NC}"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "🎯 Próximos pasos:"
echo "   1. Envía un mensaje de prueba por WhatsApp"
echo "   2. Pide 'ver el menú completo con fotos'"
echo "   3. Haz clic en la URL generada"
echo "   4. Verifica que la app del menú se carga correctamente"
echo ""
echo "📊 Para monitorear:"
echo "   docker logs -f proyecto_b_whatsapp_saas-whatsapp-gateway-1"
echo ""
