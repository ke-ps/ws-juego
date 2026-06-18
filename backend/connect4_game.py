class Connect4Game:
    def __init__(self):
        self.rows = 6
        self.cols = 7
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
