import copy

ROWS = 6
COLS = 7


class Connect4Game:
    def __init__(self):
        self.rows = ROWS
        self.cols = COLS
        self.board = [[' ' for _ in range(self.cols)] for _ in range(self.rows)]
        self.current_player = 'R'  # Red player starts

    def insert_piece(self, col):
        if not (0 <= col < self.cols):
            raise ValueError("Invalid column")

        for row in range(self.rows - 1, -1, -1):
            if self.board[row][col] == ' ':
                self.board[row][col] = self.current_player
                self.current_player = 'Y' if self.current_player == 'R' else 'R'
                return True
        raise ValueError("Column is full")

    def check_winner(self):
        # Check horizontal
        for row in range(self.rows):
            for col in range(self.cols - 3):
                if self.board[row][col] == self.board[row][col + 1] == self.board[row][col + 2] == self.board[row][col + 3] != ' ':
                    return True

        # Check vertical
        for col in range(self.cols):
            for row in range(self.rows - 3):
                if self.board[row][col] == self.board[row + 1][col] == self.board[row + 2][col] == self.board[row + 3][col] != ' ':
                    return True

        # Check diagonals
        for row in range(self.rows - 3):
            for col in range(self.cols - 3):
                if self.board[row][col] == self.board[row + 1][col + 1] == self.board[row + 2][col + 2] == self.board[row + 3][col + 3] != ' ':
                    return True
                if self.board[row][col + 3] == self.board[row + 1][col + 2] == self.board[row + 2][col + 1] == self.board[row + 3][col] != ' ':
                    return True

        return False

    def check_tie(self):
        return all(self.board[0][col] != ' ' for col in range(self.cols))

    def print_board(self):
        for row in self.board:
            print('|'.join(row))
        print('-----' * self.cols)


# ── Funciones de utilidad para Minimax (operan sobre tableros arbitrarios) ──

def get_valid_moves(board: list[list[str]]) -> list[int]:
    return [c for c in range(COLS) if board[0][c] == ' ']


def clone_board(board: list[list[str]]) -> list[list[str]]:
    return copy.deepcopy(board)


def make_move_on_board(board: list[list[str]], col: int, player: str) -> int | None:
    for row in range(ROWS - 1, -1, -1):
        if board[row][col] == ' ':
            board[row][col] = player
            return row
    return None


def is_terminal(board: list[list[str]]) -> bool:
    return _check_winner_on_board(board) is not None or all(board[0][c] != ' ' for c in range(COLS))


def _check_winner_on_board(board: list[list[str]]) -> str | None:
    for row in range(ROWS):
        for col in range(COLS - 3):
            if board[row][col] != ' ' and board[row][col] == board[row][col + 1] == board[row][col + 2] == board[row][col + 3]:
                return board[row][col]
    for col in range(COLS):
        for row in range(ROWS - 3):
            if board[row][col] != ' ' and board[row][col] == board[row + 1][col] == board[row + 2][col] == board[row + 3][col]:
                return board[row][col]
    for row in range(ROWS - 3):
        for col in range(COLS - 3):
            if board[row][col] != ' ' and board[row][col] == board[row + 1][col + 1] == board[row + 2][col + 2] == board[row + 3][col + 3]:
                return board[row][col]
            if board[row][col + 3] != ' ' and board[row][col + 3] == board[row + 1][col + 2] == board[row + 2][col + 1] == board[row + 3][col]:
                return board[row][col + 3]
    return None


def evaluate_board(board: list[list[str]], ai_player: str) -> int:
    opponent = 'Y' if ai_player == 'R' else 'R'
    score = 0

    for row in range(ROWS):
        for col in range(COLS - 3):
            window = [board[row][c] for c in range(col, col + 4)]
            score += _score_window(window, ai_player, opponent)

    for col in range(COLS):
        for row in range(ROWS - 3):
            window = [board[r][col] for r in range(row, row + 4)]
            score += _score_window(window, ai_player, opponent)

    for row in range(ROWS - 3):
        for col in range(COLS - 3):
            window = [board[row + d][col + d] for d in range(4)]
            score += _score_window(window, ai_player, opponent)

    for row in range(3, ROWS):
        for col in range(COLS - 3):
            window = [board[row - d][col + d] for d in range(4)]
            score += _score_window(window, ai_player, opponent)

    return score


def _score_window(window: list[str], ai: str, opponent: str) -> int:
    ai_count = window.count(ai)
    opp_count = window.count(opponent)
    empty_count = window.count(' ')

    if ai_count == 4:
        return 1000
    if opp_count == 4:
        return -1000
    if ai_count == 3 and empty_count == 1:
        return 100
    if opp_count == 3 and empty_count == 1:
        return -100
    if ai_count == 2 and empty_count == 2:
        return 10
    if opp_count == 2 and empty_count == 2:
        return -10
    if ai_count == 1 and empty_count == 3:
        return 1
    if opp_count == 1 and empty_count == 3:
        return -1
    return 0


def minimax(board: list[list[str]], depth: int, alpha: float, beta: float,
            maximizing: bool, ai_player: str) -> tuple[int, int | None]:
    winner = _check_winner_on_board(board)
    if winner == ai_player:
        return 100000 + depth, None
    if winner is not None:
        return -100000 - depth, None
    if depth == 0 or all(board[0][c] != ' ' for c in range(COLS)):
        return evaluate_board(board, ai_player), None

    valid_moves = get_valid_moves(board)

    if maximizing:
        best_score = float('-inf')
        best_col = valid_moves[0]
        for col in valid_moves:
            new_board = clone_board(board)
            make_move_on_board(new_board, col, ai_player)
            score, _ = minimax(new_board, depth - 1, alpha, beta, False, ai_player)
            if score > best_score:
                best_score = score
                best_col = col
            alpha = max(alpha, score)
            if beta <= alpha:
                break
        return best_score, best_col
    else:
        opponent = 'Y' if ai_player == 'R' else 'R'
        best_score = float('inf')
        best_col = valid_moves[0]
        for col in valid_moves:
            new_board = clone_board(board)
            make_move_on_board(new_board, col, opponent)
            score, _ = minimax(new_board, depth - 1, alpha, beta, True, ai_player)
            if score < best_score:
                best_score = score
                best_col = col
            beta = min(beta, score)
            if beta <= alpha:
                break
        return best_score, best_col


DEPTH_MAP = {
    "easy": 1,
    "medium": 2,
    "hard": 4,
}


def get_ai_move(board: list[list[str]], difficulty: str) -> int:
    depth = DEPTH_MAP.get(difficulty, 4)
    _, col = minimax(board, depth, float('-inf'), float('inf'), True, 'Y')
    return col if col is not None else get_valid_moves(board)[0]
