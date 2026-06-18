import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-lobby',
  standalone: true,
  imports: [],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './lobby.html',
  styleUrl: './lobby.scss',
})
export class Lobby {
  readonly status = input<'connecting' | 'connected' | 'waiting' | 'in_game'>('connecting');
  readonly clientId = input<string | null>(null);
  readonly sessionId = input<string | null>(null);
  readonly waitingMessage = input<string | null>(null);
}
