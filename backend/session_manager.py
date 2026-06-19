"""
Gestor de sesiones/rooms y conexiones WebSocket.
"""
import json
import logging
from uuid import UUID, uuid4

from fastapi import WebSocket

from models import GameMode, Session
from connect4_game import Connect4Game

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class MoveError(Exception):
    """Error al procesar un movimiento."""

    def __init__(self, message: str, code: str = "invalid_move"):
        self.message = message
        self.code = code
        super().__init__(self.message)


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

        Envía 'connected' a cada jugador ANTES de waiting/game_start
        para garantizar el orden correcto de mensajes.
        """
        # Caso PVE: crear sala directamente
        if mode == GameMode.PVE:
            session = self._create_session(mode, client_id)
            self.player_rooms[client_id] = session.id
            # Enviar connected antes que game_start
            await self._notify_player(client_id, {
                "type": "connected",
                "data": {
                    "client_id": client_id,
                    "session_id": str(session.id),
                    "mode": "pve",
                },
            })
            # Inicializar el juego
            self.init_game(session)
            # Enviar game_start solo al cliente
            await self._notify_player(client_id, {
                "type": "game_start",
                "data": {
                    "session_id": str(session.id),
                    "mode": "pve",
                    "players": {"player1": client_id, "player2": None},
                    "board": session.game.board,
                    "current_player": "R",
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

                # Enviar connected solo al nuevo jugador (player2)
                # player1 ya recibió connected cuando creó la sala
                await self._notify_player(client_id, {
                    "type": "connected",
                    "data": {
                        "client_id": client_id,
                        "session_id": str(session.id),
                        "mode": "pvp",
                    },
                })

                # Inicializar el juego cuando ambos jugadores están conectados
                self.init_game(session)

                # Enviar game_start a AMBOS jugadores con tablero inicial
                game_start_msg = {
                    "type": "game_start",
                    "data": {
                        "session_id": str(session.id),
                        "mode": "pvp",
                        "players": {"player1": session.player1, "player2": client_id},
                        "board": session.game.board,
                        "current_player": "R",  # Rojo siempre empieza
                    },
                }
                await self._notify_player(session.player1, game_start_msg)
                await self._notify_player(client_id, game_start_msg)

                # Notificar el turno al jugador 1 (quien empieza)
                await self._notify_player(session.player1, {
                    "type": "turn",
                    "data": {
                        "player": session.player1,
                        "is_current": True,
                        "player_number": "R",
                    },
                })
                await self._notify_player(session.player2, {
                    "type": "turn",
                    "data": {
                        "player": session.player2,
                        "is_current": False,
                        "player_number": "Y",
                    },
                })
                return session

        # No hay sala disponible → crear nueva y esperar
        session = self._create_session(mode, client_id)
        self.player_rooms[client_id] = session.id
        self.waiting_rooms.append(session.id)

        # Enviar connected antes que waiting
        await self._notify_player(client_id, {
            "type": "connected",
            "data": {
                "client_id": client_id,
                "session_id": str(session.id),
                "mode": "pvp",
            },
        })

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

    # ── Gestión de partida ────────────────────────────────────────────────────

    def init_game(self, session: Session) -> None:
        """Inicializa el motor de juego para una sesión."""
        session.game = Connect4Game()
        session.is_over = False

    def _validate_column(self, col: int) -> None:
        """Valida que la columna esté dentro de los límites."""
        if not (0 <= col < 7):
            raise MoveError(f"Columna {col} fuera de rango (0-6)", "invalid_column")

    def _validate_not_full(self, session: Session, col: int) -> None:
        """Valida que la columna no esté llena."""
        if session.game.board[0][col] != ' ':
            raise MoveError(f"Columna {col} llena", "column_full")

    def _validate_turn(self, session: Session, client_id: str) -> None:
        """Valida que sea el turno del jugador."""
        expected_player = session.game.current_player
        player_number = session.get_player_number(client_id)
        logger.info(
            "[TURN_CHECK] session=%s client=%s expected=%s actual=%s room_id=%s",
            session.id, client_id[:8], expected_player, player_number,
            session.id,
        )
        if expected_player != player_number:
            logger.warning(
                "[TURN_REJECT] session=%s client=%s expected=%s actual=%s",
                session.id, client_id[:8], expected_player, player_number,
            )
            raise MoveError("No es tu turno", "not_your_turn")

    async def handle_move(self, client_id: str, col: int) -> dict:
        """
        Procesa un movimiento de un jugador.
        """
        # Obtener sesión del jugador
        session_id = self.player_rooms.get(client_id)
        if not session_id:
            logger.warning("[MOVE_REJECT] client=%s reason=no_session", client_id[:8])
            raise MoveError("No estás en ninguna partida", "no_session")

        session = self.sessions.get(session_id)
        if not session:
            logger.warning("[MOVE_REJECT] session=%s reason=not_found", session_id)
            raise MoveError("Sesión no encontrada", "no_session")

        if not session.game:
            logger.warning("[MOVE_REJECT] session=%s reason=game_not_started", session.id)
            raise MoveError("Partida no inicializada", "game_not_started")

        if session.is_over:
            logger.warning("[MOVE_REJECT] session=%s reason=game_over", session.id)
            raise MoveError("La partida ha terminado", "game_over")

        # Log pre-move state
        player_number = session.get_player_number(client_id)
        logger.info(
            "[MOVE_BEFORE] session=%s room=%s client=%s player=%s col=%d current_player=%s p1=%s p2=%s",
            session.id, session_id, client_id[:8], player_number, col,
            session.game.current_player,
            session.player1[:8] if session.player1 else None,
            session.player2[:8] if session.player2 else None,
        )

        # Validar movimiento
        self._validate_column(col)
        self._validate_not_full(session, col)
        self._validate_turn(session, client_id)

        # Determinar la fila donde caerá la pieza
        row = None
        for r in range(session.game.rows - 1, -1, -1):
            if session.game.board[r][col] == ' ':
                row = r
                break

        # Insertar pieza
        session.game.board[row][col] = player_number

        # Preparar respuesta del movimiento
        move_result = {
            "row": row,
            "col": col,
            "player": player_number,
        }

        # Verificar victoria
        if session.game.check_winner():
            session.is_over = True
            logger.info(
                "[MOVE_WIN] session=%s winner=%s player=%s col=%d row=%d",
                session.id, player_number, client_id[:8], col, row,
            )
            await self.broadcast_to_session(
                session.id,
                {
                    "type": "game_over",
                    "data": {
                        "winner": player_number,
                        "reason": "win",
                        "board": session.game.board,
                    },
                },
            )
            return move_result

        # Verificar empate
        if session.game.check_tie():
            session.is_over = True
            logger.info("[MOVE_TIE] session=%s", session.id)
            await self.broadcast_to_session(
                session.id,
                {
                    "type": "game_over",
                    "data": {
                        "winner": None,
                        "reason": "tie",
                        "board": session.game.board,
                    },
                },
            )
            return move_result

        # Cambiar turno
        old_player = session.game.current_player
        session.game.current_player = 'Y' if session.game.current_player == 'R' else 'R'
        next_player = session.game.current_player
        logger.info(
            "[MOVE_AFTER] session=%s client=%s col=%d turn_switch: %s -> %s",
            session.id, client_id[:8], col, old_player, next_player,
        )

        # Enviar evento move a AMBOS jugadores (para actualizar sus tableros)
        await self.broadcast_to_session(
            session.id,
            {
                "type": "move",
                "data": {
                    **move_result,
                    "board": session.game.board,
                    "next_player": next_player,
                },
            },
        )

        # Enviar turno a cada jugador individualmente
        # El frontend solo actualiza isMyTurn con mensajes type "turn"
        is_r_turn = (next_player == 'R')
        await self._notify_player(session.player1, {
            "type": "turn",
            "data": {
                "player": session.player1,
                "is_current": is_r_turn,
                "player_number": "R",
            },
        })
        logger.info(
            "[TURN_SENT] session=%s to=%s (player1, R) is_current=%s",
            session.id, session.player1[:8] if session.player1 else None, is_r_turn,
        )
        await self._notify_player(session.player2, {
            "type": "turn",
            "data": {
                "player": session.player2,
                "is_current": not is_r_turn,
                "player_number": "Y",
            },
        })
        logger.info(
            "[TURN_SENT] session=%s to=%s (player2, Y) is_current=%s",
            session.id, session.player2[:8] if session.player2 else None, not is_r_turn,
        )

        return move_result

    async def handle_pve_move(self, client_id: str, col: int) -> dict:
        """
        Procesa un movimiento en modo PVE (jugador vs IA).
        Por ahora, la IA simplemente escoge una columna aleatoria válida.
        """
        session_id = self.player_rooms.get(client_id)
        if not session_id:
            raise MoveError("No estás en ninguna partida", "no_session")

        session = self.sessions.get(session_id)
        if not session or not session.game:
            raise MoveError("Partida no inicializada", "game_not_started")

        if session.is_over:
            raise MoveError("La partida ha terminado", "game_over")

        # Movimiento del jugador humano
        self._validate_column(col)
        self._validate_not_full(session, col)
        self._validate_turn(session, client_id)

        # El jugador humano siempre es 'R'
        row = None
        for r in range(session.game.rows - 1, -1, -1):
            if session.game.board[r][col] == ' ':
                row = r
                break

        session.game.board[row][col] = 'R'

        move_result = {
            "row": row,
            "col": col,
            "player": 'R',
        }

        # Verificar victoria del jugador
        if session.game.check_winner():
            session.is_over = True
            await self.send_to_player(
                client_id,
                {
                    "type": "game_over",
                    "data": {
                        "winner": 'R',
                        "reason": "win",
                        "board": session.game.board,
                    },
                },
            )
            return move_result

        # Verificar empate
        if session.game.check_tie():
            session.is_over = True
            await self.send_to_player(
                client_id,
                {
                    "type": "game_over",
                    "data": {
                        "winner": None,
                        "reason": "tie",
                        "board": session.game.board,
                    },
                },
            )
            return move_result

        # Turno de la IA (simple: columna aleatoria válida)
        import random

        valid_cols = [c for c in range(7) if session.game.board[0][c] == ' ']
        if not valid_cols:
            return move_result

        ai_col = random.choice(valid_cols)
        ai_row = None
        for r in range(session.game.rows - 1, -1, -1):
            if session.game.board[r][ai_col] == ' ':
                ai_row = r
                break

        session.game.board[ai_row][ai_col] = 'Y'

        # Enviar movimiento de la IA al jugador
        await self.send_to_player(
            client_id,
            {
                "type": "opponent_move",
                "data": {
                    "row": ai_row,
                    "col": ai_col,
                    "player": 'Y',
                    "board": session.game.board,
                    "next_player": 'R',
                },
            },
        )

        # Verificar victoria de la IA
        if session.game.check_winner():
            session.is_over = True
            await self.send_to_player(
                client_id,
                {
                    "type": "game_over",
                    "data": {
                        "winner": 'Y',
                        "reason": "win",
                        "board": session.game.board,
                    },
                },
            )
            return move_result

        # Verificar empate tras movimiento de IA
        if session.game.check_tie():
            session.is_over = True
            await self.send_to_player(
                client_id,
                {
                    "type": "game_over",
                    "data": {
                        "winner": None,
                        "reason": "tie",
                        "board": session.game.board,
                    },
                },
            )

        return move_result


# Instancia global (singleton)
session_manager = SessionManager()