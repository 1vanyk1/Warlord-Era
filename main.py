import pygame
import os
import random
import math
import sqlite3


pygame.init()  # Создаём игровое окно
width, height = 1200, 800
screen = pygame.display.set_mode((width, height))
running = True

selected_province = []  # Внутриигровая информация
countries = {}
countries_ids = []
language = 'ru'  # Язык
languages = {'en': 'english', 'ru': 'russian'}  # Планировались локализации но я не успел :)
player_country = 'yue'  # Страна игрока
divisions = []  # Дивизии  | Меню (открыты ли) \/
menu_opened = {'division': False, 'province': False, 'diplo': False, 'country_choose': False}
div_id = 0  # Последнее id дивизии


def load_image(name, colorkey=None):  # загрузка изображений
    fullname = os.path.join('data/backgrounds', name)
    image = pygame.image.load(fullname)
    if colorkey == -1:
        colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey)
    image = image.convert_alpha()
    return image


def if_there_army_in_province(pos, country=None):  # Узнаём, есть ли в провинции армия
    if country is None:                            # (определённой страны)
        for i in divisions:
            if i.return_pos() == pos:
                return True
    else:
        for i in divisions:
            if i.return_pos() == pos and i.country == country:
                return True
    return False


def get_army_of_province(pos, country=None):  # Узнаём каков состав армии провинции
    a = []
    if country is None:
        for i in divisions:
            if i.return_pos() == pos:
                a.append(i)
    else:
        for i in divisions:
            if i.return_pos() == pos and i.country == country:
                a.append(i)
    return a


def get_army_that_attacking_province(pos, country):  # Узнаём, кто аттакует провинцию
    a = []
    for i in divisions:
        if i.where_is_going != [] and i.where_is_going[0] == pos and \
                i.country in countries[country].wars:
            a.append(i)
    return a


def can_go(prov, country, hp=1, i=None):  # Узнаём, может ли пойти туда дивизия (или нет)
    if i is None:
        if prov == country or prov in countries[country].wars:
            return True
    else:
        if prov == country or (prov in countries[country].wars and
                               (player_country == country or hp > 0.5 or
                                get_army_of_province(i) == [])):
            return True
    return False


def find_path(mass, start_point, end_point, country, hp=1):  # Строим маршрут для дивизии
    if end_point is None:
        return []
    w = gamemap.len_m  # Узнаём кол-во провинций (чтобы не нагружать процессор)
    a = [0 for _ in range(w)]  # Список, показывающий, была ли проверена провинция
    ways = [[] for _ in range(w)]  # Список, показывающий маршрут до этой провинции
    a[start_point] = 2
    while a[end_point] == 0:  # пока не найдём маршрут проверяем всю карту
        t = False  # Есть ли непроверенные провинции
        for i in range(w):
            if a[i] == 2:
                if i == end_point:  # маршрут найден
                    return ways[end_point]
                t = True  # Есть непроверенные провинции
                for j in gamemap.can_go[i]:
                    if a[j] == 0 and can_go(mass[j], country, hp, j):
                        a[j] = 3  # Следующие проверяемые провинции (нужно менять,чтобы убрать баги)
                        ways[j] += ways[i] + [j]  # Маршрут на этой провинции
                a[i] = 1
                ways[i] = []  # Чистим память
        for i in range(w):
            if a[i] == 3:
                a[i] = 2
        if not t:  # маршрут не найден
            return []
    return ways[end_point]  # маршрут найден


def get_country(country_id):  # возвращаем спрану, если её нет, то создаём
    if country_id not in countries_ids:
        countries[country_id] = Country(country_id)
        countries_ids.append(country_id)
    return countries[country_id]


def declare_war(country1, country2):  # объявление войны country1 стране country2
    country1 = get_country(country1).get_id()
    country2 = get_country(country2).get_id()
    if country2 not in countries[country1].wars:
        countries[country1].wars.append(country2)
    if country1 not in countries[country2].wars:
        countries[country2].wars.append(country1)


def peace(country1, country2):  # объявление о мире между country1 и country2
    if country2 in countries[country1].wars:
        countries[country1].wars.remove(country2)
    if country1 in countries[country2].wars:
        countries[country2].wars.remove(country1)


class Country:  # класс страны
    def __init__(self, country_id):
        self.id = country_id
        data = self.generate_info(country_id)  # Получаем информацию
        self.data = {}
        for i in data:
            row = i.split(' = ')
            if row[1].isdigit():
                row[1] = int(row[1])
            self.data[row[0]] = row[1]
        self.wars = []

    def generate_info(self, country_id):  # получаем информацию о стране из файла
        country_id += '.txt'
        directory = os.path.join('data', 'countries')
        files = os.listdir(directory)  # Путь к файлу...
        if country_id in files:  # Получаем информацию из файла (если он есть)
            file = open(os.path.join(directory, country_id), 'r')
            data = file.read().split('\n')
            file.close()
            return data
        return None

    def get_color(self):  # возвращаем цвет страны
        return self.data['r'], self.data['g'], self.data['b']

    def get_name(self):  # возвращаем название страны
        return self.data['name']

    def get_id(self):  # возвращаем id страны
        return self.id


def get_count_of_divisions_of_country(country, on_border_with=None):  # получаем кол-во армии страны
    c = 0                                                             # (и тех кто стоит на границе)
    borders_that_closed = []
    if on_border_with is None:
        for i in divisions:
            if i.country == country and i.hp >= 5:
                c += 1
                borders_that_closed.append(i.return_pos_of_border())
    else:
        for i in divisions:
            if i.country == country and i.on_board == on_border_with:
                c += 1
                borders_that_closed.append(i.return_pos_of_border())
    return c, borders_that_closed


def delete_elems_from_mass(mass, elems):  # удаляем из mass элементы elems
    return [i for i in mass if i not in elems]


# ИИ \/ ----------------------------------------------------------------------------------------


def division_can_go_away(div):  # узнаём, может ли дивизия покунуть границу
    if get_army_that_attacking_province(div.return_pos(), div.country):
        return False  # Если её атакуют, то нет
    army = get_army_of_province(div.return_pos())
    if len(army) == 1:
        return False  # Если не кто больше не будет охранять границу, то нет
    c = 0
    for i in army:  # Узнаём информацию, про другие дивизии
        if i.on_board == div.on_board and not i.is_moving():
            if c == 1:  # Если хотя бы одна стоит (не считая нашу), то уйти можно
                return True
            c += 1
    return False  # Иначе нельзя


def close_borders_from_enemy(country, enemy, needed=True):  # закрываем границу от врага
    border = []                                             # (и очень важно ли нам это)
    w = gamemap.len_m
    for i in range(w):  # получаем все пограничные провинции
        if gamemap.board[i] == country:
            for j in gamemap.can_go[i]:
                if gamemap.board[j] == enemy:
                    border.append(i)
                    break
    border.sort()  # получаем армию страны, и ту, которая на границе
    count = get_count_of_divisions_of_country(country)[0]  # получаем кол-во всех дивизий
    count_on_border, borders_that_closed = get_count_of_divisions_of_country(country, enemy)
    border = delete_elems_from_mass(border, borders_that_closed)  # получаем незанятые границы
    if count != 0 and len(border) != 0:
        if count < len(border):  # армии мало
            c = 0
            border = random.sample(border, count)  # Выбираем, что закрыть
            for i in divisions:
                if c == len(border):  # Если всё закрыли, то всё
                    break
                if i.country == country and (i.on_board is None or division_can_go_away(i) and
                                             needed):  # подходит, ли дивизия
                    b = border[c]  # Ставим на границу
                    if i.return_pos() == b or i.find_path(b):
                        i.on_board = enemy  # каждой дивизии говорим, куда становиться
                    c += 1
        else:  # армии достаточно
            c = 0
            for i in divisions:
                if i.country == country and (i.on_board is None or division_can_go_away(i) and
                                             needed):  # подходит, ли дивизия
                    b = border[c]  # Ставим на границу
                    if i.return_pos() == b or i.find_path(b):
                        i.on_board = enemy  # каждой дивизии говорим, куда становиться
                    c += 1
                    if c == len(border):
                        break


def attack_enemy(country, enemy):  # атака на врага
    for k in divisions:
        if k.country == country and k.on_board == enemy and not k.is_moving() and \
                k.hp / k.max_hp > 0.2:  # может ли дивизия атаковать
            border = []
            i = k.return_pos()
            maybe_go = []
            c = 0
            for j in gamemap.can_go[i]:  # узнаём, куда она может напасть
                if gamemap.board[j] == enemy:
                    c += 1
                    border.append(j)
                    if len(get_army_of_province(j)) == 0:
                        maybe_go.append(j)
            if border:  # нападаем (если можем)
                if (len(get_army_of_province(k.return_pos())) > 1 or random.randint(0, 9) == 1) \
                        and k.hp / k.max_hp > 0.5:
                    k.find_path(random.sample(border, 1)[0])
                elif len(border) == 1:  # узнаём, могут ли нам помочь наши соседи
                    t = False
                    for j in gamemap.can_go[border[0]]:  # узнаём, куда она может напасть
                        if gamemap.board[j] == country:
                            divs = get_army_of_province(j, country)
                            for div in divs:
                                if not div.is_moving():  # Если они не двигаются, то помогают
                                    div.find_path(border[0])
                                    t = True
                    if t:
                        k.find_path(border[0])  # Если нам помогают, то и сами нападаем
            elif len(maybe_go) == 1 and c == 1 or random.randint(0, 3) == 1 and maybe_go:
                k.find_path(maybe_go[0])


def stop_moving(country, is_at_war):  # останавливаем дивизии, если надо
    for k in divisions:
        if k.country == country:
            i = k.return_pos_of_border()
            t = True
            if is_at_war and k.on_board not in countries[country].wars:
                pass  # Если она во время войны не там где надо, то мы её отводим
            elif gamemap.board[i] == k.on_board:  # Если она на позиции, то нет
                t = False
            else:
                for j in gamemap.can_go[i]:  # Если туда, куда она идёт находится граница, то нет
                    if gamemap.board[j] == k.on_board:
                        t = False
                        break
            if t:  # Если нужно отводить, то отводим
                k.on_board = None
                if k.where_is_going:
                    k.find_path(k.where_is_going[0])


# ИИ /\ ----------------------------------------------------------------------------------------


def change_color(color, n):  # Изменяем цвет (r, g, b) на n
    r, g, b = color
    r, g, b = r + n, g + n, b + n
    if r < 0:  # Проверка, чтобы не было ошибок
        r = 0
    elif r > 255:
        r = 255
    if g < 0:
        g = 0
    elif g > 255:
        g = 255
    if b < 0:
        b = 0
    elif b > 255:
        b = 255
    return r, g, b


class Provinces:
    def __init__(self):
        directory = os.path.join('data', 'provs')
        files = os.listdir(directory)  # получаем файлы о провинциях
        self.board = ['yue'] * len(files)  # простое заполнение
        country = get_country('yue')
        self.colors = [country.get_color()] * len(files)
        self.happiness = [50] * len(files)  # Счастье в провинциях
        self.left = 0  # Отклонение от верха экрана
        self.top = 0  # Отклонение от лева экрана
        self.cell_size = 0.5  # Размер провинций

        self.selected_province = -1  # Выбранная провинция
        self.borders = []  # Границы
        self.can_go = []  # Куда можно идти
        self.out_borders = []  # Границы карты
        self.centres = []  # Центры провинций
        self.borders_with_others = []  # Границы с другими провинциями
        self.provs_rect = []  # Лево, вверх, ширина и высота провинций
        self.provs_names = []  # Названия провинций

        for prov_id in sorted(files, key=lambda x: int(x.split('.')[0])):
            file = open(os.path.join(directory, prov_id), 'r')  # Открываем файлы провинций
            data = file.read().split('\n')  # Получаем информацию о каждой провинции из файла
            file.close()
            d1 = data[0].split()  # 1 строка
            self.centres.append((int(d1[0]), int(d1[1])))  # Центр
            self.borders.append(  # Границы
                [(int(d1[i * 2 + 2]), int(d1[i * 2 + 3])) for i in range(int(len(d1) / 2) - 1)])
            hor, ver = [int(i) for i in d1[2::2]], [int(i) for i in d1[3::2]]  # Получаем x, y точек
            self.provs_rect.append([min(hor), min(ver), max(hor) - min(hor), max(ver) - min(ver)])
            out_borders = []  # Границы карты (они могут состоять из нескольких частей)
            for i in data[1].split(';'):
                t = i.split()
                if len(t) < 3:  # Если это одна точка, то это не граница
                    continue
                out_borders.append([(int(t[j * 2]), int(t[j * 2 + 1])) for j in
                                    range(int(len(t) / 2))])  # иначе добавляем
            self.out_borders.append(out_borders)  # Добавляем границы карты
            con = sqlite3.connect("data/localisation/provs.db")
            cur = con.cursor()  # Получаем название провинции
            result = cur.execute(
                "SELECT " + languages[language] + " FROM provs WHERE id_name = " +
                prov_id.split('.')[0]).fetchone()[0]
            self.provs_names.append(result)  # Добавляем название
            con.close()
            if len(data) > 2:  # Границы с соседними провинциями (Если они есть)
                borders_with_others = {}
                can_g = []
                for text in data[2:]:
                    if text == '':
                        break  # Если информация закончилась то мы переходим к следующему
                    t = text.split(':')
                    if len(t[1].split('  ')) != 1:  # Если граница не состоит из одной точки, то
                        n = int(t[0])
                        can_g.append(n)  # у нас есть к ней доступ
                        out_borders = []
                        for i in t[1].split(';'):  # Смотрим каждую часть
                            t1 = i.split()
                            if len(t1) < 3:  # Если она состоит из одной точки,то переходим к другой
                                continue
                            out_borders.append(  # Иначе добавляем
                                [(int(t1[j * 2]), int(t1[j * 2 + 1])) for j in
                                 range(int(len(t1) / 2))])
                        borders_with_others[n] = out_borders
                self.borders_with_others.append(borders_with_others)
                self.can_go.append(can_g)
            else:  # Если нет (???) то мы добавляем пустые строки
                self.borders_with_others.append({})
                self.can_go.append([])
        self.len_m = len(self.borders)  # Кол-во провинций

    def return_map_borders(self):  # Получаем границы карты
        return min([min([j[0] for j in i]) for i in self.borders]), \
               min([min([j[1] for j in i]) for i in self.borders]), \
               max([max([j[0] for j in i]) for i in self.borders]), \
               max([max([j[1] for j in i]) for i in self.borders])

    def can_see_army(self, i):  # Можем ли мы видеть армию в провиции
        if self.board[i] == player_country or player_country in \
                [self.board[j] for j in self.can_go[i]]:
            return True
        return False

    def set_view(self, left, top, cell_size):  # Задать положение карты относительно камеры
        self.left = left
        self.top = top
        self.cell_size = cell_size / 100

    def can_see_prov(self, i):  # Можем ли мы видеть провинцию
        return self.provs_rect[i][0] * self.cell_size <= width - self.left and \
               (self.provs_rect[i][0] + self.provs_rect[i][2]) * self.cell_size >= -self.left and \
               self.provs_rect[i][1] * self.cell_size <= height - self.top and \
               (self.provs_rect[i][1] + self.provs_rect[i][3]) * self.cell_size >= -self.top

    def render(self):  # Рисуем карту...
        for i in range(self.len_m):
            if self.can_see_prov(i):  # Если мы видим провинцию
                if menu_opened['diplo']:  # Если открыто меню дипломатии
                    if self.selected_province == -1:  # Если мы не выбрали провинцию,
                        cou = player_country  # то показываем политику относительно игрока
                    else:  # Иначе относительно владельца провинции
                        cou = self.board[self.selected_province]
                    if self.board[i] == cou:  # Если это провинция пладельца
                        color = (0, 100, 200)
                    elif self.board[i] in countries[cou].wars:  # врага
                        color = (200, 0, 0)
                    else:  # другого
                        color = (100, 100, 100)
                    pygame.draw.polygon(screen, color, [(  # рисуем провинцию
                        self.left + p[0] * self.cell_size,
                        self.top + p[1] * self.cell_size) for p in self.borders[i]], 0)
                else:  # Иначе | Если у нас меню выбора страны \/
                    if menu_opened['country_choose'] and self.selected_province != -1 and \
                            self.board[self.selected_province] == self.board[i]:
                        pygame.draw.polygon(screen, change_color(self.colors[i],
                                                                 self_change_light[0]),
                                            [(self.left + p[0] * self.cell_size,
                                              self.top + p[1] * self.cell_size)
                                             for p in self.borders[i]], 0)
                    else:  # Иначе
                        pygame.draw.polygon(screen, self.colors[i],
                                            [(self.left + p[0] * self.cell_size,
                                              self.top + p[1] * self.cell_size) for p in
                                             self.borders[i]], 0)
        for i in range(self.len_m):  # Рисуем границы карты
            for k in self.out_borders[i]:
                pygame.draw.lines(screen, pygame.Color("white"), False,
                                  [(int(self.left + p[0] * self.cell_size),
                                    int(self.top + p[1] * self.cell_size)) for p in k], 2)
            for j in self.can_go[i]:  # Рисуем границы с другими провинциями
                if self.board[j] != self.board[i]:  # Если они не наши
                    for k in self.borders_with_others[i][j]:
                        pygame.draw.lines(screen, pygame.Color("white"), False,
                                          [(int(self.left + p[0] * self.cell_size),
                                            int(self.top + p[1] * self.cell_size)) for p in k], 2)
                elif ZOOM > 75:  # Или если мы очень сильно приблизили
                    for k in self.borders_with_others[i][j]:
                        pygame.draw.lines(screen, pygame.Color("gray"), False,
                                          [(int(self.left + p[0] * self.cell_size),
                                            int(self.top + p[1] * self.cell_size)) for p in k], 1)
        if self.selected_province != -1 and not menu_opened['country_choose']:  # Рисуем выбранную
            for k in self.out_borders[self.selected_province]:                  # провинцию
                pygame.draw.lines(screen, pygame.Color("yellow"), False,
                                  [(int(self.left + p[0] * self.cell_size),
                                    int(self.top + p[1] * self.cell_size)) for p in k], 2)
            for j in self.can_go[self.selected_province]:
                for k in self.borders_with_others[self.selected_province][j]:
                    pygame.draw.lines(screen, pygame.Color("yellow"), False,
                                      [(int(self.left + p[0] * self.cell_size),
                                        int(self.top + p[1] * self.cell_size)) for p in k], 2)
        if not menu_opened['country_choose']:  # Если мы не выбираем страну
            for div in divisions:  # Рисуем дивизии (три цикла, так как нет нормальных слоёв :( )
                k = div.return_pos()
                if ZOOM > 75 and self.can_see_army(k):  # Если мы её видим
                    selected = div.return_info()[3]
                    if selected:  # И если мы её выбрали
                        steps = [k] + div.where_is_going
                        for step in range(len(steps) - 1):  # Рисуем, куда она идёт
                            pos1 = steps[step]
                            pos2 = steps[step + 1]
                            pygame.draw.line(screen, pygame.Color("red"),
                                             (self.left + self.centres[pos1][0] * self.cell_size,
                                              self.top + self.centres[pos1][1] * self.cell_size),
                                             (self.left + self.centres[pos2][0] * self.cell_size,
                                              self.top + self.centres[pos2][1] * self.cell_size), 5)
                        if len(steps) > 1:  # Если она идёт
                            pos1 = steps[0]
                            pos2 = steps[1]
                            hlntg = 1 - div.how_long_need_to_go / 5  # рисуем, сколько она прошла
                            cell_x = self.left + self.centres[pos1][0] * self.cell_size
                            cell_y = self.top + self.centres[pos1][1] * self.cell_size
                            pygame.draw.line(screen, (255, 127, 127), (cell_x, cell_y),
                                             (cell_x + (self.left + self.centres[pos2][0] *
                                                        self.cell_size - cell_x) * hlntg,
                                              cell_y + (self.top + self.centres[pos2][1] *
                                                        self.cell_size - cell_y) * hlntg), 5)
                            x1, y1 = self.centres[steps[-2]]  # Рисуем конец стрелочки
                            x2, y2 = self.centres[steps[-1]]
                            d_x, d_y = x1 - x2, y1 - y2
                            diag = (d_x ** 2 + d_y ** 2) ** 0.5
                            sin = d_y / diag * math.cos(math.pi / 6) + d_x / diag * math.sin(math.pi
                                                                                             / 6)
                            cos = d_x / diag * math.cos(math.pi / 6) - d_y / diag * math.sin(math.pi
                                                                                             / 6)
                            cell_x = self.left + x2 * self.cell_size  # Поворачиваем /\
                            cell_y = self.top + y2 * self.cell_size  # Рисуем и ещё раз поворачиваем
                            pygame.draw.line(screen, pygame.Color("red"), (cell_x, cell_y),
                                             (cell_x + int(20 * cos), cell_y + int(20 * sin)), 5)
                            sin = d_y / diag * math.cos(math.pi / 6) - d_x / diag * math.sin(math.pi
                                                                                             / 6)
                            cos = d_x / diag * math.cos(math.pi / 6) + d_y / diag * math.sin(math.pi
                                                                                             / 6)
                            pygame.draw.line(screen, pygame.Color("red"), (cell_x, cell_y),
                                             (cell_x + int(20 * cos), cell_y + int(20 * sin)), 5)
            for div in divisions:
                k = div.return_pos()
                if ZOOM > 75 and self.can_see_army(k):  # Если мы видим дивизию
                    selected = div.return_info()[3]
                    i, j = self.centres[k]
                    pygame.draw.rect(screen, pygame.Color("grey"),  # Фон прямоугольника
                                     [(self.left + (i + 0.5) * self.cell_size - 29, self.top - 14 +
                                       (j + 0.5) * self.cell_size), (58, 28)], 0)
                    if selected:  # И если её выбрали, то ещё жёлтая окантовка
                        pygame.draw.rect(screen, pygame.Color("yellow"),
                                         [(self.left + (i + 0.5) * self.cell_size - 30,
                                           self.top - 15 + (j + 0.5) * self.cell_size),
                                          (60, 30)], 4)
            for div in divisions:
                k = div.return_pos()
                if ZOOM > 75 and self.can_see_army(k):  # Если мы видим...
                    max_hp, hp = div.return_info()[:2]
                    selected = div.return_info()[3]
                    i, j = self.centres[k]
                    if not selected:  # Если дивизия не выбрана
                        if div.country in countries[player_country].wars:  # Она вражеская ли
                            pygame.draw.rect(screen, pygame.Color("red"),
                                             [(self.left + (i + 0.5) * self.cell_size - 29,
                                               self.top - 14 + (j + 0.5) * self.cell_size),
                                              (58, 28)], 2)
                        else:  # Или нет
                            pygame.draw.rect(screen, pygame.Color("black"),
                                             [(self.left + (i + 0.5) * self.cell_size - 29,
                                               self.top - 14 +
                                               (j + 0.5) * self.cell_size), (58, 28)], 2)
                    pygame.draw.rect(screen, pygame.Color("green"),  # Здоровье
                                     [(self.left + (i + 0.5) * self.cell_size - 25, self.top + 1 +
                                       (j + 0.5) * self.cell_size), (int(hp * 50 / max_hp), 10)], 0)
                    pygame.draw.rect(screen, pygame.Color("black"),  # Граница здоровья
                                     [(self.left + (i + 0.5) * self.cell_size - 26, self.top +
                                       (j + 0.5) * self.cell_size), (52, 12)], 1)

    def update_province(self, i, prov_id):  # Изменения с провинцией
        country_before = self.board[i]  # Бывший владелец
        self.board[i] = prov_id  # Новый владелец
        self.colors[i] = get_country(prov_id).get_color()  # Новый цвет
        for i in self.board:  # У бывшего владельца ещё остались провинции
            if country_before == i:
                return None
        countries_ids.remove(country_before)  # Если нет, то его удаляем
        for i in countries_ids:  # И все с ним заключают мир
            peace(country_before, i)

    def move_units(self, mouse_pos):  # Перемещаем войска
        cell, b = self.get_cell(mouse_pos, True)
        self.find_path(player_country, cell, True)

    def get_click(self, mouse_pos):  # Реакция на щелчок
        cell, b = self.get_cell(mouse_pos)
        self.on_click(cell, b)

    def get_cell(self, mouse_pos, is_moving=False):  # Что нажато?
        self.selected_province = -1  # Если ничего
        for i in range(self.len_m):
            if self.can_see_prov(i):  # Если провинция видна
                prov_original = pygame.Surface((self.provs_rect[i][2] * self.cell_size,
                                                self.provs_rect[i][3] * self.cell_size),
                                               pygame.SRCALPHA)  # Рисуем временную поверхность
                pygame.draw.polygon(prov_original, (0, 0, 0), [  # На ней же провинцию
                    ((j[0] - self.provs_rect[i][0]) * self.cell_size,
                     (j[1] - self.provs_rect[i][1]) * self.cell_size) for j in self.borders[i]])
                mouse_original = pygame.Surface((1, 1), pygame.SRCALPHA)  # Временная поверхн. мыши
                pygame.draw.polygon(mouse_original, (255, 0, 0), [(0, 0), (0, 1), (1, 1), (1, 0)])
                provrect = prov_original.get_rect(center=(self.left + (self.provs_rect[i][0] +
                                                              self.provs_rect[i][2] / 2) *
                                                 self.cell_size, self.top + (  # Границы провинции
                        self.provs_rect[i][1] + self.provs_rect[i][3] / 2) * self.cell_size))
                mask_prov = pygame.mask.from_surface(prov_original)  # Маска провинции
                mask_mouse = pygame.mask.from_surface(mouse_original)  # Маска мыши
                offset = provrect[0] - mouse_pos[0], provrect[1] - mouse_pos[1]  # Точка касания
                if mask_mouse.overlap(mask_prov, offset):  # Касаемся ли
                    if not is_moving:  # Если это не перемещение дивизий
                        if ZOOM > 75 and if_there_army_in_province(i) and \
                                abs(mouse_pos[0] - self.left - self.centres[i][0] *
                                    self.cell_size) <= 30 and \
                                abs(mouse_pos[1] - self.top - self.centres[i][1] *
                                    self.cell_size) <= 15:  # Если мы касаемся дивизии
                            return i, True
                        self.selected_province = i  # Иначе это выделенная вровинция
                    return i, False
        return None, False  # Если мы так ничего и не нашли

    def deselect_whole_army(self):  # Отменить выделение всей армии
        for k in divisions:
            if k.country == player_country:
                k.select(False)

    def find_path(self, country, cell, need_to_be_selected=False):  # Найти путь для дивизий
        for k in divisions:
            if k.country == country and (not need_to_be_selected or k.selected):
                k.find_path(cell)

    def on_click(self, cell_coords, b):  # Что делать на щелчок
        selected_province.clear()  # Отменяем выделение
        menu_opened['province'] = False  # И закрываем меню
        menu_opened['division'] = False
        self.deselect_whole_army()
        if cell_coords is not None:  # Если выбрана провинция
            selected_province.append(cell_coords)
            if b:  # Если попали по дивизии
                if if_there_army_in_province(cell_coords):  # Если есть армия в этой провинции,
                    t = False
                    for k in get_army_of_province(cell_coords):
                        if k.country == player_country:  # то вся армия, принадлежащая игроку -
                            k.select(True)  # выделяется
                            t = True
                    menu_opened['division'] = t  # Открываем меню армии (если выбраны дивизии)
            else:  # Иначе открываем меню провинции
                menu_opened['province'] = True

    def actions_with_provinces(self):  # Действия с поровинциями
        for i in range(self.len_m):
            if random.randint(1, 3) == 1:  # Изменяем счастье
                self.happiness[i] -= random.randint(-1, 1)
            if self.happiness[i] < 10 and random.randint(1, 5) == 1:  # Если счастье, маленькое,
                self.happiness[i] = 60  # то происходит восстание
                count_under_reb = self.board[i]
                declare_war(self.board[i], 'communists')
                self.update_province(i, 'communists')
                divisions.append(Division(50, 20, 40, i, 'communists'))
                divisions.append(Division(50, 20, 40, i, 'communists'))
                for ii in range(self.len_m):  # И по всей территории страны, в которой произошло
                    if self.board[ii] == count_under_reb:  # восстание, уменьшается счастье
                        self.happiness[ii] -= random.randint(0, 5)
            if self.happiness[i] < 0:  # Проверка, находится ли счастье в диапозоне
                self.happiness[i] = 0
            elif self.happiness[i] > 100:
                self.happiness[i] = 100
            # Сражение
            strength_1 = 0  # Сила защищающихся | Защищающие \/
            army_under_attack = [i for i in get_army_of_province(i) if not i.is_surviving]
            army_attacking = get_army_that_attacking_province(i, self.board[i])  # Атакующие
            if army_attacking == [] or army_under_attack == []:
                continue  # Если кого, либо из них нет, то сражения нет
            for k in army_under_attack:  # Узнаём силу защиты
                strength_1 += k.strength
            strength_2 = 0  # Сила атакующих
            for k in army_attacking:
                k.get_damage(random.randint(0, int(strength_1 / 10)))  # Наносим урон атакующим
                if k.hp < 5:  # Если у них мало здоровья, то они перестают атаковать
                    x = k.return_pos()
                    k.find_path(x)
                    k.on_board = None
                else:  # Иначе узнаём их силу
                    strength_2 += k.strength
            for k in army_under_attack:  # Наносим урон защищающимся
                k.get_damage(random.randint(0, int(strength_2 / 15)))
                if k.hp < 5:  # Если у них мало здоровья, то они отступают
                    k.try_to_survive()


class Division:  # Дивизии
    def __init__(self, max_hp, hp, strength, pos, country):
        global div_id
        self.hp = hp  # Здоровье дивизии
        self.max_hp = max_hp  # Максимальное здоровье дивизии
        self.strength = strength  # Сила дивизии
        self.selected = False  # Выбрана ли
        self.country = country  # Владелец
        self.where_is_going = []  # Маршрут
        self.how_long_need_to_go = 0  # Как долго ей осталось идти
        self.pos = pos  # Позиция
        self.on_board = None  # На границе с кем
        self.id = div_id  # id дивизии
        self.is_surviving = False  # Спасается ли
        div_id += 1

    def return_info(self):  # Информация о дивизии
        return self.max_hp, self.hp, self.strength, self.selected

    def select(self, b: bool):  # Выбрать дивизию
        self.selected = b

    def find_path(self, end_pos):  # Построить маршрут
        next_prov = None
        if self.is_surviving:
            return None  # Если она спасается, то её переместить нельзя
        if self.where_is_going:  # Если она куда-то уже идёт,
            next_prov = self.where_is_going[0]  # то узнаём, какая следующая провинция
        self.where_is_going = find_path(gamemap.board, self.pos, end_pos, self.country,
                                        self.hp / self.max_hp)  # Строим новый маршрут
        if self.where_is_going:  # Если есть маршрут
            if next_prov is None or not next_prov == self.where_is_going[0]:  # Если следующая
                self.how_long_need_to_go = 5  # провинция не совпадает не совпадает, то <
            return True  # Новый маршрут найден
        return False  # Новый маршрут не найден

    def go(self):  # Делаем "шаг"
        if self.where_is_going:  # Если идём
            for i in self.where_is_going:  # Проверяем, можем ли мы идти по маршруту
                if not can_go(gamemap.board[i], self.country):  # Если где-то нет,
                    self.is_surviving = False
                    self.find_path(self.where_is_going[-1])  # То пытаемся построить новый маршрут
                    if not self.where_is_going:
                        self.how_long_need_to_go = 0
                        return None  # Если не получилось, то заканчиваем
            if self.is_surviving:  # Если спасаемся, то идём медленнее
                self.how_long_need_to_go -= 0.5
            else:  # Иначе нормально
                self.how_long_need_to_go -= 1
            if self.how_long_need_to_go <= 0:  # Если мы закончили путь
                p = self.where_is_going[0]
                if gamemap.board[p] in countries[self.country].wars and \
                        get_army_of_province(p) != []:
                    self.how_long_need_to_go += 1  # Если нам что-то мегает, то мы не закончили путь
                    return None
                self.pos = self.where_is_going.pop(0)  # Перемещаемся
                self.is_surviving = False  # Не спасаемся
                if gamemap.board[self.pos] in countries[self.country].wars:  # Если это вражеское
                    gamemap.update_province(self.pos, self.country)  # То захватываем
                self.how_long_need_to_go = 5
                if not self.where_is_going:  # Если мы не куда не идём, то нам "осталось 0 дней,
                    self.how_long_need_to_go = 0  # чтобы попасть в следующую провинцию"
        else:  # Иначе, мы не спасаемся
            self.is_surviving = False
            if self.on_board is not None:
                t = True
                for i in gamemap.can_go[self.pos]:
                    if i == self.on_board:
                        t = False
                        break
                if t:  # Если мы не стоим на границе, то открепляемся от неё
                    self.on_board = None

    def return_pos(self):  # Возвращаем позицию
        return self.pos

    def return_pos_of_border(self):  # Возвращаем позицию пограничной провинции
        if not self.where_is_going:
            return self.pos
        return self.where_is_going[-1]

    def regeneration(self):  # Восстанавливаем здаровье
        if self.hp < self.max_hp:
            self.hp += random.randint(0, 1)

    def is_moving(self):  # Перемещаемся ли
        if not self.where_is_going:
            return False
        return True

    def get_damage(self, damage):  # Получаем урон
        self.hp -= damage
        if self.hp <= 0:
            if self.is_surviving:  # Если мы спасоем и здоровье на 0, то дивизия погибает
                remove_division(self)
            else:
                self.hp = 0

    def try_to_survive(self):  # СПАСАЕМСЯ!!!
        if self.is_surviving:  # Если уже спасаемся
            if not self.where_is_going:  # И мы не идём,
                remove_division(self)  # то погибаем :(
            return None
        i = self.pos
        can_go1 = []
        can_go2 = []
        for j in gamemap.can_go[self.pos]:  # Узнаём, куда можно спастись
            if get_army_that_attacking_province(j, self.country) == [] and \
                    can_go(gamemap.board[i], self.country, 0.1, j):
                if gamemap.board[j] == self.country:
                    can_go1.append(j)  # Наша провинция
                elif not get_army_of_province(j):
                    can_go2.append(j)  # Не наша провинция
        if can_go1:  # Спасаемся
            self.find_path(random.sample(can_go1, 1)[0])
            self.is_surviving = True
            if not self.where_is_going:
                remove_division(self)
        elif can_go2:
            self.find_path(random.sample(can_go2, 1)[0])
            self.is_surviving = True
            if not self.where_is_going:
                remove_division(self)
        else:  # Если не куда спасаться, то дивизия погибает
            remove_division(self)


def remove_division(div):  # Уничтожение дивизии
    try:
        divisions.remove(div)
    except:
        pass
    finally:
        pass


def create_event():  # События (ПОКА ЗАСКРИПТОВАНЫ)
    if date == [7, 4, 1927]:
        declare_war(gamemap.board[17], 'jiang_yingshu')
        declare_war(gamemap.board[14], 'jiang_yingshu')
        gamemap.update_province(17, 'jiang_yingshu')
        divisions.append(Division(50, 25, 50, 17, 'jiang_yingshu'))
        divisions.append(Division(50, 25, 50, 17, 'jiang_yingshu'))
    elif date == [20, 1, 1928]:
        declare_war(gamemap.board[23], 'jiang_jieba')
        declare_war(gamemap.board[14], 'jiang_jieba')
        gamemap.update_province(23, 'jiang_jieba')
        divisions.append(Division(50, 30, 50, 23, 'jiang_jieba'))
    elif date == [14, 12, 1928]:
        gamemap.update_province(5, 'li_shen')
        gamemap.update_province(6, 'li_shen')
        gamemap.update_province(7, 'li_shen')
        divisions.append(Division(50, 30, 50, 5, 'li_shen'))
        divisions.append(Division(50, 30, 50, 7, 'li_shen'))


def draw_scenario_name():  # "Рисуем" название сценария
    font = pygame.font.Font(None, 30)
    text = font.render(scenario_name, 1, (255, 255, 255))
    text_h = text.get_height()
    pygame.draw.rect(screen, (127, 127, 127), (0, 0, width, text_h + 20), 0)
    screen.blit(text, (int((width - text.get_width()) / 2), 10))


def draw_province_menu():  # Рисуем нижнее меню
    if menu_opened['country_choose']:  # Если у нас меню выбора страны
        font = pygame.font.Font(None, 30)
        country = get_country(gamemap.board[selected_province[0]])
        core = country.get_name()
        text = font.render(core, 1, (255, 255, 255))
        y = height - text.get_height() - 10
        text_h = text.get_height()
        pygame.draw.rect(screen, (127, 127, 127), (0, y - 10, width, text_h + 20), 0)
        screen.blit(text, (10, y))
        pygame.draw.rect(screen, (0, 0, 0), (width - 202, y - 10, 2, text_h + 20), 0)
        text = font.render("Начать Игру", 1, (255, 255, 255))
        screen.blit(text, (width - 190, y))
    else:  # Иначе
        font = pygame.font.Font(None, 30)
        text = font.render(gamemap.provs_names[selected_province[0]], 1, (255, 255, 255))
        x = text.get_width() + 10
        y = height - text.get_height() - 10
        text_h = text.get_height()
        pygame.draw.rect(screen, (127, 127, 127), (0, y - 10, width, text_h + 20), 0)
        screen.blit(text, (10, y))
        pygame.draw.rect(screen, (0, 0, 0), (x + 10, y - 10, 2, text_h + 20), 0)
        x = text.get_width() + 22
        country = get_country(gamemap.board[selected_province[0]])
        core = country.get_name()
        happy = gamemap.happiness[selected_province[0]]
        text = font.render("Счастье: " + str(happy) + ", владелец: " + core, 1, (255, 255, 255))
        screen.blit(text, (x + 10, y))
        if menu_opened['diplo'] and gamemap.selected_province != -1:  # Если открыто меню дипломатии
            cou = gamemap.board[gamemap.selected_province]  # Если страна не наш протишник и не мы
            if cou != player_country and cou not in countries[player_country].wars:
                pygame.draw.rect(screen, (0, 0, 0), (width - 202, y - 10, 2, text_h + 20), 0)
                text = font.render("Объявить войну", 1, (255, 255, 255))
                screen.blit(text, (width - 190, y))  # То рисуем "кнопку"


def draw_date():  # Рисуем дату
    font = pygame.font.Font(None, 20)
    d, m, y = tuple(str(i) for i in date)
    text = font.render(d if len(d) == 2 else '0' + d, 1, (255, 255, 255))
    text_h = text.get_height()
    pygame.draw.rect(screen, (127, 127, 127), (width - 70, 0, 70, text_h + 20), 0)
    screen.blit(text, (width - 67, 10))
    text = font.render('.' + m if len(m) == 2 else '.0' + m, 1, (255, 255, 255))
    screen.blit(text, (width - 51, 10))
    text = font.render('.' + y, 1, (255, 255, 255))
    screen.blit(text, (width - 33, 10))


def draw_diplopatia():  # Рисуем кнопку дипломатии
    font = pygame.font.Font(None, 20)
    text = font.render('Дипломатия', 1, (255, 255, 255))
    text_h = text.get_height()
    if menu_opened['diplo']:
        pygame.draw.rect(screen, (191, 191, 191), (width - 170, 0, 100, text_h + 20), 0)
    else:
        pygame.draw.rect(screen, (127, 127, 127), (width - 170, 0, 100, text_h + 20), 0)
    pygame.draw.rect(screen, (0, 0, 0), (width - 170, 0, 100, text_h + 20), 1)
    screen.blit(text, (width - 167, 10))


def draw_divisions_menu():  # Рисуем меню дивизий
    font = pygame.font.Font(None, 20)
    text = font.render('Дивизия', 1, (0, 0, 0))
    pygame.draw.rect(screen, (127, 127, 127), (0, 0, 99, height), 0)
    pygame.draw.rect(screen, (0, 0, 0), (99, 0, 2, height), 0)
    count = 0
    for i in divisions:  # И каждую выделенную дивизию
        if i.selected:
            info = i.return_info()[:2]
            pygame.draw.rect(screen, pygame.Color('green'), (0, count * 30 + 20,
                                                             100 * info[1] / info[0], 10), 0)
            pygame.draw.rect(screen, pygame.Color('yellow'), (0, count * 30, 99, 27), 2)
            pygame.draw.rect(screen, (0, 0, 0), (0, count * 30 + 28, 100, 2), 0)
            screen.blit(text, (10, count * 30 + 5))
            count += 1


def change_date():  # Меняем дату
    m = date[1]
    if date[0] == 28 and m == 2:
        del date[:2]
        date.insert(0, 1)
        date.insert(1, 3)
    elif date[0] == 30 and m in [4, 6, 9, 11]:
        del date[:2]
        date.insert(0, 1)
        date.insert(1, m + 1)
    elif date[0] == 31 and m in [1, 3, 5, 7, 8, 10, 12]:
        del date[:2]
        date.insert(0, 1)
        date.insert(1, m + 1)
        if m == 12:
            y = date[2]
            del date[1:]
            date.insert(1, 1)
            date.insert(2, y + 1)
    else:
        d = date[0]
        del date[0]
        date.insert(0, d + 1)


def get_difference_between_cords(xy1, xy2):  # Получаем различия между двумя координатами
    x1, y1 = xy1
    x2, y2 = xy2
    return x1 - x2, y1 - y2


def fix_screen():  # Делаем так, чтобы экран не выходил за край карты (да, именно экран)
    global LEFT, TOP
    if LEFT > 0:
        LEFT = 0
    elif LEFT < width + (left - right) * ZOOM / 100:
        LEFT = width + (left - right) * ZOOM / 100
    if TOP > 0:
        TOP = 0
    elif TOP < height + (top - bottom) * ZOOM / 100:
        TOP = height + (top - bottom) * ZOOM / 100


def change_zoom(n, pos):  # Изменяем приближение
    global ZOOM, LEFT, TOP
    ZOOM += n
    x, y = pos
    LEFT -= x
    LEFT *= ZOOM / (ZOOM - n)
    LEFT += x
    TOP -= y
    TOP *= ZOOM / (ZOOM - n)
    TOP += y
    fix_screen()
    gamemap.set_view(LEFT, TOP, ZOOM)


def change_pos_by_holding(pos):  # Изменяем положение, когда задерживаем мышкой
    global LEFT, TOP
    LEFT += pos[0]
    TOP += pos[1]
    fix_screen()


def actions_with_divisions():  # Действия с дивизиями
    for i in divisions:
        i.go()
        i.regeneration()


def select_division_from_list(n):  # Выбрать дивизию из списка
    count = 0
    for i in divisions:
        if i.selected:
            if count == n:  # Если её нашли,
                gamemap.deselect_whole_army()  # То отменяем выделение всей армии
                i.select(True)  # И выделяем её
                return None
            count += 1


def have_borders(country1, country2):  # Имеют ли две страны общие границы
    for i in range(gamemap.len_m):
        if gamemap.board[i] == country1 and \
                country2 in [gamemap.board[j] for j in gamemap.can_go[i]]:
            return True
    return False


def ai_actions():  # Действия ИИ
    for i_id in countries_ids:
        if i_id != player_country:  # Если это не наша страна
            is_at_war = False
            for j_id in countries_ids:  # Определяем, находится ли она в состоянии войны
                if j_id in countries[i_id].wars:
                    if have_borders(i_id, j_id):  # (точнее имеет ли границы с врагами и их самих)
                        is_at_war = True
                        break
            stop_moving(i_id, is_at_war)  # Отменяем перемещение некоторых войск
            for j_id in countries_ids:
                if j_id in countries[i_id].wars:  # Атакуем врагов и закрываем от них границу
                    close_borders_from_enemy(i_id, j_id)
                    attack_enemy(i_id, j_id)
                elif j_id != i_id and not is_at_war:  # Просто закрываем границу от соседей
                    close_borders_from_enemy(i_id, j_id, False)
            if get_count_of_divisions_of_country(i_id)[0] > 1 or random.randint(0, 9) == 1:
                for j_id in countries_ids:  # /\ Можем ли мы воевать
                    if random.randint(0, 100) == 1 and j_id != i_id:  # Шанс войны
                        if not is_at_war:  # Если не воюешь и имеешь границы с ним
                            if have_borders(i_id, j_id):
                                declare_war(i_id, j_id)
                        elif gamemap.board[14] == j_id:  # Или он имеет столицу
                            declare_war(i_id, j_id)


def load_scenario(scenario_name1):  # Загрузить сценарий
    global scenario_name
    directory = os.path.join('data', 'scenarios')
    file = open(os.path.join(directory, scenario_name1), 'r')
    data = file.read().split('\n')  # Получаем информацию о сценарии
    file.close()
    date.clear()
    scenario_name = data[0].strip()  # Название сценария
    for i in list(map(int, data[1].strip().split())):
        date.append(i)  # Дата
    cou = data[2].strip()  # Кто изначально владеет всей картой
    gamemap.board = [cou] * gamemap.len_m
    country = get_country(cou)
    gamemap.colors = [country.get_color()] * gamemap.len_m
    line = 4
    while data[line] != '':  # Пока не пройдём по всем странам
        cou, provs = tuple(data[line].strip().split(':'))
        for i in provs.split():  # Добавляем страны и передаём им территории
            gamemap.update_province(int(i), cou)
        line += 1
    line += 1
    while len(data) > line and data[line] != '':  # Пока не пройдём по всем дивизиям
        d = data[line].strip().split()  # Мы их добавляем
        divisions.append(Division(int(d[0]), int(d[1]), int(d[2]), int(d[3]), d[4]))
        line += 1
    line += 1
    while len(data) > line and data[line] != '':  # Пока не пройдём по всей дипломатии
        d = data[line].strip().split()
        if d[0] == 'war':  # Если введено war значит объявляем войну
            declare_war(d[1], d[2])
        line += 1


def load_game():  # Загружаем игру
    global gamemap, left, top, right, bottom, ZOOM, LEFT, TOP, IS_HOLDING, START_HOLDING_POS, \
        date, game_started, div_id, menu_opened, scenario_name
    scenario_name = ''  # А перед этим всё обнуляем
    selected_province.clear()
    countries.clear()
    countries_ids.clear()
    divisions.clear()
    gamemap = Provinces()
    left, top, right, bottom = gamemap.return_map_borders()
    ZOOM = 60
    LEFT, TOP = 0, 0
    IS_HOLDING = False
    START_HOLDING_POS = None
    date = [5, 2, 1927]
    load_scenario('The Second Yunnanese Civil War.txt')  # Загружаем сценарий
    gamemap.set_view(LEFT, TOP, ZOOM)
    game_started = False
    menu_opened = {'division': False, 'province': False, 'diplo': False, 'country_choose': False}
    div_id = 0


def draw():  # Русуем главное меню
    if game_started:
        return None
    font = pygame.font.Font(None, 100)
    text = font.render('Начать Игру', 1, (255, 255, 255))
    text_x = width // 2 - text.get_width() // 2
    text_y = sprite.rect.y + 660
    pygame.draw.rect(screen, (0, 0, 0), (350, sprite.rect.y + 650, 500, 90), 0)
    screen.blit(text, (text_x, text_y))


all_sprites = pygame.sprite.Group()  # Создаём группу спрайтов
sprite = pygame.sprite.Sprite()  # Задний фон
sprite.image = pygame.transform.scale(load_image("Chinese_republic_forever.jpg"), (width, height))
sprite.rect = sprite.image.get_rect()
all_sprites.add(sprite)

self_change_light = [0, True]  # Изменение цвета

MYEVENTTYPE = 30
pygame.time.set_timer(MYEVENTTYPE, 20)  # Таймер
load_game()

wait_ticks = 0  # Сколько ждать тиков
ADD_TICKS = 40  # Сколько прибавить тиков
time_is_running = False  # Идёт ли игровое время
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if game_started:  # Если началась игра
            if event.type == MYEVENTTYPE:
                screen.fill((0, 0, 127))
                gamemap.render()  # Рисуем...
                draw_diplopatia()
                draw_date()
                if menu_opened['province']:  # Если открыто меню провинций
                    draw_province_menu()
                if menu_opened['division']:  # ...меню армиии
                    draw_divisions_menu()
                if time_is_running:  # Если идёт игровое время,
                    wait_ticks += ADD_TICKS  # то добавляем тики
                if wait_ticks >= 200:  # Если тиков >= 200,
                    create_event()  # то создаём ивенты
                    gamemap.actions_with_provinces()  # происходят события с провинциями
                    wait_ticks = 0
                    change_date()  # изменяется дата
                    actions_with_divisions()  # происходят действия с дивизиями
                    ai_actions()  # ИИ делает действия
            if event.type == pygame.MOUSEBUTTONDOWN:  # Реакция на мышь
                if event.button == 1:
                    START_HOLDING_POS = event.pos  # Если нажата ЛКМ, то начинаем зажим
                elif event.button == 3:
                    gamemap.move_units(event.pos)  # Если нажата ПКМ, то перемещаем войска
                elif event.button == 4:
                    if ZOOM < 100:  # Если крутим колёсико мыши, то меняем размер карты
                        change_zoom(2, event.pos)
                elif event.button == 5:
                    if ZOOM > 60:
                        change_zoom(-2, event.pos)
            if event.type == pygame.MOUSEMOTION:  # Движение мыши
                if START_HOLDING_POS is not None:  # Если мы зажали ЛКМ,
                    IS_HOLDING = True  # то мы двигаем экран
                    change_pos_by_holding(get_difference_between_cords(event.pos,
                                                                       START_HOLDING_POS))
                    gamemap.set_view(LEFT, TOP, ZOOM)
                    START_HOLDING_POS = event.pos
            if event.type == pygame.MOUSEBUTTONUP:  # Отжимаем мышь
                if START_HOLDING_POS == event.pos and not IS_HOLDING:  # Если мы не перемещали экран
                    if event.pos[0] <= 100 and menu_opened['division']:  # Если открыто меню дивизий
                        select_division_from_list(event.pos[1] // 30)  # то, выбираем дивизию
                    elif event.pos[1] <= 30 and event.pos[0] + 170 >= width:
                        if event.pos[0] + 70 >= width:  # Если попали по дате,
                            if not time_is_running:  # то заставляем время течь/остановиться
                                time_is_running = True
                            else:
                                time_is_running = False
                        else:
                            if not menu_opened['diplo']:  # иначе открываем меню дипломатии
                                menu_opened['diplo'] = True
                            else:
                                menu_opened['diplo'] = False
                    elif event.pos[1] + 40 >= height and menu_opened['province']:
                        if event.pos[0] + 200 >= width and menu_opened['diplo'] and \
                                gamemap.selected_province != -1 and \
                                gamemap.board[gamemap.selected_province] != player_country and \
                                gamemap.board[gamemap.selected_province] not in \
                                countries[player_country].wars:  # Объявляем войну
                            declare_war(player_country, gamemap.board[gamemap.selected_province])
                    else:
                        gamemap.get_click(event.pos)  # Иначе делаем действие с картой
                START_HOLDING_POS = None
                IS_HOLDING = False
            if event.type == pygame.KEYDOWN:  # Если нажимаем на пробел,
                if event.key == pygame.K_SPACE:  # то заставляем время течь/остановиться
                    if not time_is_running:
                        time_is_running = True
                    else:
                        time_is_running = False
        else:
            if menu_opened['country_choose']:  # Если открыто меню выбора страны
                if event.type == MYEVENTTYPE:
                    screen.fill((0, 0, 127))
                    gamemap.render()
                    if menu_opened['province']:
                        draw_province_menu()  # Рисуем меню (не провинции) выбора страны
                    draw_scenario_name()  # Пишем название сценария
                    if sprite.rect.y < height:
                        sprite.rect.y += 1  # Если задний фон не ушёл, то его опускаем
                        sprite.rect.y *= 1.2
                    if self_change_light[1]:  # Меняем цвет
                        self_change_light[0] = self_change_light[0] + 1
                        if self_change_light[0] > 10:
                            self_change_light[1] = False
                    else:
                        self_change_light[0] = self_change_light[0] - 1
                        if self_change_light[0] < 1:
                            self_change_light[1] = True
                if event.type == pygame.MOUSEBUTTONDOWN:  # Реакция на мышь
                    if event.button == 1:
                        START_HOLDING_POS = event.pos  # Если нажата ЛКМ, то начинаем зажим
                    elif event.button == 3:
                        gamemap.move_units(event.pos)  # Если нажата ПКМ, то перемещаем войска
                    elif event.button == 4:
                        if ZOOM < 100:  # Если крутим колёсико мыши, то меняем размер карты
                            change_zoom(2, event.pos)
                    elif event.button == 5:
                        if ZOOM > 60:
                            change_zoom(-2, event.pos)
                if event.type == pygame.MOUSEMOTION:  # Движение мыши
                    if START_HOLDING_POS is not None:  # Если мы зажали ЛКМ,
                        IS_HOLDING = True  # то мы двигаем экран
                        change_pos_by_holding(
                            get_difference_between_cords(event.pos, START_HOLDING_POS))
                        gamemap.set_view(LEFT, TOP, ZOOM)
                        START_HOLDING_POS = event.pos
                if event.type == pygame.MOUSEBUTTONUP:  # Отжимаем мышь
                    if START_HOLDING_POS == event.pos and not IS_HOLDING:  # Мы не перемещали экран
                        if event.pos[1] + 40 >= height and menu_opened['province']:
                            if event.pos[0] + 200 >= width:  # Мы выбрали страну
                                player_country = gamemap.board[selected_province[0]]
                                menu_opened['province'] = False
                                menu_opened['country_choose'] = False
                                game_started = True  # И начинаем игру
                        else:
                            gamemap.get_click(event.pos)  # Иначе делаем действие с картой
                    START_HOLDING_POS = None
                    IS_HOLDING = False
            else:  # Иначе
                if event.type == pygame.MOUSEBUTTONDOWN:  # Если мы попали по "кнопке"
                    if 350 <= event.pos[0] <= 850 and 650 <= event.pos[1] <= 760:
                        load_game()  # Загружаем игру
                        menu_opened['country_choose'] = True  # Выбираем страну
            all_sprites.draw(screen)  # Рисуем...
            draw()
    pygame.display.flip()
pygame.quit()  # Закрываем игру...                                          И заканчиваем это читать
