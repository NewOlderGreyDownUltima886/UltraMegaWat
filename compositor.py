


from main import Board


class Compositor:
    def __init__(self, x_size : int, y_size : int):
        self._x_size = x_size
        self._y_size = y_size
        self._board_num = x_size * y_size
        self._last_board_index = self._board_num - 1

        self._player_list = []
        self._player_symbol = {}
        
        self._board_list = []
        self._init_boards()

    def _init_boards(self):
        for i in range(self._board_num):
            new_board = Board(3, [])
            self._board_list.append(new_board)


    def go(self, x, y, player):
        
        ...



    def global_to_local(self, x_i, y_i) -> tuple | bool:
        '''return (board_index, (x_x, y_y))'''
        x_b = x_i // 3
        y_b = y_i // 3
        board_index = x_b + (y_b * self._x_size)
        if board_index > self._last_board_index:
            raise
        
        x_x = x_i % 3
        y_y = y_i % 3
        if (x_x > 2) or (y_y > 2):
            raise

        return (board_index, (x_x, y_y))




comp = Compositor(3, 2)
print(comp.global_to_local(4, 3))
print(comp.global_to_local(4, 2))
print(comp.global_to_local(3, 1))
print(comp.global_to_local(3, 3))
