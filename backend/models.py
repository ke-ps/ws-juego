"""
Modelos de datos para el juego.
"""
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel


class GameMode(str, Enum):
    """Modos de juego disponibles."""

    PVP = "pvp"  # Dos jugadores humanos
    PVE = "pve"  # Jugador humano vs IA


class Difficulty(str, Enum):
    """Niveles de dificultad para la IA."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Session(BaseModel):
    """Representa una sesión/partida."""

    id: UUID = uuid4()
    mode: GameMode
    player1: str | None = None  # WebSocket session_id del jugador 1
    player2: str | None = None  # WebSocket session_id del jugador 2 (null en PVE hasta que llegue IA)
    full: bool = False  # True cuando ambos jugadores están conectados (PvP) o jugador listo (PvE)
    game: Any | None = None  # Instancia del motor de juego (Connect4Game)
    is_over: bool = False  # True cuando la partida ha terminado
    difficulty: Difficulty = Difficulty.MEDIUM  # Dificultad IA (solo PvE)

    def is_pvp(self) -> bool:
        return self.mode == GameMode.PVP

    def is_pve(self) -> bool:
        return self.mode == GameMode.PVE

    def get_player_number(self, client_id: str) -> str:
        """Retorna 'R' o 'Y' según el client_id del jugador."""
        if self.player1 == client_id:
            return 'R'
        if self.player2 == client_id:
            return 'Y'
        raise ValueError(f"Client {client_id} no pertenece a esta sesión")


class WSMessage(BaseModel):
    """Mensaje enviado por WebSocket."""

    type: str
    payload: dict | None = None


class WSOutgoingMessage(BaseModel):
    """Mensaje enviado por el servidor a los clientes."""

    type: str
    data: dict | None = None
    sender: str | None = None  # "server", session_id del emisor, etc.