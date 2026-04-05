#!/bin/bash
set -e

echo "Verificando dependencias (Docker/Git)..."
if ! command -v git &> /dev/null; then apt-get update && apt-get install -y git; fi
if ! command -v docker &> /dev/null; then 
    echo "Instalando Docker Engine oficial..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
fi

if [ -d "Dofisniper" ]; then
    echo "Sincronizando cambios en repositorio existente..."
    cd Dofisniper
    git pull origin main
else
    echo "Clonando repositorio por primera vez..."
    git clone https://github.com/LEK-ANCAP/Dofisniper.git
    cd Dofisniper
fi

if [ ! -f "backend/.env" ]; then
    echo "Generando Variables de Entorno Seguras..."
    cat << 'EOF' > backend/.env
# DofiMall Sniper - Configuration
# --- RELLENA ESTO SI ES LA PRIMERA VEZ ---
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
SECRET_KEY=clave-generada-$(date +%s)
DATABASE_URL=sqlite+aiosqlite:///./dofimall_sniper.db
EOF
    echo "⚠️  .env base creado. Recuerda editarlo con tus credenciales reales."
else
    echo "✅ .env existente detectado. Manteniendo configuración actual."
fi

echo "Levantando la flota completa (Backend + Frontend + Base de Datos)..."
# Usar el plugin moderno 'docker compose' o el binario antiguo según disponibilidad
if docker compose version &> /dev/null; then
    docker compose build
    docker compose up -d
else
    docker-compose build
    docker-compose up -d
fi

echo "========================================="
echo "✅ ¡DESPLIEGUE COMPLETADO EXITOSAMENTE! ✅"
echo "========================================="
