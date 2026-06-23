from enum import Enum


class End(Enum):
    ok = "1"
    no = "2"
    finished = "3"



class Board:
    def __init__(self, size : int, player_list):
        self._board_size = size
        self._boar_max_index = size * size - 1 # -1 так как храним последний индекс в массиве
        self._board = [0 for _ in range(size * size)] # сам список с данными
        self._player_symbol = {}  # каждый пользователь имеет свой символ
        self._init_players(player_list)

    def _init_players(self, player_list : list[object]):
        '''Каждый пользователь - свой символ в базе данных'''
        symbol = 1
        for player in player_list:
            self._player_symbol[player] = symbol
            symbol += 1

    def go(self, x : int, y : int, player : object) -> End:
        #Главная функция чтобы ходить - куда и кто
        cord : int = self.num_to_cord(x, y)

        return End.ok


    def check_finish(self,) -> object | None:
        #возвращает либо игрока победившего, либо ничего - None
        ...
        return None


    def num_to_cord(self, x : int, y : int) -> int:
        '''non-safe'''
        res = x + y * self._board_size
        return res
    
    def cord_to_num(self, cord : int) -> tuple:
        '''non-safe'''
        x : int = cord % self._board_size  #деление без остатка
        y : int = cord // self._board_size #остаток от деления
        return (x, y)
    