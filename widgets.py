import pygame
import time
import sys

import graphic
import drawing

import code

VERSION = " 0.0.4.5.20120101 "
VENGINE = ""

BORDERX = 8
BORDERY = 4

_UICONS_NONE = 0
_UICONS_LINE = 1
_UICONS_FULL = 2
_UICONS_NTOTAL = 3

_UI_SYMBOLS = 128

class Console(object):
    def __init__(self, root, vengine, **kwargs):
        self.context = {    'quit' : lambda: self.onoff(state=_UICONS_NONE),
                            'exit' : lambda: self.onoff(state=_UICONS_NONE),
                            'clear' : lambda: self.clear()                      }
        self.context.update(**kwargs)

        self.interp = code.InteractiveConsole(self.context)

        self.root = root
        self.font = root.font
        self.symsize = self.font.rect()

        self.colors = (pygame.Color(0x20, 0x20, 0x20, 0xC0), pygame.Color(0x00, 0x80, 0xFF, 0xC0))

        self.curbox = graphic.UIElement(drawing.Widget((self.symsize[0], 4), colors=(pygame.Color(0x00, 0xFF, 0x00, 0xC0), None)))
        self.cursor = False

        self.nlines = self._dosym((self.symsize[0] * _UI_SYMBOLS + 2 * BORDERX, self.root.rect()[1] - self.font.rect()[1] - 2 * BORDERY))[1]
        self.oprint = graphic.UIElement(self.font.text(_UI_SYMBOLS * self.nlines))
        self.iprint = graphic.UIElement(self.font.text(_UI_SYMBOLS * self.nlines))

        self.canvas = graphic.UIElement(drawing.Widget((0.0, 0.0), colors=self.colors))
        self._cmode()

        self.history = [ "" ]
        self.histpos = 0
        self.histcut = 0
        self.curpos = 0

        self.orig_stdout, sys.stdout = sys.stdout, self
        self.orig_stderr, sys.stderr = sys.stderr, self

        global VENGINE
        VENGINE = vengine
        self.clear()

    def __del__(self):
        sys.stdout = self.orig_stdout
        sys.stderr = self.orig_stderr

    def _dosym(self, rect):
        return (int((rect[0] - 2*BORDERX) / self.symsize[0]), int((rect[1] - 2*BORDERY) / self.symsize[1]))

    def _cline(self):
        rect = (self.symsize[0] * _UI_SYMBOLS + 2 * BORDERX, self.symsize[1] + 2 * BORDERY)
        self.symbols = self._dosym(rect)
        self.canvas.globj.rect(rect)
        self.root.insert('console', self.canvas, (self.root.rect()[0] - rect[0]) / 2.0, 0.0)

    def _cfull(self):
        rect = (self.symsize[0] * _UI_SYMBOLS + 2 * BORDERX, self.root.rect()[1] - self.font.rect()[1] - 2 * BORDERY)
        self.symbols = self._dosym(rect)
        self.canvas.globj.rect(rect)
        self.root.insert('console', self.canvas, (self.root.rect()[0] - rect[0]) / 2.0, 0.0)

    def _cfree(self):
        rect = (self.root.rect()[0] * 0.75, self.root.rect()[1] * 0.75)
        self.symbols = self._dosym(rect)
        self.canvas.globj.rect(rect)
        self.root.insert('console', self.canvas, (self.root.rect()[0] - rect[0]) / 2.0, (self.root.rect()[1] - rect[1]) / 2.0)

    def _cmode(self, shown=None):
        self.shown = shown and shown or _UICONS_NONE
        [ self._cline, self._cline, self._cfull ][self.shown]()

    def onoff(self, onoff=None, state=None):
        if state is not None:
            shown = state
        elif onoff:
            shown = self.shown + 1
        else:
            shown = self.shown - 1
        self._cmode(shown % _UICONS_NTOTAL)

        self.doout()
        self.do_in(self.history[self.histpos], False)

    def blink(self):
        self.cursor = not self.cursor
        self.cmove(self.curpos)

    def cmove(self, curpos):
        self.curpos = curpos

    def frame(self):
        if not self.canvas: return

        if self.ofresh:
            self.ofresh = False
            self.font.render(self.oprint.globj, '\n'.join(self.olines))
            self.canvas.insert('output', self.oprint, BORDERX, BORDERY)

        if self.ifresh:
            self.ifresh = False
            self.font.render(self.iprint.globj, '\n'.join(self.ilines[-self.symbols[1]:]))
            self.canvas.insert('input', self.iprint, BORDERX, BORDERY + (len(self.olines) * self.symsize[1]))

        if self.shown and self.cursor:
            cx = BORDERX + ((len(self.prompt) + 1 + self.curpos)%self.symbols[0]) * self.symsize[0]
            ls = (len(self.olines) + ((len(self.prompt) + 1 + self.curpos) / self.symbols[0]))
            cy = BORDERY + min(ls + 1, self.symbols[1]) * self.symsize[1] - 4
            self.canvas.insert('cursor', self.curbox, cx, cy)
        else:
            self.canvas.delete('cursor')

    def doout(self):
        if self.symbols[1] <= 1:
            self.olines = []
        elif self.buffer:
            self.olines = self.output[-self.symbols[1]+self.innoff+2:] + [self.buffer]
        else:
            self.olines = self.output[-self.symbols[1]+self.innoff+1:]

        self.ofresh = True

    def write(self, string):
        print >> self.orig_stdout, string,

        lines = (self.buffer + string).split('\n')
        self.buffer = lines.pop()

        for line in lines:
            for pos in xrange(0, len(line), self.symbols[0]):
                self.output.append(line[pos:pos+self.symbols[0]])

        if self.buffer:
            cut = len(self.buffer)/self.symbols[0] * self.symbols[0]
            for pos in xrange(0, cut, self.symbols[0]):
                self.output.append(self.buffer[pos:pos+self.symbols[0]])

            self.buffer = self.buffer[cut:]

        self.doout()

    def do_in(self, input, edit=True):
        buffer = "%s %s" % (self.prompt, input)
        if (len(buffer)/self.symbols[0] != self.innoff):
            self.innoff = len(buffer)/self.symbols[0]
            self.doout()

        self.ilines = []
        self.ifresh = True
        for pos in xrange(0, len(buffer), self.symbols[0]):
            self.ilines.append(buffer[pos:pos+self.symbols[0]])

        # copy on write
        if edit and self.histpos < self.histcut:
            self.histpos = len(self.history)
            self.history.append(input)
        else:
            self.history[self.histpos] = input

    def clear(self):
        self.buffer = ""
        self.prompt = ">>>"
        self.output = []
        self.innoff = 0
        self.blanks = 0
        self.indent = 0
        self.filled = False

        self.write("~ nayadra shell ~ %s ~\n" % VERSION)
        self.write("~ versum engine ~ %s ~\n" % VENGINE)
        self.do_in(self.history[self.histpos])
        self.cmove(self.curpos)

    def enter(self, key, symbol):
        if key == pygame.K_F5:
            self.clear()
        elif key == pygame.K_TAB:
            next = 4 - (self.curpos % 4)
            self.do_in(self.history[self.histpos][:self.curpos] + (' ' * next) + self.history[self.histpos][self.curpos:])
            self.cmove(self.curpos + next)
        elif key == pygame.K_DELETE:
            if self.curpos < len(self.history[self.histpos]):
                self.do_in(self.history[self.histpos][:self.curpos] + self.history[self.histpos][self.curpos+1:])
        elif key == pygame.K_BACKSPACE:
            if self.curpos > 0 and self.history[self.histpos][:self.curpos] == ' ' * self.curpos:
                back = self.curpos % 4 and self.curpos % 4 or 4
                self.do_in(self.history[self.histpos][:self.curpos - back] + self.history[self.histpos][self.curpos:])
                self.cmove(self.curpos - back)
            elif self.curpos > 0:
                self.do_in(self.history[self.histpos][:self.curpos-1] + self.history[self.histpos][self.curpos:])
                self.cmove(self.curpos - 1)
        elif key == pygame.K_UP:
            self.histpos = (self.histpos - 1) % len(self.history)
            self.do_in(self.history[self.histpos], False)
            self.cmove(len(self.history[self.histpos]))
        elif key == pygame.K_DOWN:
            self.histpos = (self.histpos + 1) % len(self.history)
            self.do_in(self.history[self.histpos], False)
            self.cmove(len(self.history[self.histpos]))
        elif key == pygame.K_LEFT:
            if self.curpos > 0: self.cmove(self.curpos - 1)
        elif key == pygame.K_RIGHT:
            if self.curpos < len(self.history[self.histpos]): self.cmove(self.curpos + 1)
        elif key == pygame.K_HOME:
            self.cmove(0)
        elif key == pygame.K_END:
            self.cmove(len(self.history[self.histpos]))
        elif symbol and symbol in u'\r\n':
            if not self.history[self.histpos]:
                if self.prompt == ">>>": self.blanks += 1
            else:
                self.blanks = 0

            if self.blanks <= 1 :
                print "%s %s" % (self.prompt, self.history[self.histpos])
            else:
                self.onoff(state=_UICONS_NONE)
                self.blanks = 0

            self.prompt = self.interp.push(self.history[self.histpos]) and "..." or ">>>"

            indent = len(self.history[self.histpos]) - len(self.history[self.histpos].strip())
            if indent < len(self.history[self.histpos]): self.filled = True
            elif indent != self.indent: self.filled = False
            if indent and self.filled and indent == len(self.history[self.histpos]): indent -= 4

            if (self.history[self.histpos] and (not self.histcut or self.history[self.histpos] != self.history[self.histcut-1])):
                self.history.insert(self.histcut, self.history[self.histpos])
                self.histcut += 1

            if self.histcut:
                self.history[self.histcut:] = []
                self.histcut = len(self.history)
            else:
                self.history[self.histcut+1:] = []
            self.histpos = len(self.history) - 1

            self.do_in(' ' * indent)
            self.cmove(len(self.history[self.histpos]))
            self.indent = indent
        elif symbol:
            self.do_in(self.history[self.histpos][:self.curpos] + symbol + self.history[self.histpos][self.curpos:])
            self.cmove(self.curpos + 1)

_UITIME_INGAME = 0
_UITIME_RUNFOR = 1
_UITIME_GLOBAL = 2
_UITIME_NTOTAL = 3

class Status(object):
    def __init__(self, root, runfor):
        self.time = runfor and _UITIME_RUNFOR or _UITIME_INGAME
        self.mark = True

        self.root = root
        self.font = root.font

        self.colors = (pygame.Color(0x00, 0x20, 0x40, 0x80), pygame.Color(0x00, 0x80, 0xFF, 0xC0))
        self.sbound = (self.font.rect()[0] * _UI_SYMBOLS + 2 * BORDERX, self.font.rect()[1] + 2 * BORDERY)

        self.canvas = graphic.UIElement(drawing.Widget(self.sbound, colors=self.colors))
        self.sttext = graphic.UIElement(self.font.text(_UI_SYMBOLS))

        strect = self.canvas.rect()
        uirect = self.font.size(' ' * _UI_SYMBOLS)

        self.root.insert('status', self.canvas, (self.root.rect()[0] - self.canvas.rect()[0]) / 2, self.root.rect()[1] - self.canvas.rect()[1])
        self.canvas.insert('sttext', self.sttext, strect[0] - uirect[0] - BORDERX, strect[1] - uirect[1] - BORDERY + 2)

        self.runfor = runfor

        self.events = {}
        self.events[pygame.K_q] = self.swmark
        self.events[pygame.K_w] = self.swtime

    def _format(self, millis):
        return '%02i:%02i:%02i' % (millis / (60 * 60 * 1000), (millis / (60 * 1000)) % 60, (millis / 1000) % 60)

    def _ingame(self):
        ingame = pygame.time.get_ticks()
        return self._format(ingame)

    def _global(self):
        return time.strftime('%H:%M:%S', time.localtime())

    def _runfor(self):
        elapse = self.runfor and self.runfor * 1000 - pygame.time.get_ticks() or 0
        return (elapse <= 0) and '--:--:--' or self._format(elapse)

    def swtime(self):
        self.time = (self.time + 1) % _UITIME_NTOTAL

    def swmark(self):
        self.mark = not self.mark

    def clocks(self):
        return [ self._ingame, self._runfor, self._global ][self.time]()

    def update(self, uitext):
        self.font.render(self.sttext.globj, uitext.center(_UI_SYMBOLS))

