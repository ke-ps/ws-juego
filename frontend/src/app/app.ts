import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  signal,
} from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { WebsocketService } from './services/websocket';
import { ServerMessage } from './core/websocket.types';

interface LogEntry {
  time: string;
  type: string;
  raw: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet], // 👈 IMPORTANTE
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
  protected readonly logs = signal<LogEntry[]>([]);

  constructor() {
    this.ws.connect();

    this.destroyRef.onDestroy(() => this.ws.disconnect());

    this.ws
      .messages()
      .pipe(takeUntilDestroyed())
      .subscribe((msg: ServerMessage) => {
        this.addLog(msg);
        this.handleStatus(msg);
      });
  }

  private handleStatus(msg: ServerMessage): void {
    switch (msg.type) {
      case 'connected':
        this.status.set('connected');
        this.clientId.set(msg.data.client_id);
        this.sessionId.set(msg.data.session_id);
        break;

      case 'waiting':
        this.status.set('waiting');
        break;

      case 'game_start':
        this.status.set('in_game');
        break;
    }
  }

  private addLog(msg: ServerMessage): void {
    const entry: LogEntry = {
      time: new Date().toLocaleTimeString('es-ES'),
      type: msg.type,
      raw: JSON.stringify(msg, null, 2),
    };

    this.logs.update((current) => [entry, ...current].slice(0, 30));
  }
}