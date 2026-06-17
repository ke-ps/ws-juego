"""
Router para WebSockets y lógica de juego en tiempo real.
"""
import json
from uuid import uuid4

from fastapi import APIRouter, Path, WebSocket, WebSocketDisconnect

from models import GameMode
from session_manager import session_manager

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

    # Conectar y hacer matchmaking
    await session_manager.connect(websocket, client_id)
    session = await session_manager.join_or_create(websocket, client_id, game_mode)

    # Enviar confirmación de conexión al cliente
    await session_manager.send_to_player(client_id, {
        "type": "connected",
        "data": {
            "client_id": client_id,
            "session_id": str(session.id),
            "mode": session.mode.value,
        },
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
                # Fase 3: aquí irá la lógica del juego
                # Por ahora reenviamos al rival como prueba
                await session_manager.broadcast_to_session(
                    session.id,
                    {
                        "type": "opponent_move",
                        "data": msg.get("payload", {}),
                    },
                    exclude=client_id,
                )

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