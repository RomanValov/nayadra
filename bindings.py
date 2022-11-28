import pygame


hotkey = {
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

    (pygame.MOUSEMOTION, pygame.KMOD_LCTRL): 'moveof',
    (pygame.MOUSEMOTION, pygame.KMOD_RCTRL): 'moveof',

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

