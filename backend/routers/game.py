"""
Router para WebSockets y lógica de juego en tiempo real.
"""
import json
from uuid import uuid4

from fastapi import APIRouter, Path, WebSocket, WebSocketDisconnect

from models import GameMode
from session_manager import session_manager, MoveError

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["game"])


@router.websocket("/ws/{mode}")
async def websocket_endpoint(
    websocket: WebSocket,
    mode: str = Path(..., description="Modo de juego: 'pvp' o 'pve'"),
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
    """
    # Validar modo
    if mode not in ("pvp", "pve"):
        await websocket.close(code=4000, reason="Modo inválido. Usa 'pvp' o 'pve'.")
        return

    game_mode = GameMode(mode)
    client_id = str(uuid4())  # ID único para este cliente
    print(f"[WS] Cliente {client_id} conectando en modo {mode}")

    # Conectar y hacer matchmaking
    await session_manager.connect(websocket, client_id)
    print(f"[WS] Cliente {client_id} conectado")
    session = await session_manager.join_or_create(websocket, client_id, game_mode)
    print(f"[WS] Cliente {client_id} joined session {session.id}")

    # Enviar confirmación de conexión al cliente
    connected_data = {
        "client_id": client_id,
        "session_id": str(session.id),
        "mode": session.mode.value,
    }

    # Incluir tablero inicial para modos donde el juego ya empezó
    if session.game:
        connected_data["board"] = session.game.board
        connected_data["current_player"] = session.game.current_player

    await session_manager.send_to_player(client_id, {
        "type": "connected",
        "data": connected_data,
    })

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

            if msg_type == "move":
                # Extraer columna del payload
                payload = msg.get("payload", {})
                col = payload.get("col")

                if col is None:
                    await session_manager.send_to_player(client_id, {
                        "type": "invalid_move",
                        "data": {"message": "Falta el campo 'col' en el payload"},
                    })
                    continue

                # Verificar que col sea un número entero válido
                if not isinstance(col, int) or not (0 <= col < 7):
                    await session_manager.send_to_player(client_id, {
                        "type": "invalid_move",
                        "data": {"message": "Columna debe ser un entero entre 0 y 6"},
                    })
                    continue

                # Procesar movimiento según el modo de juego
                try:
                    if session.mode == GameMode.PVE:
                        # En PVE, el servidor maneja tanto el movimiento del jugador como el de la IA
                        await session_manager.handle_pve_move(client_id, col)
                    else:
                        # En PvP, procesar el movimiento normal
                        await session_manager.handle_move(client_id, col)
                except MoveError as e:
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