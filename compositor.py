from typing import Dict, Tuple


from board import Board, End



class Compositor:
    def __init__(self, x_size : int, y_size : int):
        self._x_size = x_size
        self._y_size = y_size
        self._board_num = x_size * y_size
        self._last_board_index = self._board_num - 1

        self._player_symbol : Dict[str, int] = {}
        
        self._board_list : list[Board] = []

    def init(self):
        '''Init boards after appendig players'''
        for i in range(self._board_num):
            new_board = Board([3, 3], self._player_symbol)
            self._board_list.append(new_board)


    def go(self, x, y, player) -> End:
        # 1. Готовим данные
        if player not in self._player_symbol:
            raise Exception("Нет такого игрока!")
        res = self.global_to_local(x, y)
        if not res:
            return End.no
        board_index, (x_x, y_y) = res
        board : Board = self._board_list[board_index]

        # 2. Обращаемся к коду кости
        end : End = board.go(x_x, y_y, player)

        # 3. Возвращаем
        return end



    def global_to_local(self, x_i, y_i) -> Tuple[int, Tuple[int, int]] | None:
        '''return (board_index, (x_x, y_y))'''
        x_b = x_i // self._x_size
        y_b = y_i // self._y_size
        board_index = x_b + (y_b * self._x_size)
        if board_index > self._last_board_index:
            return None
        
        x_x = x_i % 3
        y_y = y_i % 3
        if (x_x > 2) or (y_y > 2):
            return None

        return (board_index, (x_x, y_y))
    

    def add_player(self, new_player : str, symbol = None):
        if symbol is None:
            symbol = len(self._player_symbol)
        self._player_symbol[new_player] = symbol


    def get_board_list(self,) -> list[Board]:
        return self._board_list



