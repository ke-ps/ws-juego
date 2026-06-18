import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-board',
  standalone: true,
  imports: [],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './board.html',
  styleUrl: './board.scss',
})
export class Board {
  readonly board = input<string[][]>([]);
}
