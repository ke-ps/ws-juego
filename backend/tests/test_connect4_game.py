import unittest
from backend.connect4_game import Connect4Game

class TestConnect4Game(unittest.TestCase):
    def setUp(self):
        self.game = Connect4Game()

    def test_initial_board(self):
        for row in self.game.board:
            self.assertEqual(row, [' '] * 7)

    def test_insert_piece(self):
        self.game.insert_piece(0)
        self.assertEqual(self.game.board[5][0], 'R')
        self.assertEqual(self.game.current_player, 'Y')

    def test_invalid_column(self):
        with self.assertRaises(ValueError):
            self.game.insert_piece(-1)
        with self.assertRaises(ValueError):
            self.game.insert_piece(7)

    def test_column_full(self):
        for _ in range(6):
            self.game.insert_piece(0)
        with self.assertRaises(ValueError):
            self.game.insert_piece(0)

    def test_check_winner_horizontal(self):
        for col in range(4):
            self.game.insert_piece(col)
            self.game.current_player = 'R'  # Force the same player to insert all pieces
        self.assertTrue(self.game.check_winner())

    def test_check_winner_vertical(self):
        for _ in range(4):
            self.game.insert_piece(0)
            self.game.current_player = 'R'  # Force same player for simplicity
        self.assertTrue(self.game.check_winner())

    def test_check_winner_diagonal(self):
        for col in range(4):
            self.game.insert_piece(col)
            self.game.insert_piece(col + 1)
        self.assertTrue(self.game.check_winner())

    def test_check_tie(self):
        for col in range(7):
            for _ in range(6):
                self.game.insert_piece(col)
        self.assertTrue(self.game.check_tie())

if __name__ == '__main__':
    unittest.main()

