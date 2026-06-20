"""
Router para WebSockets y lógica de juego en tiempo real.
"""
import json
from uuid import uuid4

from fastapi import APIRouter, Path, WebSocket, WebSocketDisconnect

from models import Difficulty, GameMode
from session_manager import session_manager, MoveError

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    force=True,
)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["game"])


@router.websocket("/ws/{mode}")
async def websocket_endpoint(
    websocket: WebSocket,
    mode: str = Path(..., description="Modo de juego: 'pvp' o 'pve'"),
    difficulty: str = "medium",
):
    """
    Endpoint WebSocket para unirse a una partida.

    El cliente envía JSON con:
      - type: "move" | "chat" | ...
      - payload: { ... }

    El servidor responde con:
      - type: "game_start" | "waiting" | "opponent_move" | "opponent_disconnected" | ...
      - data: { ... }

    Args:
        websocket: Conexión WebSocket del cliente.
        mode: Modo de juego ('pvp' o 'pve').
        difficulty: Dificultad de la IA ('easy', 'medium', 'hard') solo para PvE.
    """
    # Validar modo
    if mode not in ("pvp", "pve"):
        await websocket.close(code=4000, reason="Modo inválido. Usa 'pvp' o 'pve'.")
        return

    # Validar dificultad (solo para PvE, ignorada en PvP)
    try:
        difficulty_enum = Difficulty(difficulty)
    except ValueError:
        await websocket.close(code=4000, reason=f"Dificultad inválida: {difficulty}. Usa 'easy', 'medium' o 'hard'.")
        return

    game_mode = GameMode(mode)
    client_id = str(uuid4())  # ID único para este cliente
    print(f"[WS] Cliente {client_id} conectando en modo {mode}")

    # Conectar y hacer matchmaking
    await session_manager.connect(websocket, client_id)
    print(f"[WS] Cliente {client_id} conectado")
    session = await session_manager.join_or_create(websocket, client_id, game_mode, difficulty_enum)
    print(f"[WS] Cliente {client_id} joined session {session.id}")

    # Bucle de mensajes
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await session_manager.send_to_player(client_id, {
                    "type": "error",
                    "data": {"message": "JSON inválido"},
                })
                continue

            msg_type = msg.get("type", "unknown")
            logger.info("[WS_MSG] client=%s type=%s session=%s", client_id[:8], msg_type, session.id)

            if msg_type == "move":
                payload = msg.get("payload", {})
                col = payload.get("col")
                logger.info(
                    "[MOVE_RECV] client=%s session=%s col=%s",
                    client_id[:8], session.id, col,
                )

                if col is None:
                    logger.warning("[MOVE_REJECT] client=%s reason=missing_col", client_id[:8])
                    await session_manager.send_to_player(client_id, {
                        "type": "invalid_move",
                        "data": {"message": "Falta el campo 'col' en el payload"},
                    })
                    continue

                if not isinstance(col, int) or not (0 <= col < 7):
                    logger.warning("[MOVE_REJECT] client=%s col=%s reason=invalid_col", client_id[:8], col)
                    await session_manager.send_to_player(client_id, {
                        "type": "invalid_move",
                        "data": {"message": "Columna debe ser un entero entre 0 y 6"},
                    })
                    continue

                try:
                    if session.mode == GameMode.PVE:
                        await session_manager.handle_pve_move(client_id, col)
                    else:
                        await session_manager.handle_move(client_id, col)
                    logger.info("[MOVE_ACCEPTED] client=%s session=%s col=%d", client_id[:8], session.id, col)
                except MoveError as e:
                    logger.warning(
                        "[MOVE_REJECT] client=%s session=%s col=%d reason=%s code=%s",
                        client_id[:8], session.id, col, e.message, e.code,
                    )
                    await session_manager.send_to_player(client_id, {
                        "type": "invalid_move",
                        "data": {"message": e.message, "code": e.code},
                    })

            elif msg_type == "chat":
                # Mensaje de chat reenviado al rival (útil para testing)
                await session_manager.broadcast_to_session(
                    session.id,
                    {
                        "type": "chat",
                        "data": msg.get("payload", {}),
                        "sender": client_id,
                    },
                    exclude=client_id,
                )

            elif msg_type == "ping":
                await session_manager.send_to_player(client_id, {"type": "pong", "data": {}})

            else:
                await session_manager.send_to_player(client_id, {
                    "type": "error",
                    "data": {"message": f"Tipo de mensaje desconocido: {msg_type}"},
                })

    except WebSocketDisconnect:
        # El cliente se desconectó
        game_id = session_manager.player_rooms.get(client_id)
        session_manager.disconnect(client_id)

        if game_id:
            # Notificar al rival
            await session_manager.broadcast_to_session(
                game_id,
                {
                    "type": "opponent_disconnected",
                    "data": {"client_id": client_id},
                },
                exclude=client_id,
            )