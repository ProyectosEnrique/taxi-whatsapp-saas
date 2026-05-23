#!/bin/bash
# ============================================================================
# Generador de Secretos para Producción
# ============================================================================
# Genera valores seguros para JWT_SECRET y SESSION_SECRET_KEY
# ============================================================================

echo "============================================================================"
echo "  GENERADOR DE SECRETOS - WhatsApp SAAS"
echo "============================================================================"
echo ""

echo "Generando secretos seguros..."
echo ""

# Generar JWT_SECRET
JWT_SECRET=$(openssl rand -hex 32)
echo "JWT_SECRET:"
echo "$JWT_SECRET"
echo ""

# Generar SESSION_SECRET_KEY
SESSION_SECRET=$(openssl rand -hex 32)
echo "SESSION_SECRET_KEY:"
echo "$SESSION_SECRET"
echo ""

echo "============================================================================"
echo "  AGREGAR A TU .env.production O VARIABLES DE ENTORNO:"
echo "============================================================================"
echo ""
echo "JWT_SECRET=$JWT_SECRET"
echo "SESSION_SECRET_KEY=$SESSION_SECRET"
echo ""

# Crear archivo .env.production si no existe
if [ ! -f .env.production ]; then
    echo "¿Deseas crear .env.production con estos valores? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        cp .env.production.example .env.production
        
        # Reemplazar valores
        sed -i "s/JWT_SECRET=.*/JWT_SECRET=$JWT_SECRET/" .env.production
        sed -i "s/SESSION_SECRET_KEY=.*/SESSION_SECRET_KEY=$SESSION_SECRET/" .env.production
        
        echo "✅ Archivo .env.production creado!"
        echo "⚠️  RECUERDA: Actualizar las demás variables (Twilio, etc.)"
    fi
fi

echo ""
echo "============================================================================"
echo "  IMPORTANTE:"
echo "============================================================================"
echo "  - NO compartas estos valores"
echo "  - NO los subas a Git"
echo "  - Guárdalos en tu gestor de passwords"
echo "============================================================================"
