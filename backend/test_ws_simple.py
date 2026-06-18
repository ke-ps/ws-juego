"""Script simple para probar la conexión WebSocket."""
import asyncio
import json
import websockets

async def test_single_client():
    """Test con un solo cliente."""
    print("Conectando a ws://localhost:8000/ws/pvp...")
    try:
        async with websockets.connect('ws://localhost:8000/ws/pvp', ping_interval=30) as ws:
            print("Conectado. Esperando mensajes...")
            # Recibir hasta 5 mensajes
            for i in range(5):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=10)
                    data = json.loads(msg)
                    print(f"[{i+1}] type={data.get('type')}, keys={list(data.keys())}")
                    if data.get('type') == 'waiting':
                        print("   -> Cliente en espera de rival")
                        break
                    if data.get('type') == 'error':
                        print(f"   -> ERROR: {data}")
                        break
                except asyncio.TimeoutError:
                    print(f"[{i+1}] Timeout esperando mensaje")
                    break
    except websockets.exceptions.WebSocketException as e:
        print(f"WebSocket error: {e}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_single_client())
