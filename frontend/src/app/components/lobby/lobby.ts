import { ChangeDetectionStrategy, Component, input, output, signal } from '@angular/core';
import { Difficulty } from '../../core/websocket.types';

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

  readonly startGame = output<{ mode: 'pvp' | 'pve'; difficulty: Difficulty }>();
  readonly back = output<void>();

  protected readonly selectedMode = signal<'pvp' | 'pve'>('pvp');
  protected readonly selectedDifficulty = signal<Difficulty>('medium');

  protected onModeChange(mode: 'pvp' | 'pve'): void {
    this.selectedMode.set(mode);
  }

  protected onDifficultyChange(difficulty: Difficulty): void {
    this.selectedDifficulty.set(difficulty);
  }

  protected onStart(): void {
    this.startGame.emit({
      mode: this.selectedMode(),
      difficulty: this.selectedDifficulty(),
    });
  }

  protected onBack(): void {
    this.back.emit();
  }
}
