"""
Gestor de sesiones/rooms y conexiones WebSocket.
"""
import json
from uuid import UUID, uuid4

from fastapi import WebSocket

from models import GameMode, Session


class SessionManager:
    """Gestor central de sesiones de juego."""

    def __init__(self) -> None:
        # Conexiones WebSocket activas: session_id -> WebSocket
        self.active_connections: dict[str, WebSocket] = {}

        # Sesiones de juego: session_id del juego -> Session
        self.sessions: dict[UUID, Session] = {}

        # Rooms por jugador: ws_session_id -> game_session_id
        self.player_rooms: dict[str, UUID] = {}

        # Salas PvP esperando segundo jugador: game_session_id
        self.waiting_rooms: list[UUID] = []

    # ── Conexiones ───────────────────────────────────────────────────────────

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Registra una nueva conexión WebSocket."""
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str) -> None:
        """Elimina una conexión WebSocket."""
        self.active_connections.pop(client_id, None)

        game_id = self.player_rooms.pop(client_id, None)
        if game_id:
            game = self.sessions.get(game_id)
            if game:
                if game.player1 == client_id:
                    game.player1 = None
                elif game.player2 == client_id:
                    game.player2 = None
                if game.player1 is None and game.player2 is None:
                    self._remove_session(game_id)
                elif game_id in self.waiting_rooms:
                    self.waiting_rooms.remove(game_id)

    # ── Sesiones ─────────────────────────────────────────────────────────────

    def _create_session(self, mode: GameMode, player_id: str) -> Session:
        """Crea una nueva sesión de juego."""
        session = Session(id=uuid4(), mode=mode, player1=player_id)
        self.sessions[session.id] = session
        return session

    def _remove_session(self, session_id: UUID) -> None:
        """Elimina una sesión."""
        self.sessions.pop(session_id, None)
        self.waiting_rooms = [rid for rid in self.waiting_rooms if rid != session_id]

    async def _notify(self, session_id: UUID, msg: dict) -> None:
        """Envía un mensaje a todos los jugadores de una sesión (awaited)."""
        for client_id in self.player_rooms:
            if self.player_rooms[client_id] == session_id:
                await self._safe_send(self.active_connections[client_id], msg)

    async def _notify_player(self, client_id: str, msg: dict) -> None:
        """Envía un mensaje a un jugador específico (awaited)."""
        ws = self.active_connections.get(client_id)
        if ws:
            await self._safe_send(ws, msg)

    async def _safe_send(self, websocket: WebSocket, msg: dict) -> None:
        """Envía un mensaje por WebSocket sin propagar excepciones."""
        try:
            await websocket.send_text(json.dumps(msg))
        except Exception:
            pass

    # ── Matchmaking ──────────────────────────────────────────────────────────

    async def join_or_create(self, websocket: WebSocket, client_id: str, mode: GameMode) -> Session:
        """
        Lógica de matchmaking:
        - PvP: busca sala esperando, o crea una nueva.
        - PvE: crea sala directamente (jugador solo).
        """
        # Caso PVE: crear sala directamente
        if mode == GameMode.PVE:
            session = self._create_session(mode, client_id)
            self.player_rooms[client_id] = session.id
            # Enviar game_start solo al cliente
            await self._notify_player(client_id, {
                "type": "game_start",
                "data": {
                    "session_id": str(session.id),
                    "mode": "pve",
                    "players": {"player1": client_id, "player2": None},
                },
            })
            return session

        # Caso PVP
        if self.waiting_rooms:
            session_id = self.waiting_rooms.pop(0)
            session = self.sessions.get(session_id)

            if session and session.player1 and not session.full:
                session.player2 = client_id
                session.full = True
                self.player_rooms[client_id] = session.id

                # Enviar game_start a AMBOS jugadores
                game_start_msg = {
                    "type": "game_start",
                    "data": {
                        "session_id": str(session.id),
                        "mode": "pvp",
                        "players": {"player1": session.player1, "player2": client_id},
                    },
                }
                await self._notify_player(session.player1, game_start_msg)
                await self._notify_player(client_id, game_start_msg)
                return session

        # No hay sala disponible → crear nueva y esperar
        session = self._create_session(mode, client_id)
        self.player_rooms[client_id] = session.id
        self.waiting_rooms.append(session.id)

        # Enviar waiting solo al cliente que crea la sala
        await self._notify_player(client_id, {
            "type": "waiting",
            "data": {"session_id": str(session.id), "message": "Esperando rival..."},
        })
        return session

    # ── Mensajería ───────────────────────────────────────────────────────────

    async def broadcast_to_session(
        self, session_id: UUID, message: dict, exclude: str | None = None
    ) -> None:
        """Reenvía un mensaje a todos los jugadores de una sesión (awaited)."""
        session = self.sessions.get(session_id)
        if not session:
            return

        tasks = []
        for player_id in [session.player1, session.player2]:
            if player_id and player_id != exclude and player_id in self.active_connections:
                ws = self.active_connections[player_id]
                tasks.append(self._safe_send(ws, message))

        if tasks:
            import asyncio
            await asyncio.gather(*tasks, return_exceptions=True)

    async def send_to_player(self, client_id: str, message: dict) -> None:
        """Envía un mensaje a un jugador concreto (awaited)."""
        ws = self.active_connections.get(client_id)
        if ws:
            await self._safe_send(ws, message)


# Instancia global (singleton)
session_manager = SessionManager()