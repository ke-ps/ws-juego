"""
Test de matchmaking PvP real.

Verifica:
1. Dos clientes conectados simultáneamente.
2. Ambos reciben game_start.
3. Ambos comparten el mismo session_id.
4. Un move enviado por C1 llega a C2 con el payload correcto.
5. Un chat enviado por C2 llega a C1.

El test FALLA automáticamente si alguna condición no se cumple.
"""
import asyncio
import json
import sys

import websockets


# ── Excepciones propias ───────────────────────────────────────────────────────


class TestAssertionError(AssertionError):
    """Fallo de aserción en el test."""


def assert_equal(actual, expected, msg: str):
    if actual != expected:
        raise TestAssertionError(
            f"{msg}: esperado {expected!r}, obtenido {actual!r}"
        )


def assert_in(key, obj: dict, msg: str):
    if key not in obj:
        raise TestAssertionError(
            f"{msg}: clave '{key}' no encontrada en {obj!r}"
        )


# ── Cliente reutilizable ──────────────────────────────────────────────────────


class WSClient:
    """Cliente WebSocket con utilidades de recepción/envío y almacenamiento de estado."""

    def __init__(self, uri: str, name: str):
        self.uri = uri
        self.name = name
        self.ws = None
        self.client_id = None
        self.session_id = None

    async def connect(self):
        self.ws = await websockets.connect(self.uri)
        print(f"[{self.name}] Conectado.", flush=True)

    async def recv(self, timeout: float = 5.0) -> dict:
        """Recibe y parsea un mensaje JSON del servidor."""
        msg = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
        data = json.loads(msg)
        print(f"[{self.name}] recv: {json.dumps(data, separators=(',', ':'))}", flush=True)
        return data

    async def send(self, payload: dict):
        await self.ws.send(json.dumps(payload))
        print(f"[{self.name}] send: {json.dumps(payload, separators=(',', ':'))}", flush=True)

    async def close(self):
        if self.ws:
            await self.ws.close()
        print(f"[{self.name}] Desconectado.", flush=True)


# ── Test ──────────────────────────────────────────────────────────────────────


async def _collect_messages(client: WSClient, max_count: int = 10) -> dict:
    """Recolecta mensajes hasta tener connected y game_start."""
    result = {
        "connected": None,
        "game_start": None,
        "waiting": None,
        "messages": [],
    }
    for _ in range(max_count):
        msg = await client.recv()
        result["messages"].append(msg)
        if msg["type"] == "connected" and result["connected"] is None:
            result["connected"] = msg
        elif msg["type"] == "game_start" and result["game_start"] is None:
            result["game_start"] = msg
        elif msg["type"] == "waiting" and result["waiting"] is None:
            result["waiting"] = msg
        # Terminar si tenemos connected + (game_start o waiting)
        # Para el primer jugador: connected + waiting
        # Para el segundo jugador: connected + game_start
        if result["connected"] is not None and (
            result["game_start"] is not None or result["waiting"] is not None
        ):
            break
    return result


async def pvp_matchmaking_test() -> list[str]:
    """
    Test de matchmaking PvP robusto que no depende del orden de conexión.

    Verificaciones:
    1. Ambos jugadores reciben 'connected' con client_id y session_id.
    2. Ambos jugadores reciben 'game_start' con los mismos players.
    3. Ambos comparten el mismo session_id.
    4. Un move enviado por C1 llega a C2 con el payload correcto.
    5. Un chat enviado por C2 llega a C1.
    """
    c1 = WSClient("ws://localhost:8000/ws/pvp", "C1")
    c2 = WSClient("ws://localhost:8000/ws/pvp", "C2")

    try:
        # ── Conexión SIMULTÁNEA con gather ──
        await asyncio.gather(c1.connect(), c2.connect())
        print("[MAIN] Ambos conectados.", flush=True)

        # ── Recopilar mensajes de ambos jugadores en PARALELO ──
        c1_data, c2_data = await asyncio.gather(
            _collect_messages(c1),
            _collect_messages(c2),
        )

        # Imprimir todos los mensajes recibidos
        print(f"[C1] Mensajes recibidos: {len(c1_data['messages'])}", flush=True)
        for msg in c1_data["messages"]:
            print(f"  - {msg['type']}", flush=True)
        print(f"[C2] Mensajes recibidos: {len(c2_data['messages'])}", flush=True)
        for msg in c2_data["messages"]:
            print(f"  - {msg['type']}", flush=True)

        # ── Verificar connected ──
        assert c1_data["connected"] is not None, "C1 debe recibir 'connected'"
        assert c2_data["connected"] is not None, "C2 debe recibir 'connected'"
        c1.client_id = c1_data["connected"]["data"]["client_id"]
        c1.session_id = c1_data["connected"]["data"]["session_id"]
        c2.client_id = c2_data["connected"]["data"]["client_id"]
        c2.session_id = c2_data["connected"]["data"]["session_id"]
        print(f"[C1] connected: client_id={c1.client_id}, session_id={c1.session_id}", flush=True)
        print(f"[C2] connected: client_id={c2.client_id}, session_id={c2.session_id}", flush=True)

        # ── Verificar game_start recibido ──
        assert c1_data["game_start"] is not None, "C1 debe recibir 'game_start'"
        assert c2_data["game_start"] is not None, "C2 debe recibir 'game_start'"
        print(f"[C1] game_start: session_id={c1_data['game_start']['data']['session_id']}", flush=True)
        print(f"[C2] game_start: session_id={c2_data['game_start']['data']['session_id']}", flush=True)

        # ── Verificaciones: mismo session_id ──
        assert_equal(
            c1_data["game_start"]["data"]["session_id"],
            c2_data["game_start"]["data"]["session_id"],
            "Ambos game_start deben tener el mismo session_id"
        )
        assert_equal(c1.session_id, c2.session_id, "C1 y C2 deben compartir el mismo session_id")

        # ── Verificar players en game_start ──
        players_c1 = c1_data["game_start"]["data"]["players"]
        players_c2 = c2_data["game_start"]["data"]["players"]
        assert_equal(set(players_c1.values()), set(players_c2.values()),
                     "Ambos game_start deben listar los mismos jugadores")
        assert_equal(c1.client_id in set(players_c1.values()), True,
                     "C1.client_id debe estar en game_start.players")
        assert_equal(c2.client_id in set(players_c2.values()), True,
                     "C2.client_id debe estar en game_start.players")
        print(f"[CHECK] session_id: {c1.session_id} OK", flush=True)
        print(f"[CHECK] players: {players_c1} OK", flush=True)

        # ── C1 envía move, C2 debe recibirlo ──
        move_payload = {"col": 3, "row": 5}
        await c1.send({"type": "move", "payload": move_payload})

        msg = await c2.recv()
        assert_equal(msg["type"], "opponent_move", "C2 debe recibir 'opponent_move'")
        assert_equal(msg["data"], move_payload, "C2 debe recibir el payload exacto de C1")
        print("[CHECK] Move de C1 llegó a C2 con payload correcto OK", flush=True)

        # ── C2 envía chat, C1 debe recibirlo ──
        chat_payload = {"text": "hola rival"}
        await c2.send({"type": "chat", "payload": chat_payload})

        msg = await c1.recv()
        assert_equal(msg["type"], "chat", "C1 debe recibir 'chat'")
        assert_equal(msg["data"], chat_payload, "C1 debe recibir el chat payload exacto")
        print("[CHECK] Chat de C2 llegó a C1 OK", flush=True)

        print("\n[PASS] Todas las comprobaciones pasaron.", flush=True)
        return ["PASS"]

    except asyncio.TimeoutError as e:
        msg = f"[FAIL] Timeout: {e}"
        print(msg, flush=True)
        return ["FAIL", msg]
    except TestAssertionError as e:
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


# ── Entry point ───────────────────────────────────────────────────────────────


async def main():
    print("=" * 60, flush=True)
    print("TEST PvP: Matchmaking — dos clientes simultáneos", flush=True)
    print("=" * 60, flush=True)

    result = await asyncio.wait_for(pvp_matchmaking_test(), timeout=15.0)

    print("=" * 60, flush=True)
    print(f"Resultado final: {result[0]}", flush=True)
    print("=" * 60, flush=True)

    with open("test_pvp_result.txt", "w") as f:
        f.write(result[0] + "\n")
        for line in result[1:]:
            f.write(line + "\n")

    if result[0] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())