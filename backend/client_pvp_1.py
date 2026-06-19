"""Cliente WebSocket PvP - Jugador 1."""
import asyncio
import json

import websockets


async def main():
    uri = "ws://localhost:8001/ws/pvp"
    print(f"[Cliente 1] Conectando a {uri}...", flush=True)

    async with websockets.connect(uri) as ws:
        print("[Cliente 1] Conectado.", flush=True)

        # 1. connected
        msg = json.loads(await ws.recv())
        print(f"[Cliente 1] connected: {msg}", flush=True)

        # 2. waiting o game_start
        msg = json.loads(await ws.recv())
        print(f"[Cliente 1] recibe: {msg}", flush=True)

        if msg["type"] == "game_start":
            print("[Cliente 1] Partida iniciada. Enviando move...", flush=True)
            await ws.send(json.dumps({"type": "move", "payload": {"col": 3, "row": 5}}))
            print("[Cliente 1] Move enviado.", flush=True)

            reply = json.loads(await ws.recv())
            print(f"[Cliente 1] rival responde: {reply}", flush=True)

    print("[Cliente 1] Desconectado.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())