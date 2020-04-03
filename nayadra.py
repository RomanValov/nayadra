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

def main():
    # initui
    pygame.init()

    screen = graphic.UIScreen((config.XLEN, config.YLEN))
    board = graphic.UIBoard(screen, (config.XTSZ, config.YTSZ))
    board.zoomto(config.ZOOMTO)
    board.moveto(config.MOVETO)

    engine = control.Control((config.XTSZ, config.YTSZ), makepath(config.DATA, True))
    cursor = graphic.UICursor(board, config.CURSOR)

    # shell functions
    zoomon = lambda chzm: board.zoomon(chzm)
    zoomto = lambda zoom: board.zoomto(zoom)
    moveon = lambda dx, dy: board.moveon((dx, dy))
    moveto = lambda dx, dy: board.moveto((dx, dy))
    turnon = lambda turn: board.turnon(turn)
    turnto = lambda turn: board.turnto(turn)
    action = lambda draw=None: engine.handled(pygame.K_1)
    marker = lambda mark=None: engine.handled(pygame.K_2)
    eraser = lambda mark=None: engine.handled(pygame.K_3)
    drop   = lambda: engine.handled(pygame.K_7)

    status = widgets.Status(screen, config.RUNFOR)
    console = widgets.Console(screen, engine.banner, **locals())

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

    handled = dict()

    # graphic keys
    handled[pygame.KEYDOWN, pygame.K_DELETE] = lambda: cursor.resize(-1)
    handled[pygame.KEYDOWN, pygame.K_INSERT] = lambda: cursor.resize(+1)
    handled[pygame.KEYDOWN, pygame.K_HOME] = lambda: board.turnon(-1)
    handled[pygame.KEYDOWN, pygame.K_END] = lambda: board.turnon(+1)
    handled[pygame.KEYDOWN, pygame.K_PAGEDOWN] = lambda: board.zoomon(-1, False)
    handled[pygame.KEYDOWN, pygame.K_PAGEUP] = lambda: board.zoomon(+1, False)
    handled[pygame.KEYDOWN, pygame.K_LEFT] = lambda: board.moveon((-16, 0))
    handled[pygame.KEYDOWN, pygame.K_RIGHT] = lambda: board.moveon((+16, 0))
    handled[pygame.KEYDOWN, pygame.K_UP] = lambda: board.moveon((0, -16))
    handled[pygame.KEYDOWN, pygame.K_DOWN] = lambda: board.moveon((0, +16))

    wx, wy = 0.0, 0.0

    inproc = True
    inzoom = False
    indraw = False
    while running:
        for event in pygame.event.get():
            mx, my = pygame.mouse.get_pos()
            bpress = pygame.mouse.get_pressed()

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
                engine.handled(pygame.K_QUESTION)
                fps = fpsc
                fpsc = 0

                countr += 1
                if config.SWITCH and not countr % config.SWITCH:
                    engine.handled(pygame.K_SPACE)
            elif event.type == pygame.USEREVENT:
                running = False

            # component events
            elif event.type == pygame.KEYUP and board.handled(event.key) == None:
                pass
            elif event.type == pygame.KEYUP and status.handled(event.key) == None:
                pass
            elif event.type == pygame.KEYUP and engine.handled(event.key) == None:
                pass

            elif event.type == pygame.KEYDOWN and (event.type, event.key) in handled:
                apply(handled[event.type, event.key])

            # mouse events
            elif event.type == pygame.MOUSEBUTTONDOWN:
                bevent = event.dict['button'] - 1
                if bevent == 4:
                    if bpress[1] or (bpress[0] and bpress[2]):
                        if inproc: engine.handled(pygame.K_RIGHTBRACKET)
                    elif bpress[2]:
                        board.zoomon(-1)
                    elif bpress[0]:
                        engine.handled(pygame.K_COMMA)
                        indraw = False
                    else:
                        cursor.resize(-1)
                    inproc = False
                elif bevent == 3:
                    if bpress[1] or (bpress[0] and bpress[2]):
                        if inproc: engine.handled(pygame.K_LEFTBRACKET)
                    elif bpress[2]:
                        board.zoomon(+1)
                    elif bpress[0]:
                        engine.handled(pygame.K_PERIOD)
                        indraw = False
                    else:
                        cursor.resize(+1)
                    inproc = False
                elif bevent == 2:
                    board.breaks(nomove=True)
                elif bevent == 1:
                    board.breaks(noturn=True)
                elif bevent == 0:
                    if not bpress[2] and not indraw:
                        engine.handled(pygame.K_BACKQUOTE)
                        indraw = True
            elif event.type == pygame.MOUSEMOTION:
                if pygame.mouse.get_rel() == (0, 0):
                    continue
                elif (bpress[1] and bpress[2]):
                    board.rotate((wx, wy), (mx, my), False)
                    inproc = False
                    inzoom = True
                elif bpress[1] or (bpress[0] and bpress[2]) and not inzoom:
                    board.rotate((wx, wy), (mx, my), True)
                    inproc = False
                elif bpress[2] and not inzoom:
                    board.moveon((wx - mx, wy - my), True)
                wx, wy = mx, my
            elif event.type == pygame.MOUSEBUTTONUP:
                bevent = event.dict['button'] - 1
                if bevent == 1:
                    if bpress[2] and inproc:
                        board.center((mx, my), +1)
                elif bevent == 0:
                    if bpress[2] and not indraw and inproc:
                        engine.handled(pygame.K_BACKSPACE)
                    elif indraw:
                        engine.handled(pygame.K_BACKQUOTE)
                        indraw = False

                if not any(bpress):
                    inproc = True
                    inzoom = False

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
