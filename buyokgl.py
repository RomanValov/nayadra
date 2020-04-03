import sys
sys.path += ['.']

from ctypes import util
try:
    from OpenGL.platform import win32
except AttributeError:
    pass

import pygame
import struct
import array
import sys
import math

#import logging
#logging.basicConfig()

import OpenGL
OpenGL.ERROR_CHECKING = False
OpenGL.ERROR_LOGGING = False
OpenGL.ERROR_ON_COPY = False
OpenGL.FULL_LOGGING = False

from OpenGL.GL import *
from OpenGL.extensions import alternate
from OpenGL.GL.ARB.vertex_buffer_object import *

def shift(point=None):
    glMatrixMode(GL_MODELVIEW)
    if point:
        glPushMatrix()
        glTranslatef(point[0], point[1], 0.0)
    else:
        glPopMatrix()

def vsync(value=None):
    if sys.platform == 'win32':
        import OpenGL.platform as gl_platform
        import ctypes

        get_vsync = gl_platform.createBaseFunction('wglGetSwapIntervalEXT', platform.GL, ctypes.c_int, [], '', [], 'WGL_EXT_swap_control')
        set_vsync = gl_platform.createBaseFunction('wglSwapIntervalEXT', platform.GL, ctypes.c_long, [ctypes.c_int], '', ['interval'], 'WGL_EXT_swap_control')

        if value is None:
            value = not get_vsync()
        value = ctypes.c_int(value)

        set_vsync(value)
    elif sys.platform == 'linux2':
        import OpenGL.platform as gl_platform
        import ctypes

        get_vsync = gl_platform.createBaseFunction('glXGetSwapIntervalMESA', platform.GL, ctypes.c_int, [], '', [], 'GLX_MESA_swap_control')
        set_vsync = gl_platform.createBaseFunction('glXSwapIntervalMESA', platform.GL, ctypes.c_int, [ctypes.c_int], '', ['interval'], 'GLX_MESA_swap_control')

        if value is None:
            value = not get_vsync()
        value = ctypes.c_int(value)

        set_vsync(value)
    else:
        raise NotImplementedError()

glGenBuffers = alternate(glGenBuffers, glGenBuffersARB)
glBindBuffer = alternate(glBindBuffer, glBindBufferARB)
glBufferData = alternate(glBufferData, glBufferDataARB)
glBufferSubData = alternate(glBufferSubData, glBufferSubDataARB)
glDeleteBuffers = alternate(glDeleteBuffers, glDeleteBuffersARB)

class Buffer:
    def __init__(self, type, size, usage):
        self.bufs = glGenBuffers(1)
        self.size = size
        self.type = type

        glBindBuffer(self.type, self.bufs)
        glBufferData(self.type, self.size, None, usage)
        glBindBuffer(self.type, 0)

    def __del__(self):
        glDeleteBuffers(1, [self.bufs])

    def bind(self, func=None):
        glBindBuffer(self.type, self.bufs)
        if func: func()

    def data(self, pos, data):
        glBindBuffer(self.type, self.bufs)
        glBufferSubData(self.type, pos, len(data), data)

def array_buffer(size): return Buffer(GL_ARRAY_BUFFER, size, usage=GL_DYNAMIC_DRAW)
def pixel_buffer(size): return Buffer(GL_PIXEL_UNPACK_BUFFER, size, usage=GL_STREAM_COPY)

class DrawState(object):
    tcoord_vbo = None
    tcoord_pos = 0
    vertex_vbo = None
    vertex_pos = 0
    on_texture = 0
    used_color = None
    used_width = None
    used_blend = None
    inited = False

    def coords(self, head=None, tail=None, rect=None):
        x1, y1 = head and head or (0.0, 0.0)
        dx, dy = rect and rect or (0.0, 0.0)
        x2, y2 = tail and tail or (x1 + dx, y1 + dy)

        return [ x1, y1, x2, y1, x2, y2, x1, y2 ]

    def vector(self, r, phi):
        return (r * math.cos(phi), r * math.sin(phi))

    def stream(self, farray):
        return farray and array.array('f', farray).tostring() or ''

    def __init__(self):
        if not DrawState.tcoord_vbo:
            DrawState.tcoord_vbo = array_buffer(1024 * 512 * 4)
            DrawState.tcoord_pos = 0
            DrawState.tcoord_vbo.bind(lambda: glTexCoordPointer(2, GL_FLOAT, 0, None))
        if not DrawState.vertex_vbo:
            DrawState.vertex_vbo = array_buffer(1024 * 1024 * 4)
            DrawState.vertex_pos = DrawState.tcoord_vbo.size
            DrawState.vertex_vbo.bind(lambda: glVertexPointer(2, GL_FLOAT, 0, None))

        if not DrawState.inited and DrawState.tcoord_vbo and DrawState.vertex_vbo:
            coords = self.coords()
            if self.create(len(coords) * 4, True):
                raise Exception("unexpected offset of zero buffer")
            self.redata(0, vertex=coords, tcoord=coords)
            DrawState.inited = True

    def create_vertex(self, size):
        if DrawState.vertex_pos + size <= DrawState.vertex_vbo.size:
            ret = DrawState.vertex_pos
            DrawState.vertex_pos += size
            return ret
        else:
            raise Exception("vertex buffer overflow")

    def create_tcoord(self, size):
        if DrawState.tcoord_pos + size <= DrawState.tcoord_vbo.size:
            ret = DrawState.tcoord_pos
            DrawState.tcoord_pos += size
            return ret
        else:
            raise Exception("tcoord buffer overflow")

    def create(self, size, istex):
        return [ self.create_vertex, self.create_tcoord ][istex](size)

    def delete(self, pos):
        pass

    def redata(self, pos, vertex, tcoord):
        if pos < self.tcoord_vbo.size and tcoord:
            self.tcoord_vbo.data(pos, self.stream(tcoord))
        if pos < self.vertex_vbo.size and vertex:
            self.vertex_vbo.data(pos, self.stream(vertex))

    def usetex(self, tex, solid=None):
        if tex == DrawState.on_texture: return

        if tex:
            glEnable(GL_TEXTURE_2D)
            glEnableClientState(GL_TEXTURE_COORD_ARRAY)
            glBindTexture(GL_TEXTURE_2D, tex)
        else:
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisableClientState(GL_TEXTURE_COORD_ARRAY)
            glDisable(GL_TEXTURE_2D)
        DrawState.on_texture = tex

    def primis(self, prim):
        if prim[1] and prim[1] != DrawState.used_width:
            glLineWidth(prim[1])
            DrawState.used_width = prim[1]
        if prim[0] and prim[0] != DrawState.used_color:
            glColor(prim[0].r / 255.0, prim[0].g / 255.0, prim[0].b / 255.0, prim[0].a / 255.0)
            DrawState.used_color = prim[0]
        return bool(prim[0])

class Drawable(DrawState):
    def __init__(self, vertex, tcoord=None, texture=0):
        super(Drawable, self).__init__()

        self.texture = texture

        self.ntotal = 0
        self.curlen = 0
        self.offset = 0

        self.make(vertex=vertex, tcoord=tcoord)
        self.prim()

    def __del__(self):
        if self.offset: self.delete(self.offset)

    def prim(self, primis=None):
        self.primitives = primis and primis or {}

    def make(self, vertex, tcoord=None):
        newlen = max(vertex and len(vertex) / 2 or 0, tcoord and len(tcoord) / 2 or 0)

        if not self.ntotal:
           self.offset = self.create(newlen * 8, bool(tcoord))
           self.ntotal = newlen

        if newlen <= self.ntotal:
            self.redata(self.offset, vertex, tcoord)
            self.curlen = newlen
        else:
            raise Exception("too much vertex or tcoord data")

    def draw(self):
        self.usetex(self.texture)

        for prim in sorted(self.primitives, reverse=True):
            if self.primis(self.primitives[prim]):
                glDrawArrays(prim, self.offset / 8, self.curlen)

class Rectangle(Drawable):
    def __init__(self, rect, vertex=None, tcoord=None, texture=0):
        self.bounds = rect
        if not vertex and rect:
            vertex = self.coords(rect=rect)
        if not tcoord and texture:
            tcoord = self.coords(rect=(1.0, 1.0))
        super(Rectangle, self).__init__(vertex, tcoord=tcoord, texture=texture)

    def rect(self, rect=None):
        if rect:
            self.bounds = rect
            self.make(vertex=self.coords(rect=rect), tcoord=None)
        return self.bounds

class RawTexture(Rectangle):
    def __init__(self, rect, data=None, vertex=None, tcoord=None, texture=0):
        self.texproxy = texture
        if not texture:
            texture = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture)

            w, h = rect
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        super(RawTexture, self).__init__(rect, vertex=vertex, tcoord=tcoord, texture=texture)
        self.prim({ GL_QUADS : (pygame.Color('White'), 0.0) })

    def __del__(self):
        if self.texture and not self.texproxy: glDeleteTextures(self.texture)
        super(RawTexture, self).__del__()

    def update(self, data):
        w, h = self.bounds

        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, w, h, GL_RGBA, GL_UNSIGNED_BYTE, data)

class Texture(RawTexture):
    def __init__(self, rect=None, surf=None):
        if rect:
            self.surface = pygame.Surface((rect[0], rect[1]), pygame.SRCALPHA, 32)
        elif surf:
            self.surface = surf
            rect = (self.surface.get_width(), self.surface.get_height())
        else:
            raise Exception("Failed to create Texture object")

        data = surf and pygame.image.tostring(self.surface, "RGBA") or None
        super(Texture, self).__init__(rect, data=data)

    def copy(self):
        self.update(pygame.image.tostring(self.surface, "RGBA"))

class TexTile(RawTexture):
    def __init__(self, rect, screen_rect):
        super(TexTile, self).__init__(rect, vertex=self.coords(rect=screen_rect))

    def params(self, clamp, round):
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, clamp and GL_CLAMP_TO_BORDER or GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, clamp and GL_CLAMP_TO_BORDER or GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, round and GL_LINEAR or GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)

    def format(self, points):
        coords = []
        for i, p in enumerate(points): coords[2*i:2*i+2] = [ p[0], p[1] ]
        self.make(vertex=None, tcoord=coords)

    def draw(self):
        glDisable(GL_BLEND)
        super(TexTile, self).draw()
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

class Screen(Rectangle):
    def __init__(self, rect):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0.0, rect[0], rect[1], 0.0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)

        super(Screen, self).__init__(rect)

    def draw(self):
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClear(GL_COLOR_BUFFER_BIT)

class Widget(Rectangle):
    def __init__(self, rect, colors=(None, None)):
        super(Widget, self).__init__(rect)
        self.prim({ GL_QUADS : (colors[0], 0.0), GL_LINE_LOOP : (colors[1], 4.0) })

class DrawCursor(Drawable):
    N_SEGMENTS = 60
    def __init__(self):
        self.radius = 0.0
        super(DrawCursor, self).__init__(None)

    def update(self, radius, border):
        if radius != self.radius:
            vertex = []
            for n in xrange(DrawCursor.N_SEGMENTS):
                t = 2.0 * math.pi * n / DrawCursor.N_SEGMENTS
                vertex.extend([math.sin(t) * radius, math.cos(t) * radius])

            self.make(vertex=vertex)
            self.radius = radius

        self.prim({ GL_LINE_LOOP : (border, 2.0) })

    def rect(self):
        return (self.radius * 2, self.radius * 2)

class CrossMark(Drawable):
    def __init__(self, point, radius, angle):
        super(CrossMark, self).__init__(None)
        self.prim({ GL_LINES : (pygame.Color('Red'), 4.0) })
        self.update(point, radius, angle)

    def update(self, point, radius, angle):
        x, y = point
        vector = self.vector(radius, -angle)
        vertex = []
        vertex.extend([ x - vector[0], y - vector[1] ])
        vertex.extend([ x + vector[0], y + vector[1] ])
        vertex.extend([ x + vector[1], y - vector[0] ])
        vertex.extend([ x - vector[1], y + vector[0] ])
        self.make(vertex=vertex)

class Font:
    def __init__(self, font):
        self.font = font
        self.symr = (font.size(' ' * 16)[0] / 16, font.get_linesize())
        self.syms = Texture(rect=(self.symr[0] * 0x80, self.symr[1]))

        for code in xrange(0x80):
            char = (code and chr(code) and code != 0x0D) and chr(code) or ' '
            surf = self.font.render(char, True, pygame.Color(0x40, 0xE0, 0x80, 0xC0))
            self.syms.surface.blit(surf, (self.symr[0] * code, 0.0))

        self.syms.copy()

    def size(self, text):
        return (self.symr[0] * len(text), self.symr[1])

    def text(self, size):
        tcoord = [0.0] * 8 * size
        vertex = [0.0] * 8 * size
        return RawTexture(self.syms.rect(), vertex=vertex, tcoord=tcoord, texture=self.syms.texture)

    def render(self, rtex, text, aa=False, color=None):
        tcoord = []
        vertex = []

        symf = (float(self.symr[0]), float(self.symr[1]))
        texf = (float(self.syms.rect()[0]), float(self.syms.rect()[1]))
        xoff = 0.0
        yoff = 0.0
        for c in text:
            if c in '\r\n':
                xoff = 0
                yoff += symf[1]
            else:
                base = ord(c) * symf[0]
                tcoord.extend(rtex.coords(head=(base / texf[0], 0.0), rect=(symf[0] / texf[0], 1.0)))
                vertex.extend(rtex.coords(head=(xoff, yoff), rect=symf))
                xoff += symf[0]

        rtex.make(tcoord=tcoord, vertex=vertex)

    def rect(self):
        return self.symr
