import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { WebsocketService } from './services/websocket';
import { ServerMessage } from './core/websocket.types';
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

  constructor() {
    this.ws.connect();

    this.destroyRef.onDestroy(() => this.ws.disconnect());

    this.ws
      .messages()
      .pipe(takeUntilDestroyed())
      .subscribe((msg: ServerMessage) => {
        this.handleMessage(msg);
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
        break;

      case 'move':
        this.board.set(msg.data.board);
        break;

      case 'game_over':
        this.board.set(msg.data.board);
        break;
    }
  }
}
