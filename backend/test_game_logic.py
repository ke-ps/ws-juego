"""Test completo de la lógica PvP."""
import asyncio
import json
import sys
import os

# Ensure the backend is in path
sys.path.insert(0, os.path.dirname(__file__))

import websockets


class TestError(AssertionError):
    pass


def assert_equal(actual, expected, msg: str):
    if actual != expected:
        raise TestError(f"{msg}: esperado {expected!r}, obtenido {actual!r}")


class WSClient:
    def __init__(self, uri: str, name: str):
        self.uri = uri
        self.name = name
        self.ws = None
        self.client_id = None
        self.session_id = None
        self.messages = []

    async def connect(self):
        self.ws = await websockets.connect(self.uri)
        print(f"[{self.name}] Conectado.", flush=True)

    async def recv(self, timeout: float = 5.0) -> dict:
        msg = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
        data = json.loads(msg)
        self.messages.append(data)
        print(f"[{self.name}] recv: {json.dumps(data, separators=(',', ':'))}", flush=True)
        return data

    async def send(self, payload: dict):
        await self.ws.send(json.dumps(payload))
        print(f"[{self.name}] send: {json.dumps(payload, separators=(',', ':'))}", flush=True)

    async def close(self):
        if self.ws:
            await self.ws.close()
        print(f"[{self.name}] Desconectado.", flush=True)


async def collect_messages(client: WSClient, target_types: list[str]) -> dict:
    """Recolecta mensajes hasta tener todos los tipos objetivo."""
    result = {t: None for t in target_types}
    result["messages"] = []

    for _ in range(10):
        msg = await client.recv()
        result["messages"].append(msg)
        for t in target_types:
            if msg["type"] == t and result[t] is None:
                result[t] = msg
        # Check if we have all required messages
        if all(result[t] is not None for t in target_types if t != "messages"):
            break
    return result


async def pvp_game_test():
    """Test completo de una partida PvP."""
    c1 = WSClient("ws://localhost:8000/ws/pvp", "C1")
    c2 = WSClient("ws://localhost:8000/ws/pvp", "C2")

    try:
        # Connect both clients
        await asyncio.gather(c1.connect(), c2.connect())
        print("[MAIN] Ambos conectados.", flush=True)

        # Collect messages from both
        c1_data, c2_data = await asyncio.gather(
            collect_messages(c1, ["connected", "game_start"]),
            collect_messages(c2, ["connected", "game_start"]),
        )

        # Verify connected messages
        assert c1_data["connected"] is not None, "C1 debe recibir 'connected'"
        assert c2_data["connected"] is not None, "C2 debe recibir 'connected'"
        c1.client_id = c1_data["connected"]["data"]["client_id"]
        c1.session_id = c1_data["connected"]["data"]["session_id"]
        c2.client_id = c2_data["connected"]["data"]["client_id"]
        c2.session_id = c2_data["connected"]["data"]["session_id"]
        print(f"[C1] client_id={c1.client_id}", flush=True)
        print(f"[C2] client_id={c2.client_id}", flush=True)

        # Consume any pending turn messages (sent after game_start)
        for c in [c1, c2]:
            while True:
                try:
                    msg = await asyncio.wait_for(c.recv(), timeout=0.5)
                    print(f"[{c.name}] Mensaje pendiente: {msg['type']}", flush=True)
                    if msg["type"] not in ["turn"]:
                        break
                except asyncio.TimeoutError:
                    break

        # Verify game_start messages
        assert c1_data["game_start"] is not None, "C1 debe recibir 'game_start'"
        assert c2_data["game_start"] is not None, "C2 debe recibir 'game_start'"

        # Verify same session
        assert_equal(c1.session_id, c2.session_id, "Ambos deben compartir el mismo session_id")

        # Verify board in game_start
        board1 = c1_data["game_start"]["data"].get("board")
        board2 = c2_data["game_start"]["data"].get("board")
        assert board1 is not None, "game_start debe incluir board"
        assert_equal(board1, board2, "Ambos tableros deben ser iguales")
        print("[CHECK] Matchmaking OK", flush=True)

        # Determine who is player1 (R) and player2 (Y) from game_start
        players = c1_data["game_start"]["data"]["players"]
        player1_id = players["player1"]
        player2_id = players["player2"]
        print(f"[INFO] player1={player1_id[:8]}..., player2={player2_id[:8]}...", flush=True)

        # Test turn validation: player2 tries to move first (should fail)
        # The player who is NOT player1 (i.e., player2) should NOT be able to move first
        if c2.client_id == player2_id:
            # C2 is player2, should not be able to move first
            await c2.send({"type": "move", "payload": {"col": 3}})
            msg = await c2.recv()
            assert_equal(msg["type"], "invalid_move", "C2 (player2) debe recibir 'invalid_move'")
            assert_equal(msg["data"]["code"], "not_your_turn", "Código debe ser 'not_your_turn'")
            print("[CHECK] Turn validation OK (C2=player2, tried to move first)", flush=True)
            mover, waitrer = c1, c2
        else:
            # C1 is player2, should not be able to move first
            await c1.send({"type": "move", "payload": {"col": 3}})
            msg = await c1.recv()
            assert_equal(msg["type"], "invalid_move", "C1 (player2) debe recibir 'invalid_move'")
            assert_equal(msg["data"]["code"], "not_your_turn", "Código debe ser 'not_your_turn'")
            print("[CHECK] Turn validation OK (C1=player2, tried to move first)", flush=True)
            mover, waitrer = c2, c1

        # player1 makes the first valid move
        await mover.send({"type": "move", "payload": {"col": 3}})

        # Both should receive move event
        mover_move = await mover.recv()
        waitrer_move = await waitrer.recv()
        print(f"[mover] Move response: {mover_move}", flush=True)
        print(f"[waitrer] Move response: {waitrer_move}", flush=True)

        assert_equal(mover_move["type"], "move", "mover debe recibir 'move'")
        assert_equal(waitrer_move["type"], "move", "waitrer debe recibir 'move'")
        assert_equal(mover_move["data"]["col"], 3, "Columna debe ser 3")
        assert_equal(mover_move["data"]["player"], "R", "Jugador R hace el primer movimiento")
        print("[CHECK] Move processing OK", flush=True)

        # Now the other player can move
        await waitrer.send({"type": "move", "payload": {"col": 4}})

        # Collect move responses from both
        mover_move2 = await mover.recv()
        waitrer_move2 = await waitrer.recv()
        assert_equal(mover_move2["type"], "move", "mover debe recibir move de waitrer")
        assert_equal(waitrer_move2["type"], "move", "waitrer debe recibir confirmacion de su move")
        assert_equal(waitrer_move2["data"]["col"], 4, "Columna 4")
        assert_equal(waitrer_move2["data"]["player"], "Y", "Jugador Y hace el segundo movimiento")
        print("[CHECK] Turn alternation OK", flush=True)

        print("\n[PASS] Todas las pruebas pasaron!", flush=True)
        return ["PASS"]

    except Exception as e:
        msg = f"[FAIL] {type(e).__name__}: {e}"
        print(msg, flush=True)
        import traceback
        traceback.print_exc()
        return ["FAIL", msg]
    finally:
        await c1.close()
        await c2.close()


async def main():
    print("=" * 60, flush=True)
    print("TEST PvP: Partida completa", flush=True)
    print("=" * 60, flush=True)

    result = await asyncio.wait_for(pvp_game_test(), timeout=30.0)
    print("=" * 60, flush=True)
    print(f"Resultado: {result[0]}", flush=True)
    print("=" * 60, flush=True)

    if result[0] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
