import math
import pygame
from collections import OrderedDict as ordered

import drawing

_INERT_THRESH = 1024.0 / (1000.0  * 64.0)
_INERT_FRICTS = 1.12
_INERT_HOLDON = 4.0

class UIElement(object):
    def __init__(self, globj):
        self.globj = globj
        self.draws = ordered()

    def render(self):
        self.globj.draw()

        for name in self.draws:
            draw, x, y = self.draws[name]

            drawing.shift((x, y))
            draw.render()
            drawing.shift()

    def insert(self, name, draw, x=0.0, y=0.0):
        self.draws[name] = (draw, x, y)

    def delete(self, name):
        if name in self.draws:
            del self.draws[name]

    def rect(self):
        return self.globj.rect()

class UIScreen(UIElement):
    surf_flags = pygame.DOUBLEBUF | pygame.OPENGL

    def make(self, (x, y)):
        flags = UIScreen.surf_flags
        if not x or not y:
            flags |= pygame.FULLSCREEN
            x, y = pygame.display.list_modes(0, flags)[0]
        pygame.display.set_mode((x, y), flags, 24)
        pygame.mouse.set_visible(False)
        pygame.key.set_repeat(333, 33)

        return x, y

    def calc(self, (x, y)):
        self.XLEN = float(x)
        self.YLEN = float(y)
        self._XLO = 0.0
        self._XHI = float(x)
        self._YLO = 0.0
        self._YHI = float(y)
        self.XC   = (self._XLO + self._XHI) / 2.0
        self.YC   = (self._YLO + self._YHI) / 2.0
        self.DIAG = math.hypot(self.XC, self.YC)

    def __init__(self, (x, y)):
        x, y = self.make((x, y))
        self.calc((x, y))
        super(UIScreen, self).__init__(drawing.Screen((x, y)))

        self.font = drawing.Font(pygame.font.Font(pygame.font.match_font("consolas", bold=True), 21))

    def render(self):
        super(UIScreen, self).render()
        pygame.display.flip()

class UIBoard(UIElement):
    def __init__(self, root, rect, round=False, clamp=False):
        self.root = root

        super(UIBoard, self).__init__(drawing.TexTile(rect, self.root.rect()))
        self.root.insert('board', self)

        self.round = round
        self.clamp = clamp

        self.dx, self.dy = 0.0, 0.0
        self.scale = [ 1.0, 1.0 ]
        self.angle = 0.0
        self.degrs = 0.0

        self.ax, self.ay = 0.0, 0.0
        self.aangle = 0.0

        self.cmarks = [ UIElement(drawing.CrossMark((self.root.XC, self.root.YC), 32.0, 0.0)) ]
        for mark in self.cmarks:
            self.insert('center', mark)

        def sround(): self.round = not self.round
        def sclamp():
            self.clamp = not self.clamp
            if self.clamp: self._clamp()

        self.events = {
            '_round': sround,
            '_clamp': sclamp,

            '_vsync': lambda: drawing.vsync(),
            'center': lambda: (self.moveto((0.0, 0.0)), self.breaks(True, True)),
            'noturn': lambda: (self.turnto(0.0), self.breaks(True, True)),
            'nozoom': lambda: (self.zoomto(0.0, False), self.breaks(True, True)),

            'turn_f': lambda: self.turnon(-1),
            'turn_b': lambda: self.turnon(+1),
            'zoom_o': lambda: self.zoomon(-1, False),
            'zoom_i': lambda: self.zoomon(+1, False),
            'move_l': lambda: self.moveon((-16, 0)),
            'move_r': lambda: self.moveon((+16, 0)),
            'move_u': lambda: self.moveon((0, -16)),
            'move_d': lambda: self.moveon((0, +16)),

            'zoomon': lambda chzm: self.zoomon(chzm),
            'zoomto': lambda zoom: self.zoomto(zoom),
            'moveon': lambda *args: self.moveon(*args),
            'moveto': lambda *args: self.moveto(*args),
            'turnon': lambda turn: self.turnon(turn),
            'turnto': lambda turn: self.turnto(turn),

            'rotate': lambda *args: self.rotate(*args),
        }

    def normal(self):
        cx, cy = self.rect()
        dx = ((self.dx + cx/2) % cx) - cx/2
        dy = ((self.dy + cy/2) % cy) - cy/2
        return (-dx, -dy)

    def _clamp(self, negate=False):
        def normalize(c, n): return ((c + n/2) % n) - n/2
        def rotation((x,y), angle):
            cos, sin = math.cos(angle), math.sin(angle)
            return (x * cos - y * sin, x * sin + y * cos)

        cx, cy = self.rect()
        ax, ay = rotation((self.dx, self.dy), -self.angle)

        if abs(ax) > self.root.XC or abs(ay) > self.root.YC:
            cx *= self.scale[True]
            cy *= self.scale[True]

        self.dx, self.dy = normalize(self.dx, cx), normalize(self.dy, cy)

    def totexhelper(self, (rx, ry), center=False):
        ax, ay = rx - self.root.XC, ry - self.root.YC
        rx = ax * math.cos(self.angle) - ay * math.sin(self.angle)
        ry = ax * math.sin(self.angle) + ay * math.cos(self.angle)
        return (rx, ry)

    def totexcoords(self, (rx, ry), forgl=False, forui=False):
        # angle
        tx, ty = self.totexhelper((rx, ry))

        # shift and scale
        tx = (tx - self.dx)/self.scale[True] + self.rect()[0]/2.0
        ty = (ty - self.dy)/self.scale[True] + self.rect()[1]/2.0

        # adopt
        if forgl:
            tx /= self.rect()[0]
            ty /= self.rect()[1]
        else:
            tx %= self.rect()[0]
            ty %= self.rect()[1]

        if forui:
            tx -= self.rect()[0]/2.0
            ty -= self.rect()[1]/2.0

        return tx, ty

    def rscale(self, dscale, cursor):
        self.scale[False] *= dscale
        tscale = max(2.0 ** -4.0, min(2.0 ** 8.0, self.scale[False]))
        dscale = tscale / self.scale[True]

        rx, ry = self.totexhelper(cursor and pygame.mouse.get_pos() or (self.root.XC, self.root.YC))

        if dscale:
            self.dx *= dscale
            self.dx += rx * (1 - dscale)
            self.dy *= dscale
            self.dy += ry * (1 - dscale)
            self.scale[True] *= dscale
        return self.scale[True]

    def zoomon(self, zoom, cursor=True):
        return self.rscale((2.0 ** zoom), cursor)

    def zoomto(self, zoom, cursor=True):
        return self.rscale((2.0 ** zoom) / self.scale[False], cursor)

    def center(self, (rx, ry), zoom=0):
        ax, ay = self.totexhelper((rx, ry))
        self.dx -= ax
        self.dy -= ay

        self.zoomon(zoom, False)

    def moveon(self, (dx, dy), inerts=False):
        ax = dx * math.cos(self.angle) - dy * math.sin(self.angle)
        ay = dx * math.sin(self.angle) + dy * math.cos(self.angle)

        self.dx -= ax
        self.dy -= ay

        if inerts:
            self.ax += _INERT_HOLDON * dx
            self.ay += _INERT_HOLDON * dy

        return self.normal()

    def moveto(self, (dx, dy)):
        self.dx, self.dy = float(-dx), float(-dy)
        return self.normal()

    def rotate(self, was, now, rotate):
        was = was[0] - self.root.XC, was[1] - self.root.YC
        now = now[0] - self.root.XC, now[1] - self.root.YC

        waslen, nowlen = max(math.hypot(was[0], was[1]), 0.0001), max(math.hypot(now[0], now[1]), 0.0001)

        if rotate:
            crossp = lambda v1, v2: v1[0]*v2[1] - v1[1]*v2[0]
            dangle = math.degrees((waslen and nowlen) and math.asin(crossp(was, now) / (waslen * nowlen)) or 0.0)
            self.turnon(dangle, True)
        else:
            self.rscale(nowlen / waslen, False)

    def turnon(self, dangle, inerts=False):
        self.angle -= math.radians(dangle)
        self.degrs = ((math.degrees(self.angle) + 180) % 360) - 180
        self.cmarks[0].globj.update((self.root.XC, self.root.YC), 32.0, self.angle)

        if inerts: self.aangle += _INERT_HOLDON * dangle

        return -self.degrs

    def turnto(self, dangle):
        self.angle = -math.radians(dangle)
        self.degrs = ((math.degrees(self.angle) + 180) % 360) - 180
        self.cmarks[0].globj.update((self.root.XC, self.root.YC), 32.0, self.angle)
        return -self.degrs

    def inerts(self, nomove, noturn):
        self.ax /= (nomove and _INERT_HOLDON or _INERT_FRICTS)
        self.ay /= (nomove and _INERT_HOLDON or _INERT_FRICTS)
        self.aangle /= (noturn and _INERT_HOLDON or _INERT_FRICTS)

        if not nomove:
            if abs(self.ax) > _INERT_THRESH or abs(self.ay) > _INERT_THRESH:
                self.moveon((self.ax, self.ay))
            else:
                self.ax, self.ay = 0.0, 0.0

        if not noturn:
            if abs(self.aangle) > _INERT_THRESH:
                self.turnon(self.aangle)
            else:
                self.aangle = 0.0

    def breaks(self, nomove=False, noturn=False):
        actual = False
        if nomove:
            if abs(self.ax) > _INERT_THRESH or abs(self.ay) > _INERT_THRESH:
                self.ax, self.ay = 0.0, 0.0
                actual = True
        if noturn:
            if abs(self.aangle) > _INERT_THRESH:
                self.aangle = 0.0
                actual = True
        return actual

    def update(self, data):
        self.globj.update(data)

    def frame(self):
        self.globj.params(self.clamp, self.round)

        points = [ (0.0, 0.0), (self.root.XLEN, 0.0), (self.root.XLEN, self.root.YLEN), (0.0, self.root.YLEN) ]
        for i, p in enumerate(points): points[i] = self.totexcoords(p, forgl=True)

        self.globj.format(points)

    def uicoords(self, mark):
        return self.totexcoords(mark and pygame.mouse.get_pos() or (self.root.XC, self.root.YC), forui=True)

    def uiparams(self):
        return self.scale[True], -self.degrs

class UICursor():
    def __init__(self, root, radius):
        self.root = root

        self.canvas = UIElement(drawing.DrawCursor())
        self.pointr = UIElement(drawing.DrawCursor())
#        self.scaled = UIElement(drawing.DrawCursor())

        self.border = pygame.Color('Green')
        self.radius = radius

        self.scaled = None

        self.action(False)
        self.frame()

        self.events = {
            'shrink': lambda: self.resize(-1),
            'expand': lambda: self.resize(+1),
        }

    def action(self, draws=None):
        if draws == None:
            self.draws = not self.draws
        else:
            self.draws = draws
        self.border.a = self.draws and 0x40 or 0xFF
        return self

    def frame(self):
        if self.scaled != self.root.scale[True]:
            self.scaled = self.root.scale[True]

            self.canvas.globj.update((self.radius - 0.5) * self.scaled, self.border)
            self.pointr.globj.update(0.5 * self.scaled, self.border)
            #self.scaled.globj.update(8, pygame.Color('Red'))

        mx, my = pygame.mouse.get_pos()
        self.root.insert('cursor', self.canvas, mx, my)
        self.root.insert('pointr', self.pointr, mx, my)
#        self.root.insert('scaled', self.scaled, mx, my)

    def resize(self, delta):
        if not delta: return 0.0
        elif delta > 0:
            delta = self.radius < 4 and +1 or +4
        elif delta < 0:
            delta = self.radius > 4 and -4 or -1

        if 1 <= self.radius + delta <= 128:
            self.radius += delta
            self.scaled = None

        return delta

