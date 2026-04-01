# 🎯 DofiMall Sniper

Sistema de monitorización y auto-reserva de productos en [DofiMall](https://www.dofimall.com).

Detecta disponibilidad de productos, los añade automáticamente al carrito, y te notifica por Email/WhatsApp.

## Arquitectura

```
┌─────────────────────────────────────────────────┐
│                   Frontend (React + Vite)        │
│  Dashboard: productos, logs, estado, config      │
└──────────────────────┬──────────────────────────┘
                       │ REST API
┌──────────────────────┴──────────────────────────┐
│                Backend (FastAPI)                  │
│                                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────┐ │
│  │  Scheduler   │  │  Scraper     │  │ Notif.  │ │
│  │ (APScheduler)│──│ (Playwright) │──│ Engine  │ │
│  └─────────────┘  └──────────────┘  └─────────┘ │
│                                                   │
│  ┌─────────────┐  ┌──────────────┐               │
│  │  DB (SQLite) │  │  Auth/Config │               │
│  └─────────────┘  └──────────────┘               │
└──────────────────────────────────────────────────┘
```

## Requisitos

- Python 3.11+
- Node.js 18+
- Playwright (se instala automáticamente)

## Instalación rápida

```bash
# 1. Clonar y entrar
cd dofimall-sniper

# 2. Backend
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
playwright install chromium

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales de DofiMall

# 4. Iniciar backend
uvicorn app.main:app --reload --port 8000

# 5. Frontend (nueva terminal)
cd frontend
npm install
npm run dev
```

## Configuración (.env)

```env
# DofiMall Credentials
DOFIMALL_EMAIL=tu_email@ejemplo.com
DOFIMALL_PASSWORD=tu_password

# Notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_email@gmail.com
SMTP_PASSWORD=app_password
NOTIFICATION_EMAIL=destino@ejemplo.com

# WhatsApp (Meta Cloud API) - Opcional
WHATSAPP_TOKEN=tu_token
WHATSAPP_PHONE_ID=tu_phone_id
WHATSAPP_TO=34XXXXXXXXX

# App
SECRET_KEY=cambiar-por-clave-segura
CHECK_INTERVAL_MINUTES=5
HEADLESS=true
```

## Uso

1. Abre el dashboard en `http://localhost:5173`
2. Añade URLs de productos de DofiMall que quieras monitorizar
3. El sistema comprobará cada X minutos si hay stock
4. Cuando detecte stock → Añade al carrito → Va a pagar → Te notifica

## Despliegue en VPS (DigitalOcean)

```bash
# Usar Docker Compose
docker compose up -d
```

## Estructura del proyecto

```
dofimall-sniper/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + scheduler
│   │   ├── api/
│   │   │   ├── products.py      # CRUD productos a monitorizar
│   │   │   └── logs.py          # Historial de acciones
│   │   ├── core/
│   │   │   ├── config.py        # Settings desde .env
│   │   │   └── database.py      # SQLite setup
│   │   ├── models/
│   │   │   └── models.py        # SQLAlchemy models
│   │   ├── schemas/
│   │   │   └── schemas.py       # Pydantic schemas
│   │   ├── scraper/
│   │   │   ├── browser.py       # Playwright browser manager
│   │   │   ├── auth.py          # Login en DofiMall
│   │   │   ├── monitor.py       # Comprobar stock
│   │   │   └── purchase.py      # Auto-add to cart + checkout
│   │   └── notifications/
│   │       ├── email_notif.py   # Notificaciones email
│   │       └── whatsapp.py      # Notificaciones WhatsApp
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── components/
│   │   ├── pages/
│   │   └── hooks/
│   ├── package.json
│   └── vite.config.js
├── docker/
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── docker-compose.yml
└── README.md
```
