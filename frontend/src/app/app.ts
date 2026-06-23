import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { WebsocketService } from './services/websocket';
import { Difficulty, ServerMessage } from './core/websocket.types';
import { Lobby } from './components/lobby/lobby';
import { Board } from './components/board/board';

const ROWS = 6;
const COLS = 7;

function emptyBoard(): string[][] {
  return Array.from({ length: ROWS }, () => Array(COLS).fill(''));
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [Lobby, Board],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  private readonly ws = inject(WebsocketService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly status = signal<'connecting' | 'waiting' | 'connected' | 'in_game'>('connecting');
  protected readonly clientId = signal<string | null>(null);
  protected readonly sessionId = signal<string | null>(null);
  protected readonly waitingMessage = signal<string | null>(null);
  protected readonly board = signal<string[][]>(emptyBoard());
  protected readonly isMyTurn = signal(false);
  protected readonly winner = signal<'R' | 'Y' | null | undefined>(undefined);
  protected readonly errorMessage = signal<string | null>(null);
  protected readonly opponentDisconnected = signal(false);
  protected readonly socketConnected = signal(false);
  protected readonly mode = signal<'pvp' | 'pve'>('pvp');

  protected onStartGame(params: { mode: 'pvp' | 'pve'; difficulty: Difficulty }): void {
    this.mode.set(params.mode);
    this.status.set('connecting');
    this.ws.connect(params.mode, params.difficulty);
  }

  protected onColumnSelected(col: number): void {
    this.ws.send({ type: 'move', payload: { col } });
    if (this.mode() === 'pve') {
      this.isMyTurn.set(false);
    }
  }

  protected onDismissError(): void {
    this.errorMessage.set(null);
  }

  protected onBack(): void {
    this.ws.disconnect();
    this.status.set('connecting');
    this.clientId.set(null);
    this.sessionId.set(null);
    this.waitingMessage.set(null);
    this.board.set(emptyBoard());
    this.isMyTurn.set(false);
    this.winner.set(undefined);
    this.errorMessage.set(null);
    this.opponentDisconnected.set(false);
  }

  protected onRestart(): void {
    this.onBack();
  }

  constructor() {
    this.destroyRef.onDestroy(() => this.ws.disconnect());

    this.ws
      .messages()
      .pipe(takeUntilDestroyed())
      .subscribe((msg: ServerMessage) => {
        this.handleMessage(msg);
      });

    this.ws
      .connectionStatus()
      .pipe(takeUntilDestroyed())
      .subscribe((connected) => {
        this.socketConnected.set(connected);
        if (!connected && this.status() !== 'connecting') {
          this.errorMessage.set('Conexión perdida con el servidor');
        }
      });
  }

  private handleMessage(msg: ServerMessage): void {
    switch (msg.type) {
      case 'connected':
        this.status.set('connected');
        this.clientId.set(msg.data.client_id);
        this.sessionId.set(msg.data.session_id);
        break;

      case 'waiting':
        this.status.set('waiting');
        this.waitingMessage.set(msg.data.message);
        break;

      case 'game_start':
        this.status.set('in_game');
        if (msg.data['board']) {
          this.board.set(msg.data['board'] as string[][]);
        }
        if (this.mode() === 'pve') {
          this.isMyTurn.set(true);
        }
        break;

      case 'move':
        this.board.set(msg.data.board);
        break;

      case 'opponent_move':
        this.board.set(msg.data.board);
        this.isMyTurn.set(true);
        break;

      case 'turn':
        this.isMyTurn.set(msg.data.is_current);
        break;

      case 'game_over':
        this.board.set(msg.data.board);
        this.isMyTurn.set(false);
        this.winner.set(msg.data.winner);
        break;

      case 'invalid_move':
        this.errorMessage.set(msg.data.message);
        if (this.mode() === 'pve') {
          this.isMyTurn.set(true);
        }
        break;

      case 'error':
        this.errorMessage.set(msg.data.message);
        break;

      case 'opponent_disconnected':
        this.opponentDisconnected.set(true);
        break;
    }
  }
}
