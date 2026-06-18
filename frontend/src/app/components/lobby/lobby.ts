import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { WebsocketService } from '../../services/websocket';
import { ServerMessage } from '../../core/websocket.types';

@Component({
  selector: 'app-lobby',
  standalone: true,
  imports: [],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './lobby.html',
  styleUrl: './lobby.scss',
})
export class Lobby {
  private readonly ws = inject(WebsocketService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly status = signal<'connecting' | 'connected' | 'waiting'>('connecting');
  protected readonly clientId = signal<string | null>(null);
  protected readonly sessionId = signal<string | null>(null);
  protected readonly waitingMessage = signal<string | null>(null);

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
      case 'connected':
        this.status.set('connected');
        this.clientId.set(msg.data.client_id);
        this.sessionId.set(msg.data.session_id);
        this.waitingMessage.set(null);
        break;

      case 'waiting':
        this.status.set('waiting');
        this.waitingMessage.set(msg.data.message);
        break;
    }
  }
}
