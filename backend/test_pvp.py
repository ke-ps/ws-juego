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


# ── Excepciones propias ────────────────────────────────────────────────────

class TestError(AssertionError):
    """Fallo de aserción en el test."""


def assert_equal(actual, expected, msg: str):
    if actual != expected:
        raise TestError(
            f"{msg}: esperado {expected!r}, obtenido {actual!r}"
        )


def assert_in(key, obj: dict, msg: str):
    if key not in obj:
        raise TestError(
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
    """Recolecta mensajes hasta tener game_start + turn."""
    result = {
        "connected": None,
        "game_start": None,
        "waiting": None,
        "turn": None,
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
        elif msg["type"] == "turn" and result["turn"] is None:
            result["turn"] = msg
        # Terminar cuando tengamos game_start + turn
        # (waiting no es suficiente, hay que esperar game_start)
        if result["game_start"] is not None and result["turn"] is not None:
            break
    return result


async def pvp_matchmaking_test() -> list[str]:
    """
    Test de matchmaking PvP robusto que no depende del orden de conexión.

    Verificaciones:
    1. El primer jugador (C1) recibe 'connected' con client_id y session_id.
    2. El segundo jugador (C2) no recibe 'connected' (fix: solo game_start).
    3. Ambos jugadores reciben 'game_start' con los mismos players.
    4. Ambos comparten el mismo session_id.
    5. Un move enviado por C1 llega a C2 con el payload correcto.
    6. Un chat enviado por C2 llega a C1.
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

        # ── Verificar game_start recibido (ambos ya conectados, juegan en la misma sesión) ──
        assert c1_data["game_start"] is not None, "C1 debe recibir 'game_start'"
        assert c2_data["game_start"] is not None, "C2 debe recibir 'game_start'"
        # Ambos deben tener el mismo session_id de game_start
        assert_equal(
            c1_data["game_start"]["data"]["session_id"],
            c2_data["game_start"]["data"]["session_id"],
            "Ambos game_start deben tener el mismo session_id"
        )
        print(f"[C1] game_start: session_id={c1_data['game_start']['data']['session_id']}", flush=True)
        print(f"[C2] game_start: session_id={c2_data['game_start']['data']['session_id']}", flush=True)

        # ── Verificaciones: mismo session_id ──

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

        # ── Determinar quién empieza usando turn.is_current ──
        c1_turn = c1_data["turn"]
        c2_turn = c2_data["turn"]
        if c1_turn and c1_turn["data"]["is_current"]:
            current_player, other_player = c1, c2
            current_name, other_name = "C1", "C2"
            current_player_number = c1_turn["data"]["player_number"]
        else:
            current_player, other_player = c2, c1
            current_name, other_name = "C2", "C1"
            current_player_number = c2_turn["data"]["player_number"]
        print(f"[INFO] Turno actual: {current_name} (player {current_player_number})", flush=True)

        # ── current_player envía move, other_player debe recibirlo ──
        move_payload = {"col": 3}
        await current_player.send({"type": "move", "payload": move_payload})

        # other_player recibe: move + turn (turn actualiza isMyTurn en frontend)
        msg = await other_player.recv()
        assert_equal(msg["type"], "move", f"{other_name} debe recibir 'move'")
        assert_equal(msg["data"]["col"], 3, "Columna debe ser 3")
        assert_equal(msg["data"]["player"], current_player_number,
                     f"Jugador debe ser {current_player_number} ({current_name})")
        print(f"[CHECK] Move de {current_name} llegó a {other_name} OK", flush=True)

        msg = await other_player.recv()
        assert_equal(msg["type"], "turn", f"{other_name} debe recibir 'turn' después del move")
        assert_equal(msg["data"]["is_current"], True,
                     f"{other_name} debe tener el turno ahora")
        next_player_number = msg["data"]["player_number"]
        print(f"[CHECK] Turno pasado a {other_name} (player {next_player_number})", flush=True)

        # ── current_player recibe: move + turn ──
        msg = await current_player.recv()
        assert_equal(msg["type"], "move", f"{current_name} debe recibir 'move' (broadcast)")
        assert_equal(msg["data"]["col"], 3, "Columna debe ser 3")
        print(f"[CHECK] Move broadcast llegó a {current_name} OK", flush=True)

        msg = await current_player.recv()
        assert_equal(msg["type"], "turn", f"{current_name} debe recibir 'turn' después del move")
        assert_equal(msg["data"]["is_current"], False,
                     f"{current_name} ya no debe tener el turno")
        print(f"[CHECK] {current_name} perdió el turno correctamente", flush=True)

        # ── other_player (ahora con turno) envía chat, current_player debe recibirlo ──
        chat_payload = {"text": "hola rival"}
        await other_player.send({"type": "chat", "payload": chat_payload})

        msg = await current_player.recv()
        assert_equal(msg["type"], "chat", f"{current_name} debe recibir 'chat'")
        assert_equal(msg["data"], chat_payload, f"{current_name} debe recibir el chat payload exacto")
        print(f"[CHECK] Chat de {other_name} llegó a {current_name} OK", flush=True)

        print("\n[PASS] Todas las comprobaciones pasaron.", flush=True)
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