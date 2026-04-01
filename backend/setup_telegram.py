import time
import httpx
import asyncio

TOKEN = "7116305339:AAGcADNtikyz6hHCOaptDd_xn-xeKpw7fDI"
USERNAME_TARGET = "leooficial"

async def main():
    print(f"Esperando a que @{USERNAME_TARGET} envíe un mensaje al bot...")
    start_time = time.time()
    
    async with httpx.AsyncClient() as client:
        while time.time() - start_time < 300: # Espera hasta 5 minutos
            try:
                resp = await client.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates")
                data = resp.json()
                
                if "result" in data:
                    for item in data["result"]:
                        if "message" in item:
                            msg = item["message"]
                            chat = msg.get("chat", {})
                            from_user = msg.get("from", {})
                            
                            username = from_user.get("username", "")
                            if username.lower() == USERNAME_TARGET.lower():
                                chat_id = chat.get("id")
                                print(f"✅ ¡Encontrado! El Chat ID de @{USERNAME_TARGET} es {chat_id}")
                                
                                # Actualizar o añadir a .env
                                import os
                                env_path = os.path.join(os.path.dirname(__file__), ".env")
                                
                                with open(env_path, "r", encoding="utf-8") as f:
                                    lines = f.readlines()
                                
                                updated = False
                                with open(env_path, "w", encoding="utf-8") as f:
                                    for line in lines:
                                        if line.startswith("TELEGRAM_CHAT_ID="):
                                            f.write(f"TELEGRAM_CHAT_ID={chat_id}\n")
                                            updated = True
                                        else:
                                            f.write(line)
                                            
                                if not updated:
                                    with open(env_path, "a", encoding="utf-8") as f:
                                        f.write(f"\nTELEGRAM_CHAT_ID={chat_id}\n")
                                        
                                print("✅ ¡Archivo .env actualizado exitosamente!")
                                return
            except Exception as e:
                pass
            
            await asyncio.sleep(2)
            
    print("⏳ Tiempo de espera agotado.")

if __name__ == "__main__":
    asyncio.run(main())
