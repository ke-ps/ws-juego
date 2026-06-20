export type Difficulty = 'easy' | 'medium' | 'hard';

export interface ConnectedMessage {
  type: 'connected';
  data: {
    client_id: string;
    session_id: string;
    mode: 'pvp' | 'pve';
    difficulty?: Difficulty;
    board?: string[][];
    current_player?: string;
  };
}

export interface WaitingMessage {
  type: 'waiting';
  data: {
    session_id: string;
    message: string;
  };
}

export interface GameStartMessage {
  type: 'game_start';
  data: {
    session_id: string;
    mode: 'pvp' | 'pve';
    difficulty?: Difficulty;
    [key: string]: unknown;
  };
}

export interface TurnMessage {
  type: 'turn';
  data: {
    player: string;
    is_current: boolean;
  };
}

export interface MoveMessage {
  type: 'move';
  data: {
    row: number;
    col: number;
    player: 'R' | 'Y';
    board: string[][];
    next_player: 'R' | 'Y';
  };
}

export interface OpponentMoveMessage {
  type: 'opponent_move';
  data: {
    row: number;
    col: number;
    player: 'R' | 'Y';
    board: string[][];
    next_player: 'R' | 'Y';
  };
}

export interface InvalidMoveMessage {
  type: 'invalid_move';
  data: {
    message: string;
    code?: string;
  };
}

export interface GameOverMessage {
  type: 'game_over';
  data: {
    winner: 'R' | 'Y' | null;
    reason: 'win' | 'tie';
    board: string[][];
  };
}

export interface ChatMessage {
  type: 'chat';
  data: Record<string, unknown>;
  sender: string;
}

export interface OpponentDisconnectedMessage {
  type: 'opponent_disconnected';
  data: {
    client_id: string;
  };
}

export interface ErrorMessage {
  type: 'error';
  data: {
    message: string;
  };
}

export interface PongMessage {
  type: 'pong';
  data: Record<string, never>;
}

export type ServerMessage =
  | ConnectedMessage
  | WaitingMessage
  | GameStartMessage
  | TurnMessage
  | MoveMessage
  | OpponentMoveMessage
  | InvalidMoveMessage
  | GameOverMessage
  | ChatMessage
  | OpponentDisconnectedMessage
  | ErrorMessage
  | PongMessage;


export interface MoveClientMessage {
  type: 'move';
  payload: {
    col: number;
  };
}

export interface ChatClientMessage {
  type: 'chat';
  payload: Record<string, unknown>;
}

export interface PingClientMessage {
  type: 'ping';
}

export type ClientMessage =
  | MoveClientMessage
  | ChatClientMessage
  | PingClientMessage;
