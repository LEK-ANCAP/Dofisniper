#!/bin/bash
set -e

# --- CONFIGURACIÓN TÁCTICA ---
REPO_URL="https://github.com/LEK-ANCAP/Dofisniper.git"
PROJECT_DIR="Dofisniper"
BACKUP_DIR="backups_sniper"

echo "🎯 ═══ Iniciando Despliegue de Dofisniper ═══ 🎯"

# 1. Verificación de dependencias
echo "🔍 Verificando Git/Docker..."
if ! command -v git &> /dev/null; then apt-get update && apt-get install -y git; fi
if ! command -v docker &> /dev/null; then 
    echo "⬇️ Instalando Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh
fi

# 2. Sincronización de Código
if [ -d "$PROJECT_DIR" ]; then
    echo "🔄 Sincronizando repositorio existente..."
    cd "$PROJECT_DIR"
    
    # Backup preventivo de la DB antes de actualizar
    mkdir -p "../$BACKUP_DIR"
    if [ -f "backend/data/dofimall_sniper.db" ]; then
        echo "💾 Creando backup preventivo de la DB..."
        cp "backend/data/dofimall_sniper.db" "../$BACKUP_DIR/backup_$(date +%F_%H-%M).db"
    fi
    
    git pull origin main
else
    echo "🚀 Clonando repositorio por primera vez..."
    git clone "$REPO_URL"
    cd "$PROJECT_DIR"
fi

# 3. Configuración de Entorno (.env)
if [ ! -f "backend/.env" ]; then
    echo "📝 Generando .env táctico inicial..."
    cat << 'EOF' > backend/.env
# DofiMall Sniper - Configuración Básica
DOFIMALL_EMAIL=tu_email@ejemplo.com
DOFIMALL_PASSWORD=tu_password
DOFIMALL_BASE_URL=https://www.dofimall.com
CHECK_INTERVAL_MINUTES=1
CHECK_INTERVAL_SECONDS=5
HEADLESS=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_email@gmail.com
SMTP_PASSWORD=app_password_aqui
NOTIFICATION_EMAIL=destino@ejemplo.com
SECRET_KEY=sniper-$(date +%s%N | md5sum | head -c 16)
DATABASE_URL=sqlite+aiosqlite:////app/data/dofimall_sniper.db
EOF
    echo "⚠️  .env base creado. EDÍTALO para que el bot funcione."
else
    echo "✅ Configuración .env detectada y preservada."
fi

# 4. Construcción y Lanzamiento
echo "🐳 Levantando la flota con Docker..."

# Función para intentar levantar el sistema
deploy_containers() {
    COMPOSE_CMD="docker compose"
    if ! docker compose version &> /dev/null; then COMPOSE_CMD="docker-compose"; fi
    
    echo "🧱 Usando: $COMPOSE_CMD build & up..."
    if $COMPOSE_CMD up -d --build; then
        echo "✅ Flota activa y operando."
    else
        echo "❌ ERROR EN LA CONSTRUCCIÓN. Iniciando diagnóstico..."
        $COMPOSE_CMD logs --tail=50
        exit 1
    fi
}

deploy_containers

# 5. Limpieza de imágenes huérfanas para ahorrar espacio
echo "🧹 Limpiando imágenes antiguas..."
docker image prune -f

echo "========================================="
echo "✅ ¡SISTEMA SINCRONIZADO CUAL SNIPER! ✅"
echo "URL: dofisniper.odubasolar.com"
echo "========================================="
