import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

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
  readonly disabled = input(false);
  readonly columnSelected = output<number>();

  protected selectColumn(col: number): void {
    if (this.disabled()) return;
    this.columnSelected.emit(col);
  }
}
