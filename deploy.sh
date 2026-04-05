#!/bin/bash
set -e

echo "Descargando dependencias..."
apt-get update
apt-get install -y docker.io docker-compose git

echo "Clonando repositorio..."
rm -rf Dofisniper
git clone https://github.com/LEK-ANCAP/Dofisniper.git
cd Dofisniper

echo "Generando Variables de Entorno Seguras..."
cat << 'EOF' > backend/.env
# DofiMall Sniper - Configuration
DOFIMALL_EMAIL=tu_email@ejemplo.com
DOFIMALL_PASSWORD=tu_password
DOFIMALL_BASE_URL=https://www.dofimall.com
CHECK_INTERVAL_MINUTES=1
HEADLESS=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_email@gmail.com
SMTP_PASSWORD=app_password_aqui
NOTIFICATION_EMAIL=destino@ejemplo.com
WHATSAPP_TOKEN=
WHATSAPP_PHONE_ID=
WHATSAPP_TO=
TELEGRAM_BOT_TOKEN=7116305339:AAGcADNtikyz6hHCOaptDd_xn-xeKpw7fDI
TELEGRAM_CHAT_ID=8003584484,764259295
SECRET_KEY=cambiar-por-clave-segura-larga
DATABASE_URL=sqlite+aiosqlite:///./dofimall_sniper.db
EOF

echo "Levantando la flota completa (Backend + Frontend + Base de Datos)..."
docker-compose build
docker-compose up -d

echo "========================================="
echo "✅ ¡DESPLIEGUE COMPLETADO EXITOSAMENTE! ✅"
echo "========================================="
