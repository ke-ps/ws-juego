"""
Script de test PvE.
"""
import asyncio
import json
import sys

import websockets

async def main():
    uri = "ws://localhost:8000/ws/pve"
    print(f"[PvE] Conectando a {uri}...", flush=True)

    async with websockets.connect(uri) as ws:
        print("[PvE] Conectado.", flush=True)

        msg = json.loads(await ws.recv())
        print(f"[PvE] connected: {msg}", flush=True)

        msg = json.loads(await ws.recv())
        print(f"[PvE] recibe: {msg}", flush=True)

        if msg["type"] == "game_start":
            players = msg["data"]["players"]
            result = f"[PvE] mode={msg['data']['mode']} player1={players['player1']} player2={players['player2']}"
            print(result, flush=True)
            with open("test_pve_result.txt", "w") as f:
                f.write(result + "\n")

    print("[PvE] Desconectado.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())