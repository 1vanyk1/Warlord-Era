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
language = 'ru'
languages = {'en': 'english', 'ru': 'russian'}  # Планировались локализации но я не успел :)
player_country = 'yue'
divisions = []
menu_opened = {'division': False, 'province': False, 'diplo': False, 'country_choose': False}
div_id = 0


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


def get_army_of_province(pos, country=None):  # Узнаём, есть ли вообще в провинции армия
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
    pos1 = start_point
    pos2 = end_point
    w = gamemap.len_m
    a = [0 for _ in range(w)]  # Список, показывающий, была ли проверена провинция
    ways = [[] for _ in range(w)]  # Список, показывающий маршрут до этой провинции
    a[pos1] = 2
    while a[pos2] == 0:  # пока не найдём маршрут проверяем всю карту
        t = False
        for i in range(w):
            if a[i] == 2:
                if i == pos2:  # маршрут найден
                    return ways[pos2]
                t = True
                for j in gamemap.can_go[i]:
                    if a[j] == 0 and can_go(mass[j], country, hp, j):
                        a[j] = 2
                        ways[j] += ways[i] + [j]
                a[i] = 1
                ways[i] = []
        if not t:  # маршрут не найден
            return []
    return ways[pos2]  # маршрут найден


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
        data = self.generate_info(country_id)
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
        files = os.listdir(directory)
        if country_id in files:
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
        return False
    army = get_army_of_province(div.return_pos())
    if len(army) == 1:
        return False
    c = 0
    for i in army:
        if i.on_board == div.on_board and not i.is_moving():
            if c == 1:
                return True
            c += 1
    return False


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
    count, _ = get_count_of_divisions_of_country(country)
    count_on_border, borders_that_closed = get_count_of_divisions_of_country(country, enemy)
    border = delete_elems_from_mass(border, borders_that_closed)  # получаем незанятые границы
    if count != 0 and len(border) != 0:
        if count < len(border):  # армии мало
            c = 0
            border = random.sample(border, count)
            for i in divisions:
                if c == len(border):
                    break
                if i.country == country and (i.on_board is None or division_can_go_away(i) and
                                             needed):  # подходит, ли дивизия
                    b = border[c]
                    if i.return_pos() == b or i.find_path(b):
                        i.on_board = enemy  # каждой дивизии говорим, куда становиться
                    c += 1
        else:  # армии достаточно
            c = 0
            for i in divisions:
                if i.country == country and (i.on_board is None or division_can_go_away(i) and
                                             needed):  # подходит, ли дивизия
                    b = border[c]
                    if i.return_pos() == b or i.find_path(b):
                        i.on_board = enemy  # каждой дивизии говорим, куда становиться
                    c += 1
                    if c == len(border):
                        break


def attack_enemy(country, enemy):  # атака на врага
    for k in divisions:
        if k.country == country and k.on_board == enemy and not k.is_moving() and \
                k.hp / k.max_hp > 0.3:  # может ли дивизия атаковать
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
                if len(get_army_of_province(k.return_pos())) > 1 or random.randint(0, 3) == 1:
                    k.find_path(random.sample(border, 1)[0])
                elif len(border) == 1:  # узнаём, могут ли нам помочь наши соседи
                    t = False
                    for j in gamemap.can_go[border[0]]:  # узнаём, куда она может напасть
                        if gamemap.board[j] == country:
                            divs = get_army_of_province(j, country)
                            for div in divs:
                                if not div.is_moving():
                                    div.find_path(border[0])
                                    t = True
                    if t:
                        k.find_path(border[0])
            elif len(maybe_go) == 1 and c == 1 or random.randint(0, 3) == 1 and maybe_go:
                k.find_path(maybe_go[0])


def stop_moving(country):  # останавливаем дивизии, если надо
    for k in divisions:
        if k.country == country:
            i = k.return_pos_of_border()
            t = True
            if gamemap.board[i] == k.on_board:
                t = False
            else:
                for j in gamemap.can_go[i]:
                    if gamemap.board[j] == k.on_board:
                        t = False
                        break
            if t:
                k.on_board = None
                if k.where_is_going:
                    k.find_path(k.where_is_going[0])


# ИИ /\ ----------------------------------------------------------------------------------------


def change_color(color, n):
    r, g, b = color
    r, g, b = r + n, g + n, b + n
    if r < 0:
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
        files = os.listdir(directory)
        self.board = ['yue'] * len(files)
        country = get_country('yue')
        self.colors = [country.get_color()] * len(files)
        self.happiness = [50] * len(files)
        self.army = [] * len(files)
        self.left = 0
        self.top = 0
        self.cell_size = 0.5

        self.selected_province = -1
        self.borders = []
        self.can_go = []
        self.out_borders = []
        self.centres = []
        self.borders_with_others = []
        self.provs_rect = []
        self.provs_names = []

        for prov_id in sorted(files, key=lambda x: int(x.split('.')[0])):
            file = open(os.path.join(directory, prov_id), 'r')
            data = file.read().split('\n')
            file.close()
            d1 = data[0].split()
            self.centres.append((int(d1[0]), int(d1[1])))
            self.borders.append(
                [(int(d1[i * 2 + 2]), int(d1[i * 2 + 3])) for i in range(int(len(d1) / 2) - 1)])
            hor, ver = [int(i) for i in d1[2::2]], [int(i) for i in d1[3::2]]
            self.provs_rect.append([min(hor), min(ver), max(hor) - min(hor), max(ver) - min(ver)])
            out_borders = []
            for i in data[1].split(';'):
                t = i.split()
                if len(t) < 3:
                    continue
                out_borders.append([(int(t[j * 2]), int(t[j * 2 + 1])) for j in
                                    range(int(len(t) / 2))])
            self.out_borders.append(out_borders)
            con = sqlite3.connect("data/localisation/provs.db")
            cur = con.cursor()
            result = cur.execute(
                "SELECT " + languages[language] + " FROM provs WHERE id_name = " +
                prov_id.split('.')[0]).fetchone()[0]
            self.provs_names.append(result)
            con.close()
            if len(data) > 2:
                borders_with_others = {}
                can_g = []
                for text in data[2:]:
                    if text == '':
                        break
                    t = text.split(':')
                    if len(t[1].split('  ')) != 1:
                        n = int(t[0])
                        can_g.append(n)
                        out_borders = []
                        for i in t[1].split(';'):
                            t1 = i.split()
                            if len(t1) < 3:
                                continue
                            out_borders.append(
                                [(int(t1[j * 2]), int(t1[j * 2 + 1])) for j in
                                 range(int(len(t1) / 2))])
                        borders_with_others[n] = out_borders
                self.borders_with_others.append(borders_with_others)
                self.can_go.append(can_g)
            else:
                self.borders_with_others.append({})
                self.can_go.append([])
        self.len_m = len(self.borders)

    def return_map_borders(self):
        return min([min([j[0] for j in i]) for i in self.borders]), \
               min([min([j[1] for j in i]) for i in self.borders]), \
               max([max([j[0] for j in i]) for i in self.borders]), \
               max([max([j[1] for j in i]) for i in self.borders])

    def can_see_army(self, i):
        if self.board[i] == player_country or player_country in \
                [self.board[j] for j in self.can_go[i]]:
            return True
        return False

    def set_view(self, left, top, cell_size):
        self.left = left
        self.top = top
        self.cell_size = cell_size / 100

    def can_see_prov(self, i):
        return self.provs_rect[i][0] * self.cell_size <= width - self.left and \
               (self.provs_rect[i][0] + self.provs_rect[i][2]) * self.cell_size >= -self.left and \
               self.provs_rect[i][1] * self.cell_size <= height - self.top and \
               (self.provs_rect[i][1] + self.provs_rect[i][3]) * self.cell_size >= -self.top

    def render(self):
        for i in range(self.len_m):
            if self.can_see_prov(i):
                if menu_opened['diplo']:
                    if self.selected_province == -1:
                        cou = player_country
                    else:
                        cou = self.board[self.selected_province]
                    if self.board[i] == cou:
                        color = (0, 100, 200)
                    elif self.board[i] in countries[cou].wars:
                        color = (200, 0, 0)
                    else:
                        color = (100, 100, 100)
                    pygame.draw.polygon(screen, color, [(
                        self.left + p[0] * self.cell_size,
                        self.top + p[1] * self.cell_size) for p in self.borders[i]], 0)
                else:
                    if menu_opened['country_choose'] and self.selected_province != -1 and \
                            self.board[self.selected_province] == self.board[i]:
                        pygame.draw.polygon(screen, change_color(self.colors[i],
                                                                 self_change_light[0]),
                                            [(self.left + p[0] * self.cell_size,
                                              self.top + p[1] * self.cell_size)
                                             for p in self.borders[i]], 0)
                    else:
                        pygame.draw.polygon(screen, self.colors[i],
                                            [(self.left + p[0] * self.cell_size,
                                              self.top + p[1] * self.cell_size) for p in
                                             self.borders[i]], 0)
        for i in range(self.len_m):
            for k in self.out_borders[i]:
                pygame.draw.lines(screen, pygame.Color("white"), False,
                                  [(int(self.left + p[0] * self.cell_size),
                                    int(self.top + p[1] * self.cell_size)) for p in k], 2)
            for j in self.can_go[i]:
                if self.board[j] != self.board[i]:
                    for k in self.borders_with_others[i][j]:
                        pygame.draw.lines(screen, pygame.Color("white"), False,
                                          [(int(self.left + p[0] * self.cell_size),
                                            int(self.top + p[1] * self.cell_size)) for p in k], 2)
                elif ZOOM > 75:
                    for k in self.borders_with_others[i][j]:
                        pygame.draw.lines(screen, pygame.Color("gray"), False,
                                          [(int(self.left + p[0] * self.cell_size),
                                            int(self.top + p[1] * self.cell_size)) for p in k], 1)
        if self.selected_province != -1 and not menu_opened['country_choose']:
            for k in self.out_borders[self.selected_province]:
                pygame.draw.lines(screen, pygame.Color("yellow"), False,
                                  [(int(self.left + p[0] * self.cell_size),
                                    int(self.top + p[1] * self.cell_size)) for p in k], 2)
            for j in self.can_go[self.selected_province]:
                for k in self.borders_with_others[self.selected_province][j]:
                    pygame.draw.lines(screen, pygame.Color("yellow"), False,
                                      [(int(self.left + p[0] * self.cell_size),
                                        int(self.top + p[1] * self.cell_size)) for p in k], 2)
        if not menu_opened['country_choose']:
            for div in divisions:
                k = div.return_pos()
                if ZOOM > 75 and self.can_see_army(k):
                    selected = div.return_info()[3]
                    if selected:
                        steps = [k] + div.where_is_going
                        for step in range(len(steps) - 1):
                            pos1 = steps[step]
                            pos2 = steps[step + 1]
                            pygame.draw.line(screen, pygame.Color("red"),
                                             (self.left + self.centres[pos1][0] * self.cell_size,
                                              self.top + self.centres[pos1][1] * self.cell_size),
                                             (self.left + self.centres[pos2][0] * self.cell_size,
                                              self.top + self.centres[pos2][1] * self.cell_size), 5)
                        if len(steps) > 1:
                            pos1 = steps[0]
                            pos2 = steps[1]
                            hlntg = 1 - div.how_long_need_to_go / 5
                            cell_x = self.left + self.centres[pos1][0] * self.cell_size
                            cell_y = self.top + self.centres[pos1][1] * self.cell_size
                            pygame.draw.line(screen, (255, 127, 127), (cell_x, cell_y),
                                             (cell_x + (self.left + self.centres[pos2][0] *
                                                        self.cell_size - cell_x) * hlntg,
                                              cell_y + (self.top + self.centres[pos2][1] *
                                                        self.cell_size - cell_y) * hlntg), 5)
                            x1, y1 = self.centres[steps[-2]]
                            x2, y2 = self.centres[steps[-1]]
                            d_x, d_y = x1 - x2, y1 - y2
                            diag = (d_x ** 2 + d_y ** 2) ** 0.5
                            sin = d_y / diag * math.cos(math.pi / 6) + d_x / diag * math.sin(math.pi
                                                                                             / 6)
                            cos = d_x / diag * math.cos(math.pi / 6) - d_y / diag * math.sin(math.pi
                                                                                             / 6)
                            cell_x = self.left + x2 * self.cell_size
                            cell_y = self.top + y2 * self.cell_size
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
                if ZOOM > 75 and self.can_see_army(k):
                    selected = div.return_info()[3]
                    i, j = self.centres[k]
                    pygame.draw.rect(screen, pygame.Color("grey"),
                                     [(self.left + (i + 0.5) * self.cell_size - 29, self.top - 14 +
                                       (j + 0.5) * self.cell_size), (58, 28)], 0)
                    if selected:
                        pygame.draw.rect(screen, pygame.Color("yellow"),
                                         [(self.left + (i + 0.5) * self.cell_size - 30,
                                           self.top - 15 + (j + 0.5) * self.cell_size),
                                          (60, 30)], 4)
            for div in divisions:
                k = div.return_pos()
                if ZOOM > 75 and self.can_see_army(k):
                    max_hp, hp = div.return_info()[:2]
                    selected = div.return_info()[3]
                    i, j = self.centres[k]
                    if not selected:
                        if div.country in countries[player_country].wars:
                            pygame.draw.rect(screen, pygame.Color("red"),
                                             [(self.left + (i + 0.5) * self.cell_size - 29,
                                               self.top - 14 + (j + 0.5) * self.cell_size),
                                              (58, 28)], 2)
                        else:
                            pygame.draw.rect(screen, pygame.Color("black"),
                                             [(self.left + (i + 0.5) * self.cell_size - 29,
                                               self.top - 14 +
                                               (j + 0.5) * self.cell_size), (58, 28)], 2)
                    pygame.draw.rect(screen, pygame.Color("green"),
                                     [(self.left + (i + 0.5) * self.cell_size - 25, self.top + 1 +
                                       (j + 0.5) * self.cell_size), (int(hp * 50 / max_hp), 10)], 0)
                    pygame.draw.rect(screen, pygame.Color("black"),
                                     [(self.left + (i + 0.5) * self.cell_size - 26, self.top +
                                       (j + 0.5) * self.cell_size), (52, 12)], 1)

    def update_province(self, i, prov_id):
        country_before = self.board[i]
        self.board[i] = prov_id
        self.colors[i] = get_country(prov_id).get_color()
        for i in self.board:
            if country_before == i:
                return None
        countries_ids.remove(country_before)
        for i in countries_ids:
            peace(country_before, i)

    def move_units(self, mouse_pos):
        cell, b = self.get_cell(mouse_pos, True)
        self.find_path(player_country, cell, True)

    def get_click(self, mouse_pos):
        cell, b = self.get_cell(mouse_pos)
        self.on_click(cell, b)

    def get_cell(self, mouse_pos, is_moving=False):
        self.selected_province = -1
        for i in range(self.len_m):
            if self.can_see_prov(i):
                prov_original = pygame.Surface((self.provs_rect[i][2] * self.cell_size,
                                                self.provs_rect[i][3] * self.cell_size),
                                               pygame.SRCALPHA)
                pygame.draw.polygon(prov_original, (0, 0, 0), [
                    ((j[0] - self.provs_rect[i][0]) * self.cell_size,
                     (j[1] - self.provs_rect[i][1]) * self.cell_size) for j in self.borders[i]])
                prov = prov_original
                mouse_original = pygame.Surface((1, 1), pygame.SRCALPHA)
                pygame.draw.polygon(mouse_original, (255, 0, 0), [(0, 0), (0, 1), (1, 1), (1, 0)])
                mouse = mouse_original
                provrect = prov.get_rect(center=(self.left + (self.provs_rect[i][0] +
                                                              self.provs_rect[i][2] / 2) *
                                                 self.cell_size, self.top + (
                        self.provs_rect[i][1] + self.provs_rect[i][3] / 2) * self.cell_size))
                mask_prov = pygame.mask.from_surface(prov)
                mask_mouse = pygame.mask.from_surface(mouse)
                offset_red = provrect[0] - mouse_pos[0], provrect[1] - mouse_pos[1]
                overlap_prov = mask_mouse.overlap(mask_prov, offset_red)
                if overlap_prov:
                    if not is_moving:
                        if ZOOM > 75 and if_there_army_in_province(i) and \
                                abs(mouse_pos[0] - self.left - self.centres[i][0] *
                                    self.cell_size) <= 30 and \
                                abs(mouse_pos[1] - self.top - self.centres[i][1] *
                                    self.cell_size) <= 15:
                            return i, True
                        self.selected_province = i
                    return i, False
        return None, False

    def deselect_whole_army(self):
        for k in divisions:
            if k.country == player_country:
                k.select(False)

    def find_path(self, country, cell, need_to_be_selected=False):
        for k in divisions:
            if k.country == country and (not need_to_be_selected or k.selected):
                k.find_path(cell)

    def on_click(self, cell_coords, b):
        selected_province.clear()
        menu_opened['province'] = False
        menu_opened['division'] = False
        self.deselect_whole_army()
        if cell_coords is not None:
            selected_province.append(cell_coords)
            if b:
                if if_there_army_in_province(cell_coords):
                    t = False
                    for k in get_army_of_province(cell_coords):
                        if k.country == player_country:
                            k.select(True)
                            t = True
                    menu_opened['division'] = t
            else:
                menu_opened['province'] = True

    def actions_with_provinces(self):
        for i in range(self.len_m):
            if random.randint(1, 3) == 1:
                self.happiness[i] -= random.randint(-1, 1)
            if self.happiness[i] < 10 and random.randint(1, 5) == 1:
                self.happiness[i] = 60
                count_under_reb = self.board[i]
                declare_war(self.board[i], 'communists')
                self.update_province(i, 'communists')
                divisions.append(Division(50, 20, 40, i, 'communists'))
                divisions.append(Division(50, 20, 40, i, 'communists'))
                for ii in range(self.len_m):
                    if self.board[ii] == count_under_reb:
                        self.happiness[ii] -= random.randint(0, 5)
            if self.happiness[i] < 0:
                self.happiness[i] = 0
            elif self.happiness[i] > 100:
                self.happiness[i] = 100
            strength_1 = 0
            army_under_attack = [i for i in get_army_of_province(i) if not i.is_surviving]
            army_attacking = get_army_that_attacking_province(i, self.board[i])
            if army_attacking == [] or army_under_attack == []:
                continue
            for k in army_under_attack:
                strength_1 += k.strength
            strength_2 = 0
            for k in army_attacking:
                k.get_damage(random.randint(0, int(strength_1 / 10)))
                if k.hp < 5:
                    x = k.return_pos()
                    k.find_path(x)
                    k.on_board = None
                else:
                    strength_2 += k.strength
            for k in army_under_attack:
                k.get_damage(random.randint(0, int(strength_2 / 15)))
                if k.hp < 5:
                    k.try_to_survive()


class Division:
    def __init__(self, max_hp, hp, strength, pos, country):
        global div_id
        self.hp = hp
        self.max_hp = max_hp
        self.strength = strength
        self.selected = False
        self.country = country
        self.where_is_going = []
        self.how_long_need_to_go = 0
        self.pos = pos
        self.on_board = None
        self.id = div_id
        self.is_surviving = False
        div_id += 1

    def return_info(self):
        return self.max_hp, self.hp, self.strength, self.selected

    def select(self, b: bool):
        self.selected = b

    def find_path(self, end_pos):
        next_prov = None
        if self.is_surviving:
            return None
        if self.where_is_going:
            next_prov = self.where_is_going[0]
        self.where_is_going = find_path(gamemap.board, self.pos, end_pos, self.country,
                                        self.hp / self.max_hp)
        if self.where_is_going:
            if next_prov is None or not next_prov == self.where_is_going[0]:
                self.how_long_need_to_go = 5
            return True
        return False

    def go(self):
        if self.where_is_going:
            next_prov = self.where_is_going[0]
            for i in self.where_is_going:
                if not can_go(gamemap.board[i], self.country):
                    self.is_surviving = False
                    self.find_path(self.where_is_going[-1])
                    if not self.where_is_going:
                        self.how_long_need_to_go = 0
                        return None
                    if next_prov != self.where_is_going[0]:
                        self.how_long_need_to_go = 5
            if self.is_surviving:
                self.how_long_need_to_go -= 0.5
            else:
                self.how_long_need_to_go -= 1
            if self.how_long_need_to_go <= 0:
                p = self.where_is_going[0]
                if gamemap.board[p] in countries[self.country].wars and \
                        get_army_of_province(p) != []:
                    self.how_long_need_to_go += 1
                    return None
                self.pos = self.where_is_going.pop(0)
                self.is_surviving = False
                if gamemap.board[self.pos] in countries[self.country].wars:
                    gamemap.update_province(self.pos, self.country)
                self.how_long_need_to_go = 5
                if not self.where_is_going:
                    self.how_long_need_to_go = 0
                    if len(get_army_of_province(self.pos, self.country)) > 2:
                        self.on_board = None
        else:
            self.is_surviving = False
            if self.on_board is not None:
                t = True
                for i in gamemap.can_go[self.pos]:
                    if i == self.on_board:
                        t = False
                        break
                if t:
                    self.on_board = None

    def return_pos(self):
        return self.pos

    def return_pos_of_border(self):
        if not self.where_is_going:
            return self.pos
        return self.where_is_going[-1]

    def regeneration(self):
        if self.hp < self.max_hp:
            self.hp += random.randint(0, 1)

    def is_moving(self):
        if not self.where_is_going:
            return False
        return True

    def get_damage(self, damage):
        self.hp -= damage
        if self.hp <= 0:
            remove_division(self)

    def try_to_survive(self):
        if self.is_surviving:
            if not self.where_is_going:
                remove_division(self)
                return None
            else:
                return None
        i = self.pos
        can_go1 = []
        can_go2 = []
        for j in gamemap.can_go[self.pos]:
            if get_army_that_attacking_province(j, self.country) == [] and \
                    can_go(gamemap.board[i], self.country, 0.1, j):
                if gamemap.board[j] == self.country:
                    can_go1.append(j)
                else:
                    can_go2.append(j)
        if can_go1:
            self.find_path(random.sample(can_go1, 1)[0])
            self.is_surviving = True
            if not self.where_is_going:
                remove_division(self)
        elif can_go2:
            self.find_path(random.sample(can_go2, 1)[0])
            self.is_surviving = True
            if not self.where_is_going:
                remove_division(self)
        else:
            remove_division(self)


def remove_division(div):
    try:
        divisions.remove(div)
    except:
        pass
    finally:
        pass


def create_event():
    if date == [7, 4, 1927]:
        declare_war(gamemap.board[17], 'jiang_yingshu')
        declare_war(gamemap.board[14], 'jiang_yingshu')
        gamemap.update_province(17, 'jiang_yingshu')
        divisions.append(Division(50, 30, 50, 17, 'jiang_yingshu'))
        divisions.append(Division(50, 30, 50, 17, 'jiang_yingshu'))
        divisions.append(Division(50, 30, 50, 17, 'jiang_yingshu'))
    elif date == [20, 1, 1928]:
        declare_war(gamemap.board[23], 'jiang_jieba')
        declare_war(gamemap.board[14], 'jiang_jieba')
        gamemap.update_province(23, 'jiang_jieba')
        divisions.append(Division(50, 30, 50, 23, 'jiang_jieba'))
    elif date == [14, 12, 1928]:
        declare_war(gamemap.board[5], 'li_shen')
        declare_war(gamemap.board[6], 'li_shen')
        declare_war(gamemap.board[7], 'li_shen')
        declare_war(gamemap.board[14], 'li_shen')
        gamemap.update_province(5, 'li_shen')
        gamemap.update_province(6, 'li_shen')
        gamemap.update_province(7, 'li_shen')
        divisions.append(Division(50, 30, 50, 5, 'li_shen'))
        divisions.append(Division(50, 30, 50, 6, 'li_shen'))
        divisions.append(Division(50, 30, 50, 7, 'li_shen'))


def draw_scenario_name():
    font = pygame.font.Font(None, 30)
    text = font.render(scenario_name, 1, (255, 255, 255))
    text_h = text.get_height()
    pygame.draw.rect(screen, (127, 127, 127), (0, 0, width, text_h + 20), 0)
    screen.blit(text, (int((width - text.get_width()) / 2), 10))


def draw_province_menu():
    if menu_opened['country_choose']:
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
    else:
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
        if menu_opened['diplo'] and gamemap.selected_province != -1:
            cou = gamemap.board[gamemap.selected_province]
            if cou != player_country and cou not in countries[player_country].wars:
                pygame.draw.rect(screen, (0, 0, 0), (width - 202, y - 10, 2, text_h + 20), 0)
                text = font.render("Объявить войну", 1, (255, 255, 255))
                screen.blit(text, (width - 190, y))


def draw_date():
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


def draw_diplopatia():
    font = pygame.font.Font(None, 20)
    text = font.render('Дипломатия', 1, (255, 255, 255))
    text_h = text.get_height()
    if menu_opened['diplo']:
        pygame.draw.rect(screen, (191, 191, 191), (width - 170, 0, 100, text_h + 20), 0)
    else:
        pygame.draw.rect(screen, (127, 127, 127), (width - 170, 0, 100, text_h + 20), 0)
    pygame.draw.rect(screen, (0, 0, 0), (width - 170, 0, 100, text_h + 20), 1)
    screen.blit(text, (width - 167, 10))


def draw_divisions_menu():
    font = pygame.font.Font(None, 20)
    text = font.render('Дивизия', 1, (0, 0, 0))
    pygame.draw.rect(screen, (127, 127, 127), (0, 0, 99, height), 0)
    pygame.draw.rect(screen, (0, 0, 0), (99, 0, 2, height), 0)
    count = 0
    for i in divisions:
        if i.selected:
            info = i.return_info()[:2]
            pygame.draw.rect(screen, pygame.Color('green'), (0, count * 30 + 20,
                                                             100 * info[1] / info[0], 10), 0)
            pygame.draw.rect(screen, pygame.Color('yellow'), (0, count * 30, 99, 27), 2)
            pygame.draw.rect(screen, (0, 0, 0), (0, count * 30 + 28, 100, 2), 0)
            screen.blit(text, (10, count * 30 + 5))
            count += 1


def change_date():
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


def get_difference_between_cords(xy1, xy2):
    x1, y1 = xy1
    x2, y2 = xy2
    return x1 - x2, y1 - y2


def fix_screen():
    global LEFT, TOP
    if LEFT > 0:
        LEFT = 0
    elif LEFT < width + (left - right) * ZOOM / 100:
        LEFT = width + (left - right) * ZOOM / 100
    if TOP > 0:
        TOP = 0
    elif TOP < height + (top - bottom) * ZOOM / 100:
        TOP = height + (top - bottom) * ZOOM / 100


def change_zoom(n, pos):
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


def change_pos_by_holding(pos):
    global LEFT, TOP
    LEFT += pos[0]
    TOP += pos[1]
    fix_screen()


def actions_with_divisions():
    for i in divisions:
        i.go()
        i.regeneration()


def select_division_from_list(n):
    count = 0
    for i in divisions:
        if i.selected:
            if count == n:
                gamemap.deselect_whole_army()
                i.select(True)
                return None
            count += 1


def ai_actions():
    for i_id in countries_ids:
        if i_id != player_country:
            stop_moving(i_id)
            is_at_war = False
            for j_id in countries_ids:
                if j_id in countries[i_id].wars:
                    is_at_war = True
                    close_borders_from_enemy(i_id, j_id)
                    attack_enemy(i_id, j_id)
                elif j_id != i_id:
                    close_borders_from_enemy(i_id, j_id, False)
            if get_count_of_divisions_of_country(i_id)[0] > 1:
                for j_id in countries_ids:
                    if not is_at_war and j_id != i_id and random.randint(0, 100) == 1:
                        declare_war(i_id, j_id)
                    elif gamemap.board[14] == j_id and random.randint(0, 100) == 1:
                        declare_war(i_id, j_id)


def load_scenario(scenario_name1):
    global scenario_name
    directory = os.path.join('data', 'scenarios')
    file = open(os.path.join(directory, scenario_name1), 'r')
    data = file.read().split('\n')
    file.close()
    date.clear()
    scenario_name = data[0].strip()
    for i in list(map(int, data[1].strip().split())):
        date.append(i)
    cou = data[2].strip()
    gamemap.board = [cou] * gamemap.len_m
    country = get_country(cou)
    gamemap.colors = [country.get_color()] * gamemap.len_m
    line = 4
    while data[line] != '':
        cou, provs = tuple(data[line].strip().split(':'))
        for i in provs.split():
            gamemap.update_province(int(i), cou)
        line += 1
    line += 1
    while len(data) > line and data[line] != '':
        d = data[line].strip().split()
        divisions.append(Division(int(d[0]), int(d[1]), int(d[2]), int(d[3]), d[4]))
        line += 1
    line += 1
    while len(data) > line and data[line] != '':
        d = data[line].strip().split()
        if d[0] == 'war':
            declare_war(d[1], d[2])
        line += 1


def load_game():
    global gamemap, left, top, right, bottom, ZOOM, LEFT, TOP, IS_HOLDING, START_HOLDING_POS, \
        date, game_started, div_id, menu_opened, scenario_name
    scenario_name = ''
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
    load_scenario('The Second Yunnanese Civil War.txt')
    gamemap.set_view(LEFT, TOP, ZOOM)
    game_started = False
    menu_opened = {'division': False, 'province': False, 'diplo': False, 'country_choose': False}
    div_id = 0


def draw():
    if game_started:
        return None
    font = pygame.font.Font(None, 100)
    text = font.render('Начать Игру', 1, (255, 255, 255))
    text_x = width // 2 - text.get_width() // 2
    text_y = sprite.rect.y + 660
    pygame.draw.rect(screen, (0, 0, 0), (350, sprite.rect.y + 650, 500, 90), 0)
    screen.blit(text, (text_x, text_y))


all_sprites = pygame.sprite.Group()
sprite = pygame.sprite.Sprite()
sprite.image = pygame.transform.scale(load_image("Chinese_republic_forever.jpg"), (width, height))
sprite.rect = sprite.image.get_rect()
all_sprites.add(sprite)

self_change_light = [0, True]

MYEVENTTYPE = 30
pygame.time.set_timer(MYEVENTTYPE, 20)
load_game()

wait_ticks = 0
ADD_TICKS = 8
time_is_running = False
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
        if game_started:
            if event.type == MYEVENTTYPE:
                screen.fill((0, 0, 127))
                gamemap.render()
                draw_diplopatia()
                draw_date()
                if menu_opened['province']:
                    draw_province_menu()
                if menu_opened['division']:
                    draw_divisions_menu()
                if time_is_running:
                    wait_ticks += ADD_TICKS
                if wait_ticks == 200:
                    create_event()
                    gamemap.actions_with_provinces()
                    wait_ticks = 0
                    change_date()
                    actions_with_divisions()
                    ai_actions()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    START_HOLDING_POS = event.pos
                elif event.button == 3:
                    gamemap.move_units(event.pos)
                elif event.button == 4:
                    if ZOOM < 100:
                        change_zoom(2, event.pos)
                elif event.button == 5:
                    if ZOOM > 60:
                        change_zoom(-2, event.pos)
            if event.type == pygame.MOUSEMOTION:
                if START_HOLDING_POS is not None:
                    IS_HOLDING = True
                    change_pos_by_holding(get_difference_between_cords(event.pos,
                                                                       START_HOLDING_POS))
                    gamemap.set_view(LEFT, TOP, ZOOM)
                    START_HOLDING_POS = event.pos
            if event.type == pygame.MOUSEBUTTONUP:
                if START_HOLDING_POS == event.pos and not IS_HOLDING:
                    if event.pos[0] <= 100 and menu_opened['division']:
                        select_division_from_list(event.pos[1] // 30)
                    elif event.pos[1] <= 30:
                        if event.pos[0] + 70 >= width:
                            if not time_is_running:
                                time_is_running = True
                            else:
                                time_is_running = False
                        elif event.pos[0] + 170 >= width:
                            if not menu_opened['diplo']:
                                menu_opened['diplo'] = True
                            else:
                                menu_opened['diplo'] = False
                    elif event.pos[1] + 30 >= height:
                        if event.pos[0] + 200 >= width and menu_opened['diplo'] and \
                                gamemap.selected_province != -1 and \
                                gamemap.board[gamemap.selected_province] != player_country and \
                                gamemap.board[gamemap.selected_province] not in \
                                countries[player_country].wars:
                            declare_war(player_country, gamemap.board[gamemap.selected_province])
                    else:
                        gamemap.get_click(event.pos)
                START_HOLDING_POS = None
                IS_HOLDING = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if not time_is_running:
                        time_is_running = True
                    else:
                        time_is_running = False
        else:
            if menu_opened['country_choose']:
                if event.type == MYEVENTTYPE:
                    screen.fill((0, 0, 127))
                    gamemap.render()
                    if menu_opened['province']:
                        draw_province_menu()
                    draw_scenario_name()
                    if sprite.rect.y < height:
                        sprite.rect.y += 1
                        sprite.rect.y *= 1.1
                    if self_change_light[1]:
                        self_change_light[0] = self_change_light[0] + 1
                        if self_change_light[0] > 10:
                            self_change_light[1] = False
                    else:
                        self_change_light[0] = self_change_light[0] - 1
                        if self_change_light[0] < 1:
                            self_change_light[1] = True
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        START_HOLDING_POS = event.pos
                    elif event.button == 3:
                        gamemap.move_units(event.pos)
                    elif event.button == 4:
                        if ZOOM < 100:
                            change_zoom(2, event.pos)
                    elif event.button == 5:
                        if ZOOM > 60:
                            change_zoom(-2, event.pos)
                if event.type == pygame.MOUSEMOTION:
                    if START_HOLDING_POS is not None:
                        IS_HOLDING = True
                        change_pos_by_holding(
                            get_difference_between_cords(event.pos, START_HOLDING_POS))
                        gamemap.set_view(LEFT, TOP, ZOOM)
                        START_HOLDING_POS = event.pos
                if event.type == pygame.MOUSEBUTTONUP:
                    if START_HOLDING_POS == event.pos and not IS_HOLDING:
                        if event.pos[1] + 30 >= height:
                            if event.pos[0] + 200 >= width and menu_opened['province']:
                                player_country = gamemap.board[selected_province[0]]
                                menu_opened['province'] = False
                                menu_opened['country_choose'] = False
                                game_started = True
                        else:
                            gamemap.get_click(event.pos)
                    START_HOLDING_POS = None
                    IS_HOLDING = False
            else:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if 350 <= event.pos[0] <= 850 and 650 <= event.pos[1] <= 760:
                        load_game()
                        menu_opened['country_choose'] = True
            all_sprites.draw(screen)
            draw()
    pygame.display.flip()
pygame.quit()
