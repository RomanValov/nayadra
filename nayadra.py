import pygame
import time
import sys
import os.path
import cProfile

import buyoksh
import buyokui
import adapter

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

    screen = buyokui.UIScreen((config.XLEN, config.YLEN))
    board = buyokui.UIBoard(screen, (config.XTSZ, config.YTSZ))
    board.zoomto(config.ZOOMTO)

    engine = adapter.Adapter((config.XTSZ, config.YTSZ), makepath(config.DATA, True))
    cursor = buyokui.UICursor(board, 2)

    # shell functions
    func = {}
    func['zoomon']  = lambda chzm: board.zoomon(chzm)
    func['zoomto']  = lambda zoom: board.zoomto(zoom)
    func['moveon']  = lambda dx, dy: board.moveon((dx, dy))
    func['moveto']  = lambda dx, dy: board.moveto((dx, dy))
    func['turnon']  = lambda turn: board.turnon(turn)
    func['turnto']  = lambda turn: board.turnto(turn)
    func['action']  = lambda draw=None: engine.sendkey(pygame.K_1)
    func['marker']  = lambda mark=None: engine.sendkey(pygame.K_2)
    func['eraser']  = lambda mark=None: engine.sendkey(pygame.K_3)
    func['drop']    = lambda: engine.sendkey(pygame.K_7)

    status = buyoksh.UIStatus(screen, config.RUNFOR)
    console = buyoksh.UIConsole(screen, engine.banner, **func)

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

    HANDLED_KEYS = []
    HANDLED_KEYS += [ pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET, pygame.K_SEMICOLON, pygame.K_QUOTE ]
    HANDLED_KEYS += [ pygame.K_COMMA, pygame.K_PERIOD, pygame.K_BACKSPACE, pygame.K_SYSREQ, pygame.K_SCROLLOCK ]
    HANDLED_KEYS += [ pygame.K_SPACE, pygame.K_TAB, pygame.K_BACKQUOTE, pygame.K_BACKSLASH, pygame.K_EQUALS, pygame.K_MINUS ]
    HANDLED_KEYS += [ pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_KP_MINUS ]
    HANDLED_KEYS += [ pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9, pygame.K_KP_PLUS ]

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
                    console.onoff(state=buyoksh._UICONS_FULL)
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
                engine.sendkey(pygame.K_QUESTION)
                fps = fpsc
                fpsc = 0

                countr += 1
                if config.SWITCH and not countr % config.SWITCH:
                    engine.sendkey(pygame.K_SPACE)
            elif event.type == pygame.USEREVENT:
                running = False

            # component events
            elif event.type == pygame.KEYUP and event.key in board.events.keys():
                board.events[event.key]()
            elif event.type == pygame.KEYUP and event.key in status.events.keys():
                status.events[event.key]()
            elif event.type == pygame.KEYUP and event.key in HANDLED_KEYS:
                engine.sendkey(event.key)

            # repeatable events
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_DELETE:
                cursor.resize(-1)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_INSERT:
                cursor.resize(+1)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_HOME:
                board.turnon(-1)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_END:
                board.turnon(+1)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_PAGEDOWN:
                board.zoomon(-1, False)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_PAGEUP:
                board.zoomon(+1, False)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_LEFT:
                board.moveon((-16, 0))
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RIGHT:
                board.moveon((+16, 0))
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_UP:
                board.moveon((0, -16))
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_DOWN:
                board.moveon((0, +16))

            # mouse events
            elif event.type == pygame.MOUSEBUTTONDOWN:
                bevent = event.dict['button'] - 1
                if bevent == 4:
                    if bpress[1] or (bpress[0] and bpress[2]):
                        if inproc: engine.sendkey(pygame.K_RIGHTBRACKET)
                    elif bpress[2]:
                        board.zoomon(-1)
                    elif bpress[0]:
                        engine.sendkey(pygame.K_DELETE)
                        indraw = False
                    else:
                        cursor.resize(-1)
                    inproc = False
                elif bevent == 3:
                    if bpress[1] or (bpress[0] and bpress[2]):
                        if inproc: engine.sendkey(pygame.K_LEFTBRACKET)
                    elif bpress[2]:
                        board.zoomon(+1)
                    elif bpress[0]:
                        engine.sendkey(pygame.K_INSERT)
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
                        engine.sendkey(pygame.K_BACKQUOTE)
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
                        engine.sendkey(pygame.K_BACKSPACE)
                    elif indraw:
                        engine.sendkey(pygame.K_BACKQUOTE)
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
