import pygame
import time
import sys
import os.path
import cProfile

import widgets
import graphic
import control

try:
    import config
except:
    import defaults as config

try:
    import hotkey
except:
    import bindings as hotkey

def makepath(path, create=False):
    if not os.path.isabs(path):
        root = os.path.abspath(os.path.dirname(sys.argv[0]))
        path = os.path.join(root, path)

    if create and not os.path.exists(path): os.mkdir(path)

    return path

def domethod(method, *args, **kwargs):
    if isinstance(method, basestring):
        return methods[metod]
    elif callable(method):
        return method(*args, **kwargs)

def main():
    # initui
    pygame.init()

    builtin = {}

    screen = graphic.UIScreen((config.XLEN, config.YLEN))

    board = graphic.UIBoard(screen, (config.XTSZ, config.YTSZ))
    board.zoomto(config.ZOOMTO)
    board.moveto(config.MOVETO)

    cursor = graphic.UICursor(board, config.CURSOR)

    engine = control.Control((config.XTSZ, config.YTSZ), makepath(config.DATA, True))

    status = widgets.Status(screen, config.RUNFOR)

    builtin.update(board.events)
    builtin.update(cursor.events)
    builtin.update(engine.handled())
    builtin.update(status.events)

    builtin.update({'config': config})
    builtin.update({'hotkey': hotkey})

    console = widgets.Console(screen, engine.banner, **builtin)

    # timers
    clock = pygame.time.Clock()
    if config.RUNFOR: pygame.time.set_timer(pygame.USEREVENT, config.RUNFOR * 1000 - pygame.time.get_ticks())
    pygame.time.set_timer(pygame.USEREVENT + 7, 1024 / 64)
    pygame.time.set_timer(pygame.USEREVENT + 4, 250)
    pygame.time.set_timer(pygame.USEREVENT + 2, 500)
    pygame.time.set_timer(pygame.USEREVENT + 1, 1000)

    running = True
    blink = False
    fpsc = fps = 0
    countr = 0

    # component keys
    SKIPPED_KEYS = [ pygame.K_ESCAPE, pygame.K_MENU, pygame.K_RETURN ]

    waspos = 0.0, 0.0

    while running:
        for event in pygame.event.get():
            nowpos = pygame.mouse.get_pos()

            bpress = pygame.mouse.get_pressed()
            bevent = event.dict.get('button', 0) - 1
            keymod = pygame.key.get_mods()

            with_middle = bevent == 1
            with_right = bevent == 2
            with_left = bevent == 0

            with_fore = bevent == 3
            with_back = bevent == 4

            when_middle = bpress[1] or (bpress[0] and bpress[2])
            when_right = bpress[2]
            when_left = bpress[0]

            # console events
            if event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:
                if console.shown:
                    console.onoff(False)
                else:
                    running = False
            elif event.type == pygame.KEYUP and event.key == pygame.K_RETURN:
                if console.shown:
                    console.enter(event.key, '\n')
                else:
                    console.onoff(state=widgets._UICONS_FULL)
            elif event.type == pygame.KEYUP and event.key == pygame.K_MENU:
                console.onoff(True)
            elif event.type == pygame.KEYUP and event.key == pygame.K_F5:
                console.enter(event.key, '')
            elif event.type == pygame.KEYUP and console.shown:
                pass
            elif event.type == pygame.KEYDOWN and console.shown and event.key not in SKIPPED_KEYS:
                console.enter(event.key, event.unicode)

            # timer events
            elif event.type == pygame.USEREVENT + 7:
                board.inerts(bpress[2], bpress[1] or (bpress[2] and bpress[0]))
            elif event.type == pygame.USEREVENT + 4:
                if console.shown: console.blink()
            elif event.type == pygame.USEREVENT + 2:
                blink = not blink
            elif event.type == pygame.USEREVENT + 1:
                fps = fpsc
                fpsc = 0

                countr += 1
                if config.SWITCH and not countr % config.SWITCH:
                    apply(methods['random'])
            elif event.type == pygame.USEREVENT:
                running = False

            # events to methods
            elif event.type == pygame.KEYUP and (event.type, event.key) in hotkey.hotkey:
                method = hotkey.hotkey[event.type, event.key]
                apply(builtin[method])
            elif event.type == pygame.KEYDOWN and (event.type, event.key) in hotkey.hotkey:
                method = hotkey.hotkey[event.type, event.key]
                apply(builtin[method])

            elif event.type == pygame.MOUSEBUTTONUP and (event.type, event.button, keymod) in hotkey.hotkey:
                method = hotkey.hotkey[event.type, event.button, keymod]
                apply(builtin[method])
            elif event.type == pygame.MOUSEBUTTONDOWN and (event.type, event.button, keymod) in hotkey.hotkey:
                method = hotkey.hotkey[event.type, event.button, keymod]
                apply(builtin[method])
            elif event.type == pygame.MOUSEMOTION and (event.type, keymod) in hotkey.hotkey:
                method = hotkey.hotkey[event.type, keymod]
                apply(builtin[method], (waspos, nowpos))
                waspos = nowpos

            # mouse events
            if True:
                pass
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if None:
                    pass
                elif with_right:
                    apply(methods['moveno'])
                elif with_middle:
                    apply(methods['turnno'])
            elif event.type == pygame.MOUSEMOTION:
                if pygame.mouse.get_rel() == (0, 0):
                    continue
                elif (when_middle and when_right):
                    apply(methods['rotate'], (waspos, nowpos, False))
                elif (when_middle):
                    apply(methods['rotate'], (waspos, nowpos, True))
                elif (when_right):
                    apply(methods['moveof'], (waspos, nowpos, True))
                waspos = nowpos
            elif event.type == pygame.MOUSEBUTTONUP:
                if with_middle:
                    if when_right:
                        apply(methods['center'], ((mx, my), +1))

        # engine
        engine.impulse(board.totexcoords(nowpos), cursor.radius)
        # domain
        # moment
        moment = engine.reclaim(config.ROTATE, lambda: board.update(None))

        # status
        uiinfo = []

        ux, uy = board.uicoords(status.mark)
        us, ua = board.uiparams()
        uigenr = (not moment['pause'] or blink) and (" %08X " % moment['ngenr']) or "          "

        uiinfo += [ " %1s %1s " % (moment['draws'] and "D" or "", moment['moved'] and "M" or "") ]
        uiinfo += [ " %1X @%02X " % (moment['marks'], moment['dense']) ]
        uiinfo += [ " %1s %1s " % (board.clamp and "V" or "", board.round and "A" or "") ]
        uiinfo += [" %4ux%4u | x%8.4f <%4u | %s %5u:%5u | R%4u | # %08X | %s " %
                   (config.XTSZ, config.YTSZ, us, ua,
                    status.mark and "CURSOR" or "CENTER", int(ux), int(uy),
                    cursor.radius, moment['trace'], status.clocks())]
        uiinfo += [ uigenr ]
        uiinfo += [ " FPS %4u" % fps ]

        status.update('|'.join(uiinfo))

        # drawing
        board.frame()
        cursor.frame()
        console.frame()
        screen.render()

        # fps
        fpsc += 1

    pygame.quit()

if __name__ == '__main__':
    cProfile.run('main()', 'profile')
