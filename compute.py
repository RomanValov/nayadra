import pyopencl as cl
import pyopencl.cltypes as cltypes
import struct
import array
import numpy
import sys
import os.path
import random

from os import urandom

import pygame
import time

import present

ENGINE = 'birinchi .surround'

def get_gl_sharing_context_properties():
    ctx_props = cl.context_properties

    from OpenGL import platform as gl_platform

    props = []

    if sys.platform == "linux2":
        from OpenGL import GLX

        props.append((ctx_props.GL_CONTEXT_KHR, gl_platform.GetCurrentContext()))
        props.append((ctx_props.GLX_DISPLAY_KHR, GLX.glXGetCurrentDisplay()))
    elif sys.platform == "win32":
        from OpenGL import WGL

        props.append((ctx_props.GL_CONTEXT_KHR, gl_platform.GetCurrentContext()))
        props.append((ctx_props.WGL_HDC_KHR, WGL.wglGetCurrentDC()))
    elif sys.platform == "darwin":
        props.append((ctx_props.CONTEXT_PROPERTY_USE_CGL_SHAREGROUP_APPLE, cl.get_apple_cgl_share_group()))
    else:
        raise NotImplementedError("platform '%s' not yet supported" % sys.platform)

    return props

def create_gl_context():
    platform = cl.get_platforms()[0]

    if sys.platform == "darwin":
        ctx = cl.Context(properties=get_gl_sharing_context_properties(), devices=[])
    else:
        try:
            ctx = cl.Context(properties=[(cl.context_properties.PLATFORM, platform)] + get_gl_sharing_context_properties())
        except:
            ctx = cl.Context(properties=[(cl.context_properties.PLATFORM, platform)] + get_gl_sharing_context_properties(), devices=[platform.get_devices()[0]])

    return ctx

class Recipe(object):
    def __init__(self, ntypes, nclass):
        self.ntypes = ntypes
        self.nclass = nclass
        self.ruleid = 0
        self.buffer = self.dump(0x00, 0, [], {}) * self.ntypes * self.nclass
        self.make_conway()

    def name(self):
        return ENGINE

    def load(self, filename):
        with open(filename, 'r+b') as f:
            self.buffer = f.read(len(self.buffer))

    def save(self, filename):
        with open(filename, 'w+b') as f:
            f.write(self.buffer)

    def dump(self, rarity, forced, around, effect):
        use_forced = forced & 0x000F
        use_rarity = rarity & 0x00FF
        use_around = 0
        for bit in around: use_around |= ((1 << bit) & 0xFFFF)

        use_effect = [ (effect.get(n, 0) & 0x000F) for n in xrange(12) ]

        return struct.pack('HBB', use_around, use_rarity, use_forced) + array.array('B', use_effect).tostring()

    def data(self):
        return self.buffer

    def draw(self, recipe):
        use_around, use_rarity, use_forced = struct.unpack('HBB', recipe[:4])
        use_effect = array.array('B', recipe[4:])

        rarity, forced = use_rarity & 0xFF, use_forced & 0x0F

        bitidx, around = 0, []
        while (1 << bitidx) <= use_around:
            if (~(1 << bitidx) & use_around) != use_around: around += [ bitidx ]
            bitidx += 1

        effect = {}
        for i, e in enumerate(use_effect):
            if e & 0x0F: effect[i] = e & 0x0F

        return rarity, forced, around, effect

    def make_conway(self):
        recipe = [(0x00, 0, [], {})] * self.ntypes * self.nclass
        recipe[0x00] = (0x00, 1, [1,6], {3:1})
        recipe[0x01] = (0x00, 0, [1,6], {2:1, 3:1})

        for n in xrange(0x02, self.ntypes):
            e = [ 0, 1, 6, 6, 6 ][ n % 5 ]
            recipe[n] = (0x00, 0, [], {0:e, 1:e, 2:e, 3:e, 4:e, 5:e, 6:e, 7:e, 8:e})

        recipe[0x06] = (0x0F, 0, [1], {0:6, 1:0, 2:0, 3:0, 4:0, 5:0, 6:0, 7:0, 8:0})

        for n in xrange(self.ntypes * 1, self.ntypes * 2):
            recipe[n] = (0x00, 0, [], {0:1, 1:1, 2:1, 3:1, 4:1, 5:1, 6:1, 7:1, 8:1})

        for n in xrange(self.ntypes * 2, self.ntypes * 3):
            recipe[n] = (0x00, 0, [], {0:6, 1:6, 2:6, 3:6, 4:6, 5:6, 6:6, 7:6, 8:6})

        self.buffer = ''.join([ self.dump(*r) for r in recipe ])

    def make_random(self):
        self.ruleid += 1
        recipe = [(0x00, 0, [], {})] * self.ntypes * self.nclass
        llimit = random.randint(0x00, 0x0C)
        nrange = random.randint(1, max(1, 0x0C - llimit))
        nuance = range(llimit, llimit + nrange)

        for n in xrange(self.ntypes * self.nclass):
            recipe[n] = self.draw(urandom(16))
            posite = nuance[recipe[n][1] % len(nuance)]
            negate = 0
            rarity = (recipe[n][0] & 0x00F0) and (recipe[n][0] & 0x000F) or 0

            for k in recipe[n][3].keys():
                potent = recipe[n][3][k]
                recipe[n][3][k] = [ posite, negate, n ][potent % 3]

            recipe[n] = rarity, 0, recipe[n][2], recipe[n][3]

        recipe[0][3][0] = 0

        try: recipe[0][2].remove(0)
        except: pass

        self.buffer = ''.join([ self.dump(*r) for r in recipe ])

_ENGINE_RESET = 1
_ENGINE_PAUSE = 2
_ENGINE_OSHOT = 3
_ENGINE_DRAWS = 4
_ENGINE_MOVED = 5
_ENGINE_TOTAL = 10

class ComputeUnit:
    def __init__(self, (xtsz, ytsz), datapath, shared, isgl=True):
        self.ctx = isgl and create_gl_context() or create_some_context()

        self.q = cl.CommandQueue(self.ctx)

        mf = cl.mem_flags

        self.buffer = [ None, None ]
        self.buffer[False] = cl.Buffer(self.ctx, mf.READ_WRITE, size=(xtsz * ytsz * 4))
        self.buffer[True] =  cl.Buffer(self.ctx, mf.READ_WRITE, size=(xtsz * ytsz * 4))
        self.states = cl.Buffer(self.ctx, mf.READ_WRITE, size=(xtsz * ytsz * 4))
        self.iteration = False

        self.chroma = present.Chroma(nitems=0x100)
        self.scheme = cl.Buffer(self.ctx, mf.READ_ONLY, size=self.chroma.create(0, 0x10))

        self.recipe = Recipe(0x10, 0x04)
        self.script = cl.Buffer(self.ctx, mf.READ_ONLY, size=len(self.recipe.data()))
        cl.enqueue_write_buffer(self.q, self.script, self.recipe.data()).wait()

        for n in xrange(0x10):
            self.chroma.switch(0, n).change(0, design='gradient', indice=[2*n, 2*n+1])

        if isgl:
            self.output = cl.GLBuffer(self.ctx, mf.WRITE_ONLY, int(shared))
        else:
            raise NotImplemented()

        self.ttrace = numpy.zeros((1,), dtype=cltypes.uint) #array.array('I', [0x00000000])
        self.tsaved = numpy.zeros((1,), dtype=cltypes.uint) #array.array('I', [0x00000000])
        self.btrace = cl.Buffer(self.ctx, mf.WRITE_ONLY, size=4)

        self.smooth = 0
        self.sorder = 0
        self.sparse = 0

        self.cvars = [ False for x in xrange(_ENGINE_TOTAL) ]

        self.xtsz = xtsz
        self.ytsz = ytsz
        self.genr = 0

        self.vary = 1
        self.vmax = 4
        self.blnk = False

        self.code = ''
        self.data = datapath
        self.rindex = 0

        self.state = {}
        self.pattern('surround.c')

        self.enqueue(self.program.seedinit, self.buffer[self.iteration], self.states, urandom(4))

    def enqueue(self, func, *args):
        func(self.q, (self.xtsz, self.ytsz), None, *args)

    def pattern(self, patname):
        source = ''.join(open(patname))
        self.program = cl.Program(self.ctx, source).build()

    def shifted(self):
        self.cvars[_ENGINE_MOVED] = not self.cvars[_ENGINE_MOVED]

    def command(self, key):
        if not key: pass

        # marker
        elif key == pygame.K_BACKQUOTE:
            self.cvars[_ENGINE_DRAWS] = not self.cvars[_ENGINE_DRAWS]
        elif key == pygame.K_1 or key == pygame.K_2 or key == pygame.K_3:
            self.vary = key - pygame.K_0
        elif key == pygame.K_BACKSPACE:
            self.cvars[_ENGINE_RESET] = True

        elif key == pygame.K_LEFTBRACKET:
            if self.sparse > 0x00: self.sparse -= 0x11
        elif key == pygame.K_RIGHTBRACKET:
            if self.sparse < 0xFF: self.sparse += 0x11

        elif key == pygame.K_MINUS:
            self.vary = (self.vary - 1) % self.vmax
        elif key == pygame.K_EQUALS:
            self.vary = (self.vary + 1) % self.vmax

        elif key == pygame.K_SEMICOLON:
            _files = os.listdir(self.data)
            if _files:
                self.rindex = (self.rindex + 1) % len(_files)
                self.recipe.load(os.path.join(self.data, _files[self.rindex]))
                cl.enqueue_write_buffer(self.q, self.script, self.recipe.data()).wait()

        elif key == pygame.K_QUOTE:
            _files = os.listdir(self.data)
            if _files:
                self.rindex = (self.rindex - 1) % len(_files)
                self.recipe.load(os.path.join(self.data, rfiles[self.rindex]))
                cl.enqueue_write_buffer(self.q, self.script, self.recipe.data()).wait()

        elif key == pygame.K_COMMA:
            self.vary = (self.vary - 1) % self.vmax

        elif key == pygame.K_PERIOD:
            self.vary = (self.vary + 1) % self.vmax

        elif key == pygame.K_TAB:
            self.cvars[_ENGINE_OSHOT] = True
        elif key == pygame.K_SCROLLOCK:
            self.cvars[_ENGINE_PAUSE] = not self.cvars[_ENGINE_PAUSE]

        elif key == pygame.K_SPACE:
            self.recipe.make_random()
            cl.enqueue_write_buffer(self.q, self.script, self.recipe.data()).wait()
            #self.cvars[_ENGINE_RESET] = True
            self.cvars[_ENGINE_PAUSE] = False

        elif key == pygame.K_QUESTION:
            self.blnk = not self.blnk

        elif key == pygame.K_BACKSPACE:
            self.recipe.make_conway()
            cl.enqueue_write_buffer(self.q, self.script, self.recipe.data()).wait()
            self.cvars[_ENGINE_RESET] = True
            self.cvars[_ENGINE_PAUSE] = False

        elif key == pygame.K_SYSREQ:
            self.recipe.save(os.path.join(self.data, 'surround.%08X.bin' % int(time.time())))
            cl.enqueue_write_buffer(self.q, self.script, self.recipe.data()).wait()
            self.cvars[_ENGINE_PAUSE] = False

        elif key == pygame.K_KP_PLUS:
            if self.sorder < 7:
                self.sorder += 1
                self.smooth <<= 1

        elif key == pygame.K_KP_MINUS:
            if self.sorder > 0:
                self.sorder -= 1
                self.smooth >>= 1

    def vengine(self):
        return self.recipe.name()

    def inspect(self):
        if self.cvars[_ENGINE_RESET]: self.cvars[_ENGINE_RESET] = False
        elif not self.cvars[_ENGINE_PAUSE] or self.cvars[_ENGINE_OSHOT]:
            if self.cvars[_ENGINE_OSHOT]:
                self.cvars[_ENGINE_OSHOT] = False
                self.cvars[_ENGINE_PAUSE] = True

        if self.cvars[_ENGINE_MOVED]:
            self.cvars[_ENGINE_MOVED] = False

        self.state.update(trace=self.tsaved[0],ngenr=self.genr,dense=self.sparse)

        return self.state

    def preiter(self):
        self.state.update(
                          draws=self.cvars[_ENGINE_DRAWS],
                          moved=self.cvars[_ENGINE_MOVED],
                          marks=self.vary,
                          pause=self.cvars[_ENGINE_PAUSE],
                         )

    def iterate(self, tx, ty, radius):
        cl.enqueue_acquire_gl_objects(self.q, [ self.output ]).wait()

        # impact params
        step = [ 0x00, 0xFF ][not self.cvars[_ENGINE_PAUSE] or self.cvars[_ENGINE_OSHOT]]

        # update colour
        chlist = step and self.chroma.smooth() or []
        for bufkey, nindex, offset in chlist:
            target = self.scheme
            chroma = self.chroma.update(bufkey, nindex)
            binary = array.array('B', chroma).tostring()

            cl.enqueue_write_buffer(self.q, target, binary, offset).wait()

        # invoke action
        if self.cvars[_ENGINE_RESET]:
            self.enqueue(self.program.seedinit, self.buffer[self.iteration], self.states, urandom(4))

        # invoke design
        if step:
            if not (self.smooth % (1 << self.sorder)):
                impact = struct.pack('BBBBII', step, self.vary, radius * self.cvars[_ENGINE_DRAWS], self.sparse, tx, ty)
                self.enqueue(self.program.niterate, self.buffer[self.iteration], self.buffer[not self.iteration], self.states, self.script, impact)
                self.iteration = not self.iteration
                self.genr += 1

            factor = struct.pack('BBBB', self.smooth, self.sorder, 0, 0)
            self.enqueue(self.program.colorize, self.buffer[not self.iteration], self.buffer[self.iteration], self.output, self.scheme, factor)
            self.smooth = (self.smooth + 1) % (1 << self.sorder)

        # update ttrace
        cl.enqueue_read_buffer(self.q, self.output, self.ttrace, (int(tx) + (int(ty) * self.xtsz)) * 4).wait()
        if self.tsaved != self.ttrace: self.tsaved[:] = self.ttrace[:]

        cl.enqueue_release_gl_objects(self.q, [ self.output ]).wait()

        return self.iteration
