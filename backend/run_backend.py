import asyncio
import sys

# Crucial for Playwright on Windows under Uvicorn/FastAPI
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn
from app.main import app

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)