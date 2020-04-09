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

def makepath(path, create=False):
    if not os.path.isabs(path):
        root = os.path.abspath(os.path.dirname(sys.argv[0]))
        path = os.path.join(root, path)

    if create and not os.path.exists(path): os.mkdir(path)

    return path

handled = {
    (pygame.KEYDOWN, pygame.K_DELETE): 'shrink',
    (pygame.KEYDOWN, pygame.K_INSERT): 'expand',
    (pygame.KEYDOWN, pygame.K_HOME): 'turn_f',
    (pygame.KEYDOWN, pygame.K_END): 'turn_b',
    (pygame.KEYDOWN, pygame.K_PAGEDOWN): 'zoom_o',
    (pygame.KEYDOWN, pygame.K_PAGEUP): 'zoom_i',
    (pygame.KEYDOWN, pygame.K_LEFT): 'move_l',
    (pygame.KEYDOWN, pygame.K_RIGHT): 'move_r',
    (pygame.KEYDOWN, pygame.K_UP): 'move_u',
    (pygame.KEYDOWN, pygame.K_DOWN): 'move_d',

    (pygame.KEYDOWN, pygame.K_a): '_round',
    (pygame.KEYDOWN, pygame.K_d): '_clamp',

    (pygame.KEYDOWN, pygame.K_v): '_vsync',
    (pygame.KEYDOWN, pygame.K_c): 'center',
    (pygame.KEYDOWN, pygame.K_x): 'noturn',
    (pygame.KEYDOWN, pygame.K_z): 'nozoom',

    (pygame.KEYUP, pygame.K_BACKQUOTE): 'marker',
    (pygame.KEYUP, pygame.K_1): 'mark_1',
    (pygame.KEYUP, pygame.K_2): 'mark_2',
    (pygame.KEYUP, pygame.K_3): 'mark_3',
    (pygame.KEYUP, pygame.K_r): 'reload',
    (pygame.KEYUP, pygame.K_LEFTBRACKET): 'fill_l',
    (pygame.KEYUP, pygame.K_RIGHTBRACKET): 'fill_m',

    #(pygame.KEYUP, pygame.K_SEMICOLON): None,
    #(pygame.KEYUP, pygame.K_QUOTE): None,

    (pygame.KEYUP, pygame.K_COMMA): 'pick_n',
    (pygame.KEYUP, pygame.K_PERIOD): 'pick_p',

    (pygame.KEYUP, pygame.K_SPACE): 'stepby',
    (pygame.KEYUP, pygame.K_PAUSE): 'switch',

    (pygame.KEYUP, pygame.K_TAB): 'random',
    (pygame.KEYUP, pygame.K_BACKSPACE): 'conway',

    (pygame.KEYUP, pygame.K_SYSREQ): 'backup',
    (pygame.KEYUP, pygame.K_KP_MINUS): 'slower',
    (pygame.KEYUP, pygame.K_KP_PLUS): 'faster',

    (pygame.KEYUP, pygame.K_q): 'swmark',
    (pygame.KEYUP, pygame.K_w): 'swtime',

    (pygame.MOUSEBUTTONDOWN, 1, 0): 'marker',
    (pygame.MOUSEBUTTONUP, 1, 0): 'marker',

    (pygame.MOUSEBUTTONUP, 4, 0): 'expand',
    (pygame.MOUSEBUTTONUP, 5, 0): 'shrink',

    (pygame.MOUSEBUTTONUP, 4, pygame.KMOD_LCTRL): 'zoom_i',
    (pygame.MOUSEBUTTONUP, 4, pygame.KMOD_RCTRL): 'zoom_i',

    (pygame.MOUSEBUTTONUP, 4, pygame.KMOD_LSHIFT): 'fill_m',
    (pygame.MOUSEBUTTONUP, 4, pygame.KMOD_RSHIFT): 'fill_m',

    (pygame.MOUSEBUTTONUP, 5, pygame.KMOD_LCTRL): 'zoom_o',
    (pygame.MOUSEBUTTONUP, 5, pygame.KMOD_RCTRL): 'zoom_o',

    (pygame.MOUSEBUTTONUP, 5, pygame.KMOD_LSHIFT): 'fill_l',
    (pygame.MOUSEBUTTONUP, 5, pygame.KMOD_RSHIFT): 'fill_l',
}

def main():
    # initui
    pygame.init()

    methods = {}

    screen = graphic.UIScreen((config.XLEN, config.YLEN))

    board = graphic.UIBoard(screen, (config.XTSZ, config.YTSZ))
    board.zoomto(config.ZOOMTO)
    board.moveto(config.MOVETO)

    cursor = graphic.UICursor(board, config.CURSOR)

    engine = control.Control((config.XTSZ, config.YTSZ), makepath(config.DATA, True))

    methods.update(board.events)
    methods.update(cursor.events)
    methods.update(engine.handled())

    status = widgets.Status(screen, config.RUNFOR)
    console = widgets.Console(screen, engine.banner, **methods)

    methods.update(status.events)

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

    wx, wy = 0.0, 0.0

    while running:
        for event in pygame.event.get():
            mx, my = pygame.mouse.get_pos()
            dx, dy = (wx - mx, wy - my)
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
            elif event.type == pygame.KEYUP and (event.type, event.key) in handled:
                method = handled[event.type, event.key]
                apply(methods[method])
            elif event.type == pygame.KEYDOWN and (event.type, event.key) in handled:
                method = handled[event.type, event.key]
                apply(methods[method])

            elif event.type == pygame.MOUSEBUTTONUP and (event.type, event.button, keymod) in handled:
                method = handled[event.type, event.button, keymod]
                apply(methods[method])
            elif event.type == pygame.MOUSEBUTTONDOWN and (event.type, event.button, keymod) in handled:
                method = handled[event.type, event.button, keymod]
                apply(methods[method])

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
                    apply(methods['rotate'], ((wx, wy), (mx, my), False))
                elif (when_middle):
                    apply(methods['rotate'], ((wx, wy), (mx, my), True))
                elif (when_right):
                    apply(methods['moveon'], (dx, dy, True))
                wx, wy = mx, my
            elif event.type == pygame.MOUSEBUTTONUP:
                if with_middle:
                    if when_right:
                        apply(methods['center'], ((mx, my), +1))

        # engine
        engine.impulse(board.totexcoords((mx, my)), cursor.radius)
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
