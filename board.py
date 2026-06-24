from enum import Enum

class End(Enum):
    ok = "1"
    no = "2"
    finished = "3"

class Board:
    def __init__(self, size, player_symbol_dict):
        '''создание поля'''
        x_size = size[0]
        y_size = size[1]
        self.board = [['' for j in range(x_size)] for i in range(y_size)]

        '''инициализация игроков и символов'''
        self.player_data = []
        for i, n in enumerate(player_symbol_dict):
            self.player_data.append([])
            # порядковый номер
            self.player_data[i].append(i+1)
            # имя (передано извне)
            self.player_data[i].append(n)
            # символ (передано с именем извне)
            self.player_data[i].append(player_symbol_dict.get(n))

        self.player_symbols_list = []
        for p, e in enumerate(self.player_data):
            self.player_symbols_list.append(e[2])
        
            #print(self.board)
            #print(self.player_data)
    def go(self, x_cord_new, y_cord_new , going_player):
        self.x_cord_new = x_cord_new
        self.y_cord_new = y_cord_new
        self.going_player = going_player


        'проверка на вшивость'
        if self.board[y_cord_new][x_cord_new] in self.player_symbols_list:
            # print('это место занято!')
            return End.no
        'ход игрока'

        # узнаем символ игрока по имени:
        self.new_symbol = ''
        for i, e in enumerate(self.player_data):
            if going_player in e:
                self.new_symbol = str(e[2])
        # ходим
        self.board[y_cord_new][x_cord_new] = self.new_symbol

        # вывод поля
        # for i, e in enumerate(self.board):
            # print(str(e))

        return self.check_finished()

    def check_finished(self):
        # проверка по горизонтали
        y_core = self.board[self.y_cord_new]
        if len(set(y_core)) == 1 and y_core[0] != '': 
            # print(self.going_player + ' Победил!!! горизонталь')
            return End.finished

        # проверка по вертикали
        x_core = []
        for i, n in enumerate(self.board):
            x_core.append(n[self.x_cord_new])
        if len(set(x_core)) == 1 and x_core[0] != '': 
            # print(self.going_player + ' Победил!!! вертикаль')
            return End.finished

        # проверка по диагонали вверх
        dia_up_core = []
        for i, e in enumerate(self.board):
            if i == self.y_cord_new:
                for r, t in enumerate(self.board):
                    dia_up_core.append(e[(-r)-1])
        if len(set(dia_up_core)) == 1 and dia_up_core[0] != '': 
            # print(self.going_player + ' Победил!!! диагональ вверх')
            return End.finished
        
        # проверка по диагонали вниз
        dia_down_core = []
        for i, e in enumerate(self.board):
            if i == self.y_cord_new:
                for r, t in enumerate(self.board):
                    dia_down_core.append(t[r])
        if len(set(dia_down_core)) == 1 and dia_down_core[0] != '': 
            # print(self.going_player + ' Победил!!! диагональ вниз')
            return End.finished
        
        return End.ok


# game = Board([3, 3], player_symbol_dict={})
# game.go(x_cord_new=int(), y_cord_new=int(), going_player={}) # (x_cord_new, y_cord_new, 'Гриша')
# game.check_finished()


# player_symbol_dict={'Коля': '+', 'Андрей': '#'}
# game = Board([3, 3], player_symbol_dict)

# def one_cycle(player):
#     try:
#         print(f'\nХодит: {player}')
#         x_cord_new = int(input('введите ход по х: '))
#         y_cord_new = int(input('введите ход по y: '))

#         res = game.go(x_cord_new, y_cord_new, player)
#         if res == End.no:
#             print('Попробуй еще раз')
#             return one_cycle(player)
#         elif res == End.finished:
#             print(f"{player} победил!")
#             quit()

#     except Exception:
#             print('Произошла какая-то ошибка, попробуйте еще раз...')
#             return one_cycle(player)

# while True:
#     for player in player_symbol_dict:
#         one_cycle(player)
