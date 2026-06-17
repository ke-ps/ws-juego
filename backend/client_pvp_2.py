"""Cliente WebSocket PvP - Jugador 2."""
import asyncio
import json

import websockets


async def main():
    uri = "ws://localhost:8001/ws/pvp"
    print(f"[Cliente 2] Conectando a {uri}...", flush=True)

    async with websockets.connect(uri) as ws:
        print("[Cliente 2] Conectado.", flush=True)

        # 1. connected
        msg = json.loads(await ws.recv())
        print(f"[Cliente 2] connected: {msg}", flush=True)

        # 2. game_start
        msg = json.loads(await ws.recv())
        print(f"[Cliente 2] recibe: {msg}", flush=True)

        if msg["type"] == "game_start":
            print("[Cliente 2] Partida iniciada. Esperando move del rival...", flush=True)
            reply = json.loads(await ws.recv())
            print(f"[Cliente 2] move rival: {reply}", flush=True)

    print("[Cliente 2] Desconectado.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())