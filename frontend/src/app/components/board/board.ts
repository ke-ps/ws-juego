import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { WebsocketService } from '../../services/websocket';
import { ServerMessage } from '../../core/websocket.types';

const ROWS = 6;
const COLS = 7;

function emptyBoard(): string[][] {
  return Array.from({ length: ROWS }, () => Array(COLS).fill(''));
}

@Component({
  selector: 'app-board',
  standalone: true,
  imports: [],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './board.html',
  styleUrl: './board.scss',
})
export class Board {
  private readonly ws = inject(WebsocketService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly board = signal<string[][]>(emptyBoard());

  constructor() {
    this.ws.connect();

    this.ws
      .messages()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((msg: ServerMessage) => {
        this.handleMessage(msg);
      });
  }

  private handleMessage(msg: ServerMessage): void {
    switch (msg.type) {
      case 'game_start':
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
