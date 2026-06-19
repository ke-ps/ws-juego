"""Cliente WebSocket PvE."""
import asyncio
import json

import websockets


async def main():
    uri = "ws://localhost:8001/ws/pve"
    print(f"[Cliente PvE] Conectando a {uri}...", flush=True)

    async with websockets.connect(uri) as ws:
        print("[Cliente PvE] Conectado.", flush=True)

        # 1. connected
        msg = json.loads(await ws.recv())
        print(f"[Cliente PvE] connected: {msg}", flush=True)

        # 2. game_start (sin rival)
        msg = json.loads(await ws.recv())
        print(f"[Cliente PvE] recibe: {msg}", flush=True)

        if msg["type"] == "game_start":
            players = msg["data"]["players"]
            print(f"[Cliente PvE] player1={players['player1']} player2={players['player2']}", flush=True)

    print("[Cliente PvE] Desconectado.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())