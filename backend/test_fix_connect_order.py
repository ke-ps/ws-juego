"""
Test específico para el bug de orden de mensajes: 
verificar que el segundo jugador NO recibe 'connected' después de 'game_start'.

El fix en game.py envía 'connected' solo si session.game es None.
"""
import asyncio
import json
import sys

import websockets


class TestError(AssertionError):
    pass


class WSClient:
    def __init__(self, uri: str, name: str):
        self.uri = uri
        self.name = name
        self.ws = None

    async def connect(self):
        self.ws = await websockets.connect(self.uri)
        print(f"[{self.name}] Conectado.", flush=True)

    async def recv(self, timeout: float = 5.0) -> dict:
        msg = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
        data = json.loads(msg)
        print(f"[{self.name}] recv: {json.dumps(data, separators=(',', ':'))}", flush=True)
        return data

    async def close(self):
        if self.ws:
            await self.ws.close()
        print(f"[{self.name}] Desconectado.", flush=True)


async def test_message_order():
    """
    Escenario secuencial que verifica el orden correcto de mensajes:
    1. C1 conecta → recibe 'connected', luego 'waiting'
    2. C2 conecta → recibe 'connected', luego 'game_start'
    3. C1 recibe 'game_start'
    4. El orden para ambos jugadores es: connected ANTES de waiting/game_start
    """
    c1 = WSClient("ws://localhost:8000/ws/pvp", "C1")
    c2 = WSClient("ws://localhost:8000/ws/pvp", "C2")

    try:
        # ── 1. Conectar C1 y esperar sus mensajes ──
        print("\n--- Paso 1: Conectar C1 ---", flush=True)
        await c1.connect()

        # C1 debe recibir 'connected' primero
        c1_msg1 = await c1.recv()
        assert c1_msg1["type"] == "connected", \
            f"C1 debe recibir 'connected' primero, recibió '{c1_msg1['type']}'"
        c1_client_id = c1_msg1["data"]["client_id"]
        c1_session_id = c1_msg1["data"]["session_id"]
        print(f"[CHECK] C1 connected: client_id={c1_client_id}, session_id={c1_session_id}", flush=True)

        # C1 debe recibir 'waiting' segundo
        c1_msg2 = await c1.recv()
        assert c1_msg2["type"] == "waiting", \
            f"C1 debe recibir 'waiting' segundo, recibió '{c1_msg2['type']}'"
        print(f"[CHECK] C1 waiting: session_id={c1_msg2['data']['session_id']}", flush=True)

        # ── 2. Conectar C2 ──
        print("\n--- Paso 2: Conectar C2 ---", flush=True)
        await c2.connect()

        # C2 debe recibir 'connected' primero
        c2_msg1 = await c2.recv()
        assert c2_msg1["type"] == "connected", \
            f"C2 debe recibir 'connected' primero, recibió '{c2_msg1['type']}'"
        print(f"[CHECK] C2 connected: client_id={c2_msg1['data']['client_id']}, session_id={c2_msg1['data']['session_id']}", flush=True)

        # C2 debe recibir 'game_start' segundo
        c2_msg2 = await c2.recv()
        assert c2_msg2["type"] == "game_start", \
            f"C2 debe recibir 'game_start' segundo, recibió '{c2_msg2['type']}'"
        print(f"[CHECK] C2 game_start: session_id={c2_msg2['data']['session_id']}", flush=True)
        # Verificar que connected llegó ANTES que game_start ✓

        # ── 3. C1 debe recibir 'game_start' ──
        print("\n--- Paso 3: Verificar que C1 recibe game_start ---", flush=True)
        c1_msg3 = await c1.recv()
        assert c1_msg3["type"] == "game_start", \
            f"C1 debe recibir 'game_start' ahora, recibió '{c1_msg3['type']}'"
        print(f"[CHECK] C1 game_start: session_id={c1_msg3['data']['session_id']}", flush=True)

        # ── Verificaciones finales ──
        assert c1_session_id == c2_msg2["data"]["session_id"], \
            "Ambos jugadores deben tener el mismo session_id"
        assert c1_session_id == c1_msg3["data"]["session_id"], \
            "C1 debe mantener el mismo session_id"
        print("\n[PASS] Todas las comprobaciones pasaron. El orden de mensajes es correcto.", flush=True)
        return ["PASS"]

    except asyncio.TimeoutError as e:
        msg = f"[FAIL] Timeout: {e}"
        print(msg, flush=True)
        return ["FAIL", msg]
    except TestError as e:
        msg = f"[FAIL] {e}"
        print(msg, flush=True)
        return ["FAIL", str(e)]
    except websockets.exceptions.WebSocketException as e:
        msg = f"[FAIL] WebSocket error: {e}"
        print(msg, flush=True)
        return ["FAIL", str(e)]
    except Exception as e:
        msg = f"[FAIL] {type(e).__name__}: {e}"
        print(msg, flush=True)
        return ["FAIL", msg]
    finally:
        await c1.close()
        await c2.close()


async def main():
    print("=" * 60, flush=True)
    print("TEST: Verificar orden de mensajes (fix disconnect bug)", flush=True)
    print("=" * 60, flush=True)
    result = await asyncio.wait_for(test_message_order(), timeout=15.0)
    print("=" * 60, flush=True)
    print(f"Resultado: {result[0]}", flush=True)
    print("=" * 60, flush=True)
    if result[0] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
