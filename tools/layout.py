"""Screen layout changes for English: constants in the code (column boxes, text x positions).

The game draws its list screens with constants: a frame `0x80081ef0(a0, x, y, w8, ...)`, column
boxes `0x80082250(a0, x8, y8, w8, ...)` (x and width in 8-px cells, relative to the frame) and
text through `0x8007b580(x, y, str, colour)` / `0x8007b614(x, y, fmt, value)` (absolute pixels).
tools/dev/drawcalls.py lists those calls with the address of each constant.

SCREENS: {name: (image tag, [(address, old value, new value), ...])}: the 16-bit immediate of
the instruction at the address (an `addiu` / `ori`) is replaced; the old value is checked.
"""
import os, struct, sys

sys.path.insert(0, os.path.dirname(__file__))
import asm, nameentry, text, vwf

PROG_BASE, PROG_FOFF, OVL_BASE = 0x80010000, 0x800, 0x800EE000

SCREENS = {
    # status bar 0x8002f040: "1560/ 8/ 1  1 kan  0 mon Stamina [bar]" (x of month, day, kan, mon, label)
    'status bar': ('PROG', [
        (0x8002f09c, 0x40, 0x30), (0x8002f0bc, 0x5c, 0x42), (0x8002f10c, 0x78, 0x54),
        (0x8002f134, 0xae, 0x90), (0x8002f0d0, 0xd0, 0xc4),    # "999 mon" ends at 190
    ]),
    # people of a house (samurai home ...) 0x80033380: Name | Met | Gift | Tea | Rank | Faction
    # frame 20 px + 35 cells -> 8 px + 38 cells; columns (cells) 1+10, 11+3, 14+3, 17+3, 20+7, 27+7
    # -> 1+12, 13+3, 16+3, 19+3, 22+9, 31+6
    'house people': ('PROG', [
        (0x8003336c, 20, 8), (0x80033374, 280, 304),              # clear the window
        (0x80033678, 28, 16), (0x80033680, 272, 288),             # clear the rows
        (0x80033ae4, 20, 8), (0x80033aec, 280, 304), (0x80034d0c, 20, 8), (0x80034d14, 280, 304),
        (0x800346c4, 28, 16), (0x800346c8, 264, 288), (0x80034b28, 28, 16), (0x80034b2c, 264, 288),   # cursor bar
        (0x800333a0, 20, 8), (0x800333a8, 35, 38),
        (0x800333d0, 10, 12),
        (0x800333f0, 11, 13), (0x80033418, 14, 16), (0x80033440, 17, 19),
        (0x80033468, 20, 22), (0x80033470, 7, 9), (0x80033490, 27, 31), (0x80033498, 7, 6),
        (0x800334b4, 56, 51), (0x800334cc, 108, 115), (0x800334e4, 132, 140), (0x800334fc, 156, 163),
        (0x80033514, 196, 209), (0x8003352c, 252, 265),
        (0x800336cc, 252, 264),                                   # page n/m
        (0x80033808, 32, 18),
        (0x80033844, 114, 118), (0x8003385c, 138, 142), (0x80033874, 162, 166),
        (0x800338c0, 114, 118), (0x80033904, 138, 142), (0x80033948, 162, 166),
        (0x80033984, 184, 182), (0x800339d0, 184, 182),
        (0x80033a18, 240, 260), (0x80033a38, 240, 260),
    ]),
    # People list (Triangle -> People) header 0x800318a8, rows 0x80031be4, loop 0x80032d4c: frame 12 px /
    # 37 cells -> 8 / 38; Name | Clan | Castle | Men | Rank: cells 1+9, 10+8, 18+8, 26+4, 30+6
    # -> 1+11, 12+6, 18+7, 25+3, 28+9. Clan and castle without suffix (strbuf.SHORT_CALLS; a1 = 0).
    'people list': ('PROG', [
        (0x80031954, 12, 8), (0x8003195c, 296, 304), (0x80031988, 12, 8), (0x80031990, 37, 38),
        (0x80031bfc, 12, 8), (0x80031c04, 296, 304), (0x80032094, 12, 8), (0x8003209c, 296, 304),
        (0x80032d94, 20, 16), (0x80032d98, 280, 288), (0x800331c0, 20, 16), (0x800331c4, 280, 288),   # cursor bar
        (0x800319b8, 9, 11), (0x800319d8, 10, 12), (0x800319e0, 8, 6), (0x80031a08, 8, 7),
        (0x80031a28, 26, 25), (0x80031a30, 4, 3), (0x80031a50, 30, 28), (0x80031a58, 6, 9),
        (0x80031a74, 38, 47), (0x80031a8c, 94, 117), (0x80031aa8, 176, 165), (0x80031ac0, 224, 210),
        (0x80031ad8, 264, 256),
        (0x80031c78, 20, 18),
        (0x80031cb0, 94, 106), (0x80031cd8, 158, 154), (0x80031cf4, 230, 214), (0x80031d0c, 252, 234),
        (0x80031dc0, 94, 106), (0x80031e20, 158, 154), (0x80031e70, 230, 214), (0x80031ea4, 252, 234),
        (0x80031edc, 94, 106), (0x80031f08, 94, 106), (0x80031f28, 94, 106),
        (0x80031f88, 158, 154), (0x80031fa0, 230, 214), (0x80031fb8, 252, 234),
        (0x80031e00, 1, 0), (0x80031f68, 1, 0),                   # castle name without " Castle"
        (0x80032044, 260, 268),                                   # page n/m
    ]),
    # all castles (Records) header 0x80030a20, rows 0x80030bec: frame 68 px / 23 cells -> 44 / 29;
    # Castle | Clan | Province: cells 1+8, 9+8, 17+5 -> 1+12, 13+8, 21+7 (no suffixes)
    'castle list': ('PROG', [
        (0x80030a3c, 68, 44), (0x80030a44, 184, 232), (0x80030a98, 68, 44), (0x80030aa0, 23, 29),
        (0x80030c04, 68, 44), (0x80030c0c, 184, 232), (0x80030ff0, 68, 44), (0x80030ff8, 184, 232),
        (0x80030bac, 76, 52), (0x80030bb0, 168, 216), (0x80031078, 76, 52), (0x8003107c, 168, 216),
        (0x80031444, 76, 52), (0x80031448, 168, 216),
        (0x80030ac8, 8, 12), (0x80030ae8, 9, 13), (0x80030b10, 17, 21), (0x80030b18, 5, 7),
        (0x80030b34, 84, 85), (0x80030b4c, 142, 169), (0x80030b68, 206, 219),
        (0x80030d9c, 78, 54), (0x80030e00, 142, 150), (0x80030e30, 212, 214),
        (0x80030d84, 1, 2),                                       # castle getter flag 2: "-ji" / " Town" kept, no " Castle"
        (0x80030c90, 204, 228),                                   # page n/m ("Info" + its button sprite stay)
    ]),
    # daimyo list 0x800301c8 (Daimyo | Castles) and province list 0x80035744 (Province | Castles):
    # frame 108 px / 13 cells (1+7, 8+4) and 120 px / 10 cells (1+4, 5+4) -> both 100 px / 15 cells (1+8, 9+5)
    'daimyo list': ('PROG', [
        (0x80030264, 108, 100), (0x8003026c, 104, 120), (0x80030298, 108, 100), (0x800302a0, 13, 15),
        (0x800303c4, 108, 100), (0x800303cc, 104, 120), (0x80030574, 108, 100), (0x8003057c, 104, 120),
        (0x80030368, 116, 108), (0x8003036c, 88, 104), (0x80030604, 116, 108), (0x80030608, 88, 104),
        (0x80030954, 116, 108), (0x80030958, 88, 104),
        (0x800302c8, 7, 8), (0x800302e8, 8, 9), (0x800302f0, 4, 5),
        (0x8003030c, 120, 123), (0x80030324, 176, 175),
        (0x800304b8, 120, 110), (0x800304e4, 182, 183), (0x80030508, 120, 110), (0x80030418, 164, 172),
    ]),
    'province list': ('PROG', [
        (0x80035734, 120, 100), (0x8003573c, 80, 120), (0x80035768, 120, 100), (0x80035770, 10, 15),
        (0x80035894, 120, 100), (0x8003589c, 80, 120), (0x800359fc, 120, 100), (0x80035a04, 80, 120),
        (0x80035838, 128, 108), (0x8003583c, 64, 104), (0x80035a84, 128, 108), (0x80035a88, 64, 104),
        (0x80035dd4, 128, 108), (0x80035dd8, 64, 104),
        (0x80035798, 4, 8), (0x800357b8, 5, 9), (0x800357c0, 4, 5),
        (0x800357dc, 132, 119), (0x800357f4, 164, 175),
        (0x8003595c, 132, 110), (0x80035988, 170, 183), (0x800358e8, 152, 172),
    ]),
    # members of a faction (Factions -> portrait) 0x8003ba74: frame 88 px / 18 cells -> 68 / 23;
    # Vassal | Rank: cells 1+10, 11+6 -> 1+12, 13+9
    'faction members': ('PROG', [
        (0x8003ba64, 88, 68), (0x8003ba6c, 144, 184), (0x8003ba98, 88, 68), (0x8003baa0, 18, 23),
        (0x8003be30, 88, 68), (0x8003be38, 144, 184), (0x8003bb94, 96, 76), (0x8003bb9c, 128, 168),
        (0x8003bac8, 10, 12), (0x8003bae8, 11, 13), (0x8003baf0, 6, 9),
        (0x8003bb0c, 106, 108), (0x8003bb28, 188, 196),
        (0x8003bc5c, 100, 78), (0x8003bc90, 176, 174), (0x8003bbe8, 184, 204), (0x8003bdd8, 96, 78),
    ]),
    # castle info panel (boxes 0x80031510, text 0x80037084, close 0x80031774): frame 20 px / 35 cells -> 8 / 38;
    # label boxes (cells) 1+4, 13+4, 23+5 -> 1+7, 14+6, 26+5; values right-aligned before the next box,
    # words ("Unknown", Few / Many: `%6s` -> `%s` in BYTES) left-aligned after the label box.
    # Header: castle name 16, "%s%s" (clan + " Main Castle") 148; portraits 16 / 160; "Surveyed" to 252,66.
    'castle info': ('PROG', [
        (0x8003155c, 20, 8), (0x80031564, 280, 304), (0x80031590, 20, 8), (0x80031598, 35, 38),
        (0x80031808, 20, 8), (0x80031810, 280, 304),
        (0x800315dc, 4, 7), (0x80031604, 13, 14), (0x80031608, 4, 6), (0x80031630, 23, 26),
        (0x8003166c, 5, 7), (0x8003168c, 23, 26),
        (0x800370f8, 32, 18), (0x8003712c, 30, 18), (0x80037160, 128, 122), (0x80037188, 206, 218),
        (0x800371ac, 206, 218),
        (0x8003724c, 28, 16), (0x80037340, 96, 148), (0x800374bc, 224, 252), (0x800374c0, 46, 66),
        (0x80037388, 32, 16), (0x800373ac, 68, 52), (0x800373e0, 70, 54),
        (0x80037438, 144, 160), (0x8003745c, 180, 196), (0x80037490, 182, 198),
        # column 1: unknown / words / numbers
        (0x80037568, 96, 74), (0x800375c8, 96, 74), (0x80037670, 84, 74),
        (0x800376c4, 96, 74), (0x80037718, 96, 74), (0x800377a0, 96, 74), (0x80037828, 96, 74),
        (0x80037a2c, 84, 80), (0x80037a88, 66, 62), (0x80037ab0, 78, 74), (0x80037ae8, 78, 74),
        (0x80037b10, 78, 74),
        # column 2
        (0x80037c64, 176, 170), (0x80037d00, 164, 170),
        (0x80037d84, 176, 170), (0x80037e0c, 176, 170), (0x80037e60, 176, 170), (0x80037eb4, 176, 170),
        (0x80037ee4, 170, 182), (0x80037f1c, 182, 194), (0x80037f3c, 182, 194), (0x80037f64, 182, 194),
        (0x80037fd4, 182, 194), (0x80037f80, 182, 194), (0x80037f98, 182, 194), (0x80037fb0, 182, 194),
        # column 3
        (0x8003802c, 268, 258), (0x800380c8, 256, 258), (0x80038150, 256, 258), (0x800381d8, 256, 258),
        (0x80038260, 256, 258), (0x800382e8, 256, 258), (0x80038370, 256, 258),
        (0x8003839c, 244, 256), (0x800383c0, 244, 256), (0x80038450, 244, 256),
        (0x800383e4, 262, 274), (0x80038408, 262, 274), (0x8003842c, 280, 292),
    ]),
    # the small variant of the panel (place type 2: one column of 4 rows): frame 104 px / 14 cells -> 88 / 18,
    # label box 1+4 -> 1+7, numbers + 16 px
    'castle info (small)': ('PROG', [
        (0x800316a8, 104, 88), (0x800316b0, 112, 144), (0x800316dc, 104, 88), (0x800316e4, 14, 18),
        (0x80031828, 104, 88), (0x80031830, 112, 144), (0x80031724, 4, 7),
        (0x800371f0, 116, 98), (0x800374f8, 116, 98),
        (0x8003758c, 184, 160), (0x800378b8, 172, 160),
        (0x8003790c, 184, 160), (0x80037960, 184, 160), (0x800379e8, 184, 160),
        (0x80037b38, 172, 188), (0x80037b94, 154, 170), (0x80037bbc, 166, 182), (0x80037bf4, 166, 182),
    ]),
    # rice / horse price tables (Records): frame 24 px / 34 cells -> 8 / 38; 3 groups of (Province | Buy | Sell)
    # 88 px apart -> 96 (stride = WORDS); sort tabs 5 cells -> 8 (cursor stride 40 -> 64 = WORDS);
    # unknown prices: "Unknown" -> the "---" of 0x800cf540.
    'rice prices': ('PROG', [
        (0x80038a2c, 24, 8), (0x80038a34, 272, 304), (0x80038a60, 24, 8), (0x80038a68, 34, 38),
        (0x80038a90, 5, 8), (0x80038ab0, 6, 9), (0x80038ab8, 5, 8), (0x80038ad8, 11, 17), (0x80038ae0, 5, 8),
        (0x80038af8, 33, 17), (0x80038b00, 38, 62),
        (0x80038b68, 34, 19), (0x80038b80, 74, 83), (0x80038b98, 114, 147),
        (0x80038c04, 32, 16), (0x80038c0c, 256, 288), (0x80038ce8, 34, 18),
        (0x80038d04, 32, 16), (0x80038d5c, 32, 16), (0x80038d9c, 94, 90),
        (0x80038e7c, 28, 48), (0x80038ea8, 56, 72),
        (0x80038f10, 28, 54), (0x80038f28, 56, 78), (0x80038f18, -0x7bbc, -0x7a14), (0x80038f30, -0x7bbc, -0x7a14),
        (0x80038fa0, 88, 96), (0x8003901c, 248, 264),
        (0x80039084, 24, 8), (0x8003908c, 272, 304),
        (0x800391f8, 33, 17), (0x80039200, 38, 62), (0x800394c0, 33, 17), (0x800394c8, 38, 62),
    ]),
    'horse prices': ('PROG', [
        (0x800395f4, 24, 8), (0x800395fc, 272, 304), (0x80039628, 24, 8), (0x80039630, 34, 38),
        (0x80039658, 5, 8), (0x80039678, 6, 9), (0x80039680, 5, 8), (0x800396a0, 11, 17), (0x800396a8, 5, 8),
        (0x800396c0, 33, 17), (0x800396c8, 38, 62),
        (0x80039730, 34, 19), (0x80039748, 74, 83), (0x80039760, 114, 147),
        (0x800397cc, 32, 16), (0x800397d4, 256, 288), (0x800398b0, 40, 18),
        (0x800398cc, 32, 16), (0x80039924, 32, 16), (0x80039944, 66, 81),
        (0x800399e8, 28, 60), (0x80039a3c, 28, 66), (0x80039a44, -0x7bbc, -0x7a14),
        (0x80039ab4, 88, 96), (0x80039b30, 248, 264),
        (0x80039b98, 24, 8), (0x80039ba0, 272, 304),
        (0x80039d0c, 33, 17), (0x80039d14, 38, 62), (0x80039fd4, 33, 17), (0x80039fdc, 38, 62),
    ]),
    # Daimyo Info (Records) 0x800367a4, rows 0x80036b18, close 0x80036ccc: frame 76 px / 21 cells -> 52 / 27;
    # Head | Court Standing | Power boxes 6+4, 6+8, 6+8 -> 6+4, 6+10, 6+10;
    # Other clan | Relation | Feeling: cells 2+8, 10+4, 14+4 -> 2+11, 13+6, 19+7
    'daimyo info': ('PROG', [
        (0x80036800, 76, 52), (0x80036808, 168, 216), (0x80036cfc, 76, 52), (0x80036d04, 168, 216),
        (0x8003688c, 76, 52), (0x80036894, 21, 27), (0x80036854, 84, 60),
        (0x800368e4, 8, 10), (0x8003690c, 8, 10),
        (0x80036934, 8, 11), (0x80036954, 10, 13), (0x8003695c, 4, 6), (0x8003697c, 14, 19), (0x80036984, 4, 7),
        (0x800369a0, 128, 104), (0x800369b8, 126, 104), (0x800369d4, 138, 124),
        (0x800369ec, 94, 86), (0x80036a20, 192, 214),
        (0x80036a54, 84, 60), (0x80036a84, 160, 136), (0x80036aa8, 194, 186), (0x80036acc, 194, 186),
        (0x80036b30, 84, 60), (0x80036b38, 144, 200), (0x80036b94, 196, 220),
        (0x80036c04, 94, 70), (0x80036c3c, 160, 158), (0x80036c74, 192, 206),
    ]),
    # farmhouse "Ask about area" panels (MAPPOINT 0x8014dd58 land / 0x8014e210 stores / 0x8014e674 troops):
    # frame 96 px + 16 cells -> 56 px + 26 cells; label boxes cell 2, 4-7 wide -> cell 1, 8 wide; header
    # "<province> <castle>" 64 / 126 (the format is "%s" now), clan 64, Main Castle / Direct Rule 186;
    # numbers end at 248 (the "k koku" row starts 8 px earlier)
    'area info': ('MAPPOINT', [
        (0x8014dd48, 96, 56), (0x8014dd50, 128, 208), (0x8014dd7c, 96, 56), (0x8014dd84, 16, 26), (0x8014e194, 96, 56), (0x8014e19c, 128, 208),
        (0x8014dda4, 2, 1), (0x8014ddcc, 2, 1), (0x8014ddf4, 2, 1), (0x8014de1c, 2, 1), (0x8014de44, 2, 1), (0x8014ddac, 4, 8), (0x8014ddd4, 4, 8), (0x8014ddfc, 4, 8), (0x8014de24, 4, 8), (0x8014de4c, 7, 8),
        (0x8014dee4, 104, 64), (0x8014df0c, 156, 126), (0x8014df44, 104, 64), (0x8014dfac, 180, 186),
        (0x8014dfd4, 116, 68), (0x8014dfec, 116, 68), (0x8014e004, 116, 68), (0x8014e01c, 116, 68), (0x8014e034, 116, 68),
        (0x8014e06c, 160, 200), (0x8014e0a4, 160, 192), (0x8014e0c4, 160, 200), (0x8014e0e8, 160, 200), (0x8014e118, 190, 230), (0x8014e144, 172, 212),
        (0x8014e200, 96, 56), (0x8014e208, 128, 208), (0x8014e234, 96, 56), (0x8014e23c, 16, 26), (0x8014e60c, 96, 56), (0x8014e614, 128, 208),
        (0x8014e25c, 2, 1), (0x8014e284, 2, 1), (0x8014e2ac, 2, 1), (0x8014e2d4, 2, 1), (0x8014e2fc, 2, 1), (0x8014e264, 4, 8), (0x8014e28c, 5, 8), (0x8014e2b4, 4, 8), (0x8014e2dc, 4, 8), (0x8014e304, 4, 8),
        (0x8014e38c, 104, 64), (0x8014e3b4, 156, 126), (0x8014e3fc, 104, 64), (0x8014e468, 180, 186),
        (0x8014e490, 116, 68), (0x8014e4a8, 114, 68), (0x8014e4c0, 116, 68), (0x8014e4d8, 116, 68), (0x8014e4f0, 116, 68),
        (0x8014e524, 160, 200), (0x8014e548, 160, 200), (0x8014e56c, 160, 200), (0x8014e590, 160, 200), (0x8014e5b4, 160, 200),
        (0x8014e664, 96, 56), (0x8014e66c, 128, 208), (0x8014e698, 96, 56), (0x8014e6a0, 16, 26), (0x8014ea68, 96, 56), (0x8014ea70, 128, 208),
        (0x8014e6c0, 2, 1), (0x8014e6e8, 2, 1), (0x8014e710, 2, 1), (0x8014e738, 2, 1), (0x8014e760, 2, 1), (0x8014e6c8, 5, 8), (0x8014e6f0, 4, 8), (0x8014e718, 5, 8), (0x8014e740, 5, 8), (0x8014e768, 5, 8),
        (0x8014e800, 104, 64), (0x8014e828, 156, 126), (0x8014e860, 104, 64), (0x8014e8c8, 180, 186),
        (0x8014e8f0, 114, 68), (0x8014e908, 116, 68), (0x8014e920, 114, 68), (0x8014e938, 114, 68), (0x8014e950, 114, 68),
        (0x8014e984, 160, 200), (0x8014e9ac, 160, 200), (0x8014e9cc, 160, 200), (0x8014e9f4, 160, 200), (0x8014ea14, 160, 200),
    ]),
    # person detail header 0x8003a440: name 16 | age 96 + age-mark sprite 112 | rank 132 | court title 184
    # -> 16 | 134 + 148 | 164 | 240 (title strip sprite 108 px wide -> 80); unknown-age piece 100 -> 136
    # item info panel 0x8003cc94 (shop Square, belongings): frame 48 px / 29 cells; "Type" box cell 6, value
    # 132; "Value" box cell 18 -> 21 (216 px), number 228 -> 252 ("Nanban Goods" ends at ~205)
    'item info': ('PROG', [
        (0x8003ccd8, 18, 21), (0x8003cdc8, 196, 220), (0x8003ce34, 228, 252), (0x8003cef0, 228, 252),
    ]),
    # belongings 0x80035f9c: Name | Qty | Appraise; frame 80 px / 20 cells -> 60 px / 25 cells; boxes (cells)
    # 1+10, 11+4, 15+4 -> 1+12, 13+4, 17+7
    'belongings': ('PROG', [
        (0x80035f8c, 80, 60), (0x80035f94, 160, 200), (0x800362c8, 80, 60), (0x800362d0, 160, 200),
        (0x80035fc0, 80, 60), (0x80035fc8, 20, 25),
        (0x80035ff0, 10, 12), (0x80036010, 11, 13), (0x80036038, 15, 17), (0x80036040, 4, 7),
        (0x8003605c, 116, 102), (0x80036074, 172, 171), (0x8003608c, 204, 201),
        (0x800360d0, 88, 68), (0x800360d4, 144, 184), (0x80036358, 88, 68), (0x8003635c, 144, 184),
        (0x80036694, 88, 68), (0x80036698, 144, 184), (0x80036130, 88, 68), (0x80036138, 144, 184),
        (0x80036198, 92, 72), (0x800361bc, 184, 176), (0x80036200, 210, 218), (0x80036278, 192, 212),
    ]),
    # destination list on the map 0x80042d84 (Mission / By Province / By Daimyō / All): Castle | Days | Clan |
    # Province; frame 48 px / 28 cells -> 16 px / 36 cells; boxes (cells) 1+8, 9+5, 14+8, 22+5 -> 1+12, 13+6,
    # 19+8, 27+7 (the Days column keeps its pixels); clan without " clan" (strbuf.SHORT_CALLS)
    'destinations': ('PROG', [
        (0x80042d74, 48, 16), (0x80042d7c, 224, 288), (0x80043260, 48, 16), (0x80043268, 224, 288),
        (0x80042da8, 48, 16), (0x80042db0, 28, 36),
        (0x80042dd8, 8, 12), (0x80042df8, 9, 13), (0x80042e00, 5, 6), (0x80042e20, 14, 19),
        (0x80042e48, 22, 27), (0x80042e50, 5, 7),
        (0x80042e6c, 76, 54), (0x80042e9c, 162, 170), (0x80042eb8, 226, 236),
        (0x80042f00, 56, 24), (0x80042f04, 208, 272), (0x8004362c, 56, 24), (0x80043630, 208, 272),
        (0x80042f64, 48, 16), (0x80042f6c, 224, 288), (0x80042fb8, 224, 256),
        (0x800430c4, 58, 26), (0x800431a0, 162, 170), (0x800431d0, 232, 236),
    ]),
    # council mission list (MAPPOINT list type 2: init 0x8014c480, draw 0x80147ed8): Mission | Budget | Target |
    # Min. rank; frame 40 px / 240 -> 8 / 304; boxes (cells) 1+8, 9+5, 14+8, 22+7 -> 1+11, 12+5, 17+10, 27+10.
    # Target without " Castle" / " clan" (WORDS), budget without " kan" (progstr 800d039c).
    'mission list': ('MAPPOINT', [
        (0x8014c53c, 0x30, 16), (0x8014c544, 0xe0, 288), (0x8014c550, 0xe8, 264),     # cursor bar, page icon
        (0x8014c57c, 0x28, 8), (0x8014c584, 0xf0, 304),                               # frame
        (0x80147f24, 8, 11), (0x80147f44, 9, 12), (0x80147f6c, 14, 17), (0x80147f74, 8, 10),
        (0x80147f94, 22, 27), (0x80147f9c, 7, 10),
        (0x80147fb8, 68, 43), (0x80147fd0, 120, 107), (0x80147fe8, 160, 167), (0x80148004, 220, 242),
        (0x801480c8, 50, 18), (0x801480ec, 114, 108), (0x80148110, 154, 146), (0x8014813c, 220, 226),
    ]),
    # council assignment list (MAPPOINT list type 3: init 0x8014c67c, draw 0x801481b8): Mission | Officer;
    # frame 80 px / 160 -> 56 / 208; boxes (8-px cells) 1+8, 9+10 -> 1+11, 12+13 ("Warrior Training" 79 px,
    # "Takigawa Kazumasu" 97 px; "Hire Ashigaru" touched the officer in a 64-px column); officer x stays 156
    'assignment list': ('MAPPOINT', [
        (0x8014c694, 0x58, 64), (0x8014c69c, 0x90, 192), (0x8014c6a8, 0xc0, 216),     # cursor bar, page icon
        (0x8014c6d4, 0x50, 56), (0x8014c6dc, 0xa0, 208),                              # frame
        (0x80148204, 8, 11), (0x80148224, 9, 12), (0x8014822c, 10, 13),
        (0x80148248, 108, 90), (0x80148260, 168, 188),
        (0x801482d0, 90, 66),
    ]),
    # council recommendation list (MAPPOINT list type 4: init 0x8014c3d8, draw 0x801483a4..; only caller
    # 0x8010adf0): Officer | Rank | Backer; frame 44 px / 232 -> 8 / 304; boxes 1+10, 11+7, 18+10 -> 1+14,
    # 15+9, 24+13 ("Ashigaru Ge" was cut by the backer's name)
    'recommend list': ('MAPPOINT', [
        (0x8014c418, 0x34, 16), (0x8014c420, 0xd8, 288), (0x8014c42c, 0xe4, 264),     # cursor bar, page icon x
        (0x8014c458, 0x2c, 8), (0x8014c460, 0xe8, 304),                               # frame
        (0x801483a4, 0x2c, 8), (0x801483ac, 0xe8, 304),                               # clear
        (0x801483e8, 10, 14), (0x80148408, 11, 15), (0x80148410, 7, 9), (0x80148430, 18, 24), (0x80148438, 10, 13),
        (0x8014845c, 74, 54), (0x80148474, 148, 152), (0x8014848c, 204, 236),         # heads
        (0x801484f8, 56, 20), (0x8014851c, 136, 132), (0x8014857c, 192, 204),         # rows
    ]),
    # province price list (MAPPOINT list type 5: init 0x8014b734, draw 0x80148600; Give Orders -> Assign Work ->
    # Ask Prices): Province | Price; frame 16 px / 88 -> 136; boxes 1+4, 5+5 -> 1+8, 9+7 ("ProvincPrice",
    # "MutsuUnknown"; "Shimotsuke" 54 px, "Surveying" 49 px)
    'price orders': ('MAPPOINT', [
        (0x8014b754, 0x48, 120), (0x8014b760, 0x38, 104),                             # cursor bar w, page icon x
        (0x8014b794, 0x58, 136),                                                      # frame
        (0x80148664, 4, 8), (0x80148684, 5, 9), (0x8014868c, 5, 7),
        (0x801486a8, 28, 35), (0x801486c0, 64, 104),                                  # heads
        (0x80148798, 58, 90), (0x801487e0, 58, 90),                                   # rows
    ]),
    # shop item list (MAPPOINT list type 8: init 0x8014d858, open 0x8014d81c, draw 0x80148d60): Name | Price;
    # frame 76 px / 168 -> 60 / 200 ("3 kan 200 mon" ran past the frame); boxes 1+10, 11+9 -> 1+12, 13+11;
    # name 88 -> 72, mon 204 -> 212 (kan stays at 166), plain number 198 -> 214, dashes 166 / 204 -> 172 / 218
    'shop list': ('MAPPOINT', [
        (0x8014d890, 0x54, 68), (0x8014d898, 0x98, 184), (0x8014d8a4, 0xc4, 212),     # cursor bar, page icon x
        # (0x801479e0(obj, 0, 0, y, x): a3 = icon y 192, the stack word = icon x)
        (0x8014d834, 0x4c, 60), (0x8014d83c, 0xa8, 200),                              # frame
        (0x8014d914, 0x4c, 60), (0x8014d91c, 0xa8, 200), (0x80148d6c, 76, 60), (0x80148d74, 168, 200),   # clears
        (0x80148db4, 10, 12), (0x80148dd4, 11, 13), (0x80148ddc, 9, 11),
        (0x80148df8, 112, 103), (0x80148e38, 182, 196),
        (0x80148f30, 88, 72), (0x80148f90, 88, 72), (0x80149000, 88, 72),
        (0x80148f54, 198, 214), (0x80148fa8, 166, 172), (0x80148fc0, 204, 218), (0x80149080, 204, 212),
    ]),
    # save slot list 0x80087e2c and the System Memory row 0x80089d30: n | date | name | rank; frame 32 px /
    # 32 cells -> 8 / 38 ("Ashigaru Gen." was cut): number 40 -> 16, date 56 -> 32, name 148 -> 100, rank 228 -> 218
    'save slots': ('PROG', [
        (0x80087e38, 32, 8), (0x80087e40, 32, 38), (0x80087e84, 30, 36),
        (0x80087ea0, 0x28, 16), (0x80087ebc, 0x38, 32), (0x80088050, 0x94, 100), (0x8008807c, 0xe4, 218),
        (0x80088108, 32, 8), (0x80088110, 256, 304),
        (0x80088248, 41, 17), (0x8008824c, 238, 286), (0x800882b0, 41, 17), (0x800882b4, 238, 286),
        (0x80088318, 41, 17), (0x8008831c, 238, 286),
        (0x80089d3c, 32, 8), (0x80089d44, 32, 38), (0x80089d6c, 30, 36),
        (0x80089d78, 0x38, 32), (0x80089dd8, 0x94, 100), (0x80089df8, 0xe4, 218),
        (0x80089e84, 32, 8), (0x80089e8c, 256, 304),
    ]),
    # new-game ability type panel: skill marks (sprites 0x97.., created at 0x800749b4) x = base + 12 * level
    # slot; they sat on the English names (Special Tale types start with skill levels)
    'ability panel marks': ('PROG', [(0x800749c0, 0xb0, 206), (0x800749d0, 0xf0, 294)]),
    'person detail': ('PROG', [
        (0x8003a480, 112, 126), (0x8003a4b0, 96, 148), (0x8003a4c8, 96, 148), (0x8003a4ec, 132, 164),
        (0x8003a54c, 184, 240), (0x8003a588, 184, 240), (0x8003a56c, 108, 80), (0x8003a5c0, 100, 126),
        (0x8003ad88, 232, 228),      # stipend "%4u": ends 4 px before the "kan" sprite (figure-space pad)
    ]),
    # person detail, label sprites of the English sheet (tools/gfx.py CELLS: u = 640 + x / 2, v, width):
    # "Age" 20 px before the number (name 16 | Age 126 | number 148 | rank 164), "Dead" 26 px, "kan" 18 px,
    # ability names 44 / 38 / 50 / 32 px around the diamond
    'person detail gfx': ('PROG', [
        (0x8003a478, 672, 693), (0x8003a47c, 144, 208), (0x8003a464, 12, 20),
        (0x8003a5b8, 672, 680), (0x8003a5bc, 156, 196), (0x8003a5a4, 24, 26),
        (0x8003ad38, 672, 684), (0x8003ad3c, 132, 208), (0x8003ad24, 12, 18),
        (0x8003af94, 640, 672), (0x8003af9c, 220, 216), (0x8003af80, 36, 44),
        (0x8003afc4, 658, 640), (0x8003afc8, 36, 48), (0x8003afb0, 36, 38),
        (0x8003aff4, 640, 672), (0x8003affc, 172, 158), (0x8003afe0, 36, 50),
        (0x8003b024, 658, 670), (0x8003b028, 48, 220), (0x8003b02c, 220, 222), (0x8003b010, 36, 32),
        (0x8003afa8, 90, 83), (0x8003afd8, 90, 83),      # side labels above the diamond's tips
    ]),
    # battle organisation screen (BATTLE 0x80108a50 rows): troop type 82 -> 74, count 118 -> 122
    # ("Infantry" / "Gunners" were cut by the count; the frame ends at ~155 px)
    'battle organisation': ('BATTLE', [
        (0x80108a88, 0x52, 74), (0x80108a9c, 0x76, 122),
        # rice / funds "%8u" and fatigue "%3u": with the figure-space pad (vwf.FIGSP) they end at x = 254
        # again, under the redrawn "Cannon" / "Drill" / "Morale" labels (they start at ~248)
        (0x80108818, 206, 194), (0x8010883c, 206, 194), (0x80108854, 236, 230),
    ]),
    # battle Unit Info panel 0x8013d6xx: label 148 | ":" 176 | value 192: the colon was drawn over the last
    # letter of "Troops" / "Morale" / "Fatigue" (34-36 px) -> 185
    'battle unit info': ('BATTLE', [
        (0x8013d6bc, 176, 185), (0x8013d720, 176, 185), (0x8013d7a8, 176, 185), (0x8013d830, 176, 185),
    ]),
    # battle unit detail header (two variants): army 16 | "Unit n" / "Leader" 84 | name 140 | age 220 (the
    # age mark is not drawn here: age stays) | rank 252 -> 8 | 76 | 116 | 220 | 250
    # ("Sakuma Nobumori37", "Chief Retaine"). Name room 102 px; an army name over 66 px touches the label.
    'battle unit detail': ('BATTLE', [
        (0x8013df58, 16, 8), (0x8013dfa8, 84, 76), (0x8013dfcc, 140, 116), (0x8013e014, 252, 250),
        (0x8013e110, 16, 8), (0x8013e160, 84, 76), (0x8013e184, 140, 116), (0x8013e1cc, 252, 250),
    ]),
    # battle unit detail, stats (0x8013e1e0-0x8013e480; second half = an unknown unit, "-"): the labels are
    # English in the picture (tools/gfx.py unit_detail: "Fatigue" ends at 200): bars 192 -> 202, numbers
    # 274 -> 284. The small window 0x8013e588 (relative coordinates) is a different screen: untouched.
    'battle unit detail gfx': ('BATTLE', [
        (0x8013e274, 192, 202), (0x8013e2c8, 192, 202), (0x8013e318, 192, 202), (0x8013e36c, 192, 202),
        (0x8013e3d8, 192, 202), (0x8013e40c, 192, 202), (0x8013e440, 192, 202), (0x8013e474, 192, 202),
        (0x8013e238, 274, 284), (0x8013e298, 274, 284), (0x8013e2e8, 274, 284), (0x8013e334, 274, 284),
        (0x8013e3b8, 274, 284), (0x8013e3ec, 274, 284), (0x8013e420, 274, 284), (0x8013e454, 274, 284),
    ]),
    # battle Overview, Circle on a unit: the small bar panel 0x8013e580 (frame 80 px / 20 cells, label boxes
    # 4 cells: "Troop", "Training" under the bars, "Fatigu") -> frame 72 px / 22 cells, label boxes 6 cells,
    # labels 92 -> 84, type / bars 122 -> 130, numbers 204 -> 212, header boxes 1+9 / 10+9 -> 1+10 / 11+10
    # with their centres 124 / 196 -> 120 / 200; the two clears (open, close 0x8013e914) follow the frame
    'battle unit panel': ('BATTLE', [
        (0x8013e588, 80, 72), (0x8013e590, 160, 176), (0x8013e928, 80, 72), (0x8013e930, 160, 176),
        (0x8013e5bc, 80, 72), (0x8013e5c4, 20, 22),
        (0x8013e5ec, 9, 10), (0x8013e66c, 10, 11), (0x8013e674, 9, 10), (0x8013e644, 124, 120), (0x8013e6a0, 196, 200),
        (0x8013e6f8, 4, 6), (0x8013e71c, 92, 84),
        (0x8013e76c, 122, 130), (0x8013e7a8, 122, 130), (0x8013e808, 122, 130), (0x8013e864, 122, 130),
        (0x8013e8b8, 122, 130),
        (0x8013e7c8, 204, 212), (0x8013e834, 204, 212), (0x8013e884, 204, 212), (0x8013e8d4, 204, 212),
    ]),
    # Special Works (Records menu) 0x8003d690, rows 0x8003d760: frame 48 px / 28 cells -> 8 / 38, label box
    # 7 -> 8 cells ("Land Survey" 61 px), label x 60 -> 18, names from x 112 -> 84; stride 52 -> 76: WORDS
    # (row 1 holds three names: "Oxen & Horses" 71, "Better Tools", "Better Strains" 68 px)
    'special works': ('PROG', [
        (0x8003d69c, 48, 8), (0x8003d6a4, 224, 304), (0x8003d8f4, 48, 8), (0x8003d8fc, 224, 304),
        (0x8003d6d0, 48, 8), (0x8003d6d8, 28, 38), (0x8003d718, 7, 8),
        (0x8003d7b4, 60, 18), (0x8003d7f8, 0x70, 84),
    ]),
    # officer pick list (MAPPOINT list types 0 / 1: openers 0x8014a3dc / 0x8014adb8, draw 0x80149db8; Request
    # Aide and 15 other callers): Officer | Rank | Dom Dip Mil Cha, L1 / R1 = Officer | 12 skills. Frame
    # 16 px / 288 -> 8 / 304 ("Ashigaru Capt." ran under the ability columns). Abilities page: boxes 1+10,
    # 11+8, 19+4i (4 wide) -> 1+14, 15+10, 25+3i (3 wide: WORDS / CODE below); skills page: 11+2i -> 13+2i
    # (they cover the right end of the officer box; names are cut to 92 px there by FITNAME)
    'officer list': ('MAPPOINT', [
        (0x8014a438, 0x18, 16), (0x8014a440, 0x110, 288), (0x8014a458, 0x18, 16), (0x8014a44c, 0x100, 264),
        (0x8014a480, 0x10, 8), (0x8014a488, 0x120, 304),
        (0x8014ae10, 0x18, 16), (0x8014ae18, 0x110, 288), (0x8014ae30, 0x78, 0x70), (0x8014ae24, 0x100, 264),
        (0x8014ae50, 0x10, 8), (0x8014ae58, 0x120, 304),
        (0x80149e7c, 10, 14), (0x80149ea0, 0x1e, 46),                                 # Officer
        (0x80149ee4, 11, 15), (0x80149eec, 8, 10), (0x80149f30, 0x66, 138), (0x80149f40, 0x6d, 148),   # (New) Rank
        (0x80149fac, 4, 3), (0x80149fc0, 0x9c, 203),                                  # ability heads
        (0x8014a0d4, 12, 10), (0x8014a100, 0x60, 126),                                # name, rank
        (0x8014a1d8, 11, 13), (0x8014a200, 0x5a, 106),                                # skill heads
        (0x8014a314, 12, 10), (0x8014a340, 0x5a, 106),                                # name, skill levels
        # header cursor (below the last row; two copies): Rank, skill column (16 i + x); abilities in CODE
        (0x8014a620, 105, 129), (0x8014a628, 62, 78), (0x8014a694, 0x69, 113),
        (0x8014a8c0, 105, 129), (0x8014a8c8, 62, 78), (0x8014a934, 0x69, 113),
        # multi-select variant (type 1): "All" / "OK" buttons under the rows (boxes follow the frame): text, cursor
        (0x80147e6c, 28, 20), (0x80147e84, 60, 52),
        (0x8014aeb0, 0x19, 17), (0x8014aec0, 0x39, 49), (0x8014b110, 0x19, 17), (0x8014b120, 0x39, 49),
    ]),
    # mission works (session 60): the hero carries out a domestic mission (New Fields ... Train: entering the
    # target town asks "Carry out X?"), draw 0x80023bb8 (L1 / R1: Officer | Cost | Skills <-> Details), list
    # init 0x800236c8, chooser 0x800241ec. Frame 16 / 288 -> 8 / 304; work names 7 cells -> 11 (86 px);
    # boxes 9+10, 20+6, 27+7 -> 12+12, 24+6, 30+7; Details 8+27 -> 12+25 (descriptions <= 194 px);
    # officer through FITNAME (90 px): CODE
    'mission works': ('PROG', [
        (0x800236d4, 16, 8), (0x800236dc, 288, 304), (0x800241a4, 16, 8), (0x800241ac, 288, 304),
        (0x80023bd0, 80, 104), (0x80023bd8, 216, 200), (0x80023c20, 16, 8), (0x80023c28, 36, 38),
        (0x80023c68, 7, 11), (0x800237dc, 28, 20), (0x80023810, 28, 20), (0x80023860, 28, 20),
        (0x8002389c, 25, 17), (0x800238a4, 54, 86),                                   # row cursor (two copies)
        (0x80024460, 25, 17), (0x80024490, 25, 17), (0x80024494, 54, 86),
        (0x80023ce4, 9, 12), (0x80023cec, 10, 12), (0x80023d58, 98, 134),             # Officer
        (0x80023d0c, 20, 24), (0x80023d74, 188, 213),                                 # Cost
        (0x80023d34, 27, 30), (0x80023d8c, 236, 264),                                 # Skills
        (0x80023eb4, 92, 108), (0x80023ef0, 184, 202), (0x80023f2c, 238, 252),        # rows
        (0x80023f74, 8, 12), (0x80023f7c, 27, 25), (0x80023f98, 176, 188),            # Details
        (0x800240c8, 80, 108), (0x800240fc, 80, 108), (0x8002414c, 204, 232),
    ]),
    # ... its officer pick list (draw 0x80024744, a copy of MAPPOINT's 'officer list' with the heads of the
    # table 0x800b2628): frame 16 / 288 -> 8 / 304; abilities page 1+10, 11+7, 18+4i -> 1+14, 15+10, 25+3i
    # (CODE); skills page 11+2i -> 13+2i; names through FITPAGE (114 / 92 px)
    'mission officers': ('PROG', [
        (0x80024610, 16, 8), (0x80024618, 288, 304), (0x80024758, 16, 8), (0x80024760, 288, 304),
        (0x8002478c, 16, 8), (0x80024794, 36, 38), (0x8002613c, 24, 16), (0x80026140, 272, 288),   # + row cursor
        (0x800247cc, 10, 14), (0x800247d8, 46, 54),
        (0x80024814, 11, 15), (0x8002481c, 7, 10), (0x80024828, 120, 156), (0x80024874, 4, 3),
        (0x800249f8, 28, 20), (0x80024a3c, 108, 132), (0x80024af8, 28, 20),
        (0x800248e4, 11, 13), (0x80024908, 0x6a, 114), (0x80024ac0, 0x6a, 115), (0x80024bc0, 256, 264),
    ]),
    # four lord-only MAPPOINT lists (session 49; none reachable below daimyo: seen through RAM redirects)
    # type 6 (init 0x8014b8d0, draw 0x80148850): Officer | Castle | Castles, 5 rows; frame 64 px / 192 -> 24 /
    # 272; boxes 1+10, 11+8, 19+4 -> 1+15, 16+12, 28+5; castle getter flag 1 -> 2 (no " Castle")
    'lord officers': ('MAPPOINT', [
        (0x8014b8e8, 0x48, 32), (0x8014b8f0, 0xb0, 256),                              # cursor bar
        (0x8014b908, 0x48, 32), (0x8014b8fc, 0xd0, 248),                              # L1 / R1 hint x, page x
        (0x8014b92c, 0x40, 24), (0x8014b934, 0xc0, 272),                              # frame
        (0x801488b4, 10, 15), (0x801488d4, 11, 16), (0x801488dc, 8, 12), (0x801488fc, 19, 28), (0x80148904, 4, 5),
        (0x80148920, 94, 74), (0x80148938, 172, 185), (0x80148950, 220, 250),
        (0x801489b4, 76, 36), (0x801489ec, 1, 2), (0x801489fc, 154, 156), (0x80148a1c, 226, 259),
    ]),
    # type 7 (init 0x8014b994, draw 0x80148a88): Officer | Mission | Target | Result, frame stays 8 / 304;
    # boxes 1+10, 11+8, 19+8, 27+10 -> 1+10, 11+10, 21+7, 28+9; officer through FITNAME (78 px), target
    # through TARGET (54 px, no suffix): CODE below; "%s skill up" is "%s up" (progstr 80150c2c)
    'vassal missions': ('MAPPOINT', [
        (0x80148b18, 8, 10), (0x80148b38, 19, 21), (0x80148b40, 8, 7), (0x80148b60, 27, 28), (0x80148b68, 10, 9),
        (0x80148b9c, 116, 119), (0x80148bb4, 168, 187), (0x80148bd0, 252, 253),
        (0x80148c3c, 20, 18), (0x80148ca8, 162, 180), (0x80148cd4, 228, 237),
    ]),
    # type 9 (init 0x8014d380, draw 0x801491ac): Daimyo | Castles + "Info" (stays), and type 10 (init
    # 0x8014d79c, draw 0x801493d4): Province | Castles: the same numbers as 'daimyo list' / 'province list'
    'lord daimyo': ('MAPPOINT', [
        (0x8014d398, 0x74, 108), (0x8014d3a0, 0x58, 104), (0x8014d3ac, 0xa4, 172),
        (0x8014d428, 0x6c, 100), (0x8014d430, 0x68, 120),
        (0x801491f8, 7, 8), (0x80149218, 8, 9), (0x80149220, 4, 5),
        (0x8014923c, 120, 123), (0x80149254, 176, 175), (0x801492dc, 120, 110), (0x80149304, 182, 183),
    ]),
    'lord provinces': ('MAPPOINT', [
        (0x8014d7b4, 0x80, 108), (0x8014d7bc, 0x40, 104), (0x8014d7c8, 0x98, 172),
        (0x8014d7f4, 0x78, 100), (0x8014d7fc, 0x50, 120),
        (0x80149420, 4, 8), (0x80149440, 5, 9), (0x80149448, 4, 5),
        (0x80149464, 132, 119), (0x8014947c, 164, 175), (0x80149504, 132, 110), (0x8014952c, 170, 183),
    ]),
}

# whole instructions: (image tag, address, old word, new word)
WORDS = [
    # 'lord daimyo': clan without " clan" (strbuf.SHORT)
    ('MAPPOINT', 0x801492d0, 0x0c0172ad, 0x0c0172af),
    # price tables: tab cursor x = 40 * tab -> 64 * tab (sll 2, add -> sll 3, nop)
    ('PROG', 0x800391ec, 0x00111080, 0x001110c0), ('PROG', 0x800391f0, 0x00511020, 0),
    ('PROG', 0x800394b4, 0x00111080, 0x001110c0), ('PROG', 0x800394b8, 0x00511020, 0),
    ('PROG', 0x80039d00, 0x00111080, 0x001110c0), ('PROG', 0x80039d04, 0x00511020, 0),
    ('PROG', 0x80039fc8, 0x00111080, 0x001110c0), ('PROG', 0x80039fcc, 0x00511020, 0),
    # price tables: header group x = 88 * group -> 96 * group (((g*5)*2+g)*8 -> ((g*3)*4)*8)
    ('PROG', 0x80038d44, 0x00031080, 0x00031040), ('PROG', 0x80038d4c, 0x00021040, 0x00021080),
    ('PROG', 0x80038d50, 0x00431020, 0),
    ('PROG', 0x8003990c, 0x00031080, 0x00031040), ('PROG', 0x80039914, 0x00021040, 0x00021080),
    ('PROG', 0x80039918, 0x00431020, 0),
    # Special Works: name x = 52 * n -> 76 * n (v0 = n << 6; + n << 3; + n << 2; v1 is free here)
    ('PROG', 0x8003d7e4, 0x00111040, 0x00111180), ('PROG', 0x8003d7e8, 0x00511020, 0x001118c0),
    ('PROG', 0x8003d7ec, 0x00021080, 0x00431021), ('PROG', 0x8003d7f0, 0x00511020, 0x00111880),
    ('PROG', 0x8003d7f4, 0x00021080, 0x00431021),
    # destination list: castle name without " Castle" (a1 = 2 of the castle getter: other suffixes stay)
    ('PROG', 0x800430ac, 0x24050001, 0x24050002),
    # council mission list: target castle without " Castle", clan without " clan" (strbuf.SHORT)
    ('MAPPOINT', 0x8010ebcc, 0x24050001, 0x00002821), ('MAPPOINT', 0x8010ec00, 0x0c0172ad, 0x0c0172af),
]

# person detail header: court title "%s%s" (court rank "Sr 3rd" + title) ran past the screen edge
# ("Sr 3rdV.Dainagor"): print the title alone ("%s" = the tail of the "%s%s" string, a3 = the title; every
# title is <= 60 px, the slot at x 240 is 80 px)
WORDS += [('PROG', 0x8003a554, 0x278685a8, 0x278685aa), ('PROG', 0x8003a558, 0x02603821, 0x00403821)]

MWIDTH = asm.labels(vwf.DRAW, vwf.draw_code(0))['mwidth']      # a0 = string -> v0 = width in 6-px cells

# BATTLE centred text 0x8013c974(x, y, str): x - strlen * 6 / 2 -> real width (jal strlen -> jal mwidth);
# 10 callers (army / unit names over panels, the previous / next names of the unit detail)
WORDS.append(('BATTLE', 0x8013c998, 0x0c021a14, 0x0c000000 | (MWIDTH >> 2 & 0x3ffffff)))

# BATTLE map label 0x8013be80 (Overview / field hover): "%s%s" with " & co." (PROG 800cfff4) for 2+ units, else
# the game used that string's NUL (gp-0x6f5b = its 5 Japanese bytes) as "": English is 6 bytes, so a lone
# unit read "Name." -> gp-0x6f5a (also at 0x8014446c). **" & co." must stay 6 bytes long.**
# Label box width: jal strlen -> jal mwidth.
WORDS += [('BATTLE', 0x8013c058, 0x278290a5, 0x278290a6), ('BATTLE', 0x8014446c, 0x278590a5, 0x278590a6),
          ('BATTLE', 0x8013c1c8, 0x0c021a14, 0x0c000000 | (MWIDTH >> 2 & 0x3ffffff))]

HDR_NAMES, HDR_NAMES_END = 0x8005e208, 0x8005e290
FITNAME = nameentry.SPARE
# FITNAME(a0 = person id, a1 = pixels) -> full name, cut to "Hatakeyama Yoshits." when wider (in the name
# getter's rotating buffer); in the spare end of the old candidate window (nameentry.SPARE).
# TARGET(a0 = command, a1 = target, a2 = pixels) = the mission target getter 0x8005bcc0 for list columns:
# castle without " Castle" (flag 2), clan without " clan", person; those three cut like FITNAME (their
# getters return private buffers; the other kinds return shared strings and are passed through).
FIT_LINES = [
    'fitname:',
    ('addiu', 'sp', 'sp', -0x20), ('sw', 'ra', 0x1c, 'sp'), ('sw', 's0', 0x18, 'sp'),
    ('sw', 's1', 0x14, 'sp'), ('sw', 's2', 0x10, 'sp'),
    ('jal', 0x8005e124), ('addu', 's1', 'a1', 'zero'),
    'fit:',
    ('addu', 's0', 'v0', 'zero'), ('addu', 's2', 'v0', 'zero'),
    ('addu', 't8', 'v0', 'zero'), ('addu', 't9', 'zero', 'zero'),
    'loop:',
    ('lbu', 'a0', 0, 't8'), ('nop',), ('beqz', 'a0', 'done'), ('nop',),
    ('jal', nameentry.WIDTH), ('nop',),
    ('addu', 't9', 't9', 'v0'), ('addiu', 't8', 't8', 1),
    ('addiu', 'v1', 't9', text.width('.')), ('sltu', 'at', 's1', 'v1'),
    ('bnez', 'at', 'nodot'), ('sltu', 'at', 's1', 't9'),
    ('addu', 's2', 't8', 'zero'),                              # "." still fits after this letter
    'nodot:',
    ('beqz', 'at', 'loop'), ('nop',),
    ('lbu', 'at', -1, 's2'), ('addiu', 'v1', 'zero', 0x20), ('bne', 'at', 'v1', 'dot'), ('nop',),
    ('addiu', 's2', 's2', -1),                                 # no space before the "." ("Ishiyama.")
    'dot:',
    ('addiu', 'v0', 'zero', 0x2e), ('sb', 'v0', 0, 's2'), ('sb', 'zero', 1, 's2'),
    'done:',
    ('addu', 'v0', 's0', 'zero'),
    'ret:',
    ('lw', 'ra', 0x1c, 'sp'), ('lw', 's0', 0x18, 'sp'), ('lw', 's1', 0x14, 'sp'), ('lw', 's2', 0x10, 'sp'),
    ('jr', 'ra'), ('addiu', 'sp', 'sp', 0x20),
    'target:',
    ('addiu', 'sp', 'sp', -0x20), ('sw', 'ra', 0x1c, 'sp'), ('sw', 's0', 0x18, 'sp'),
    ('sw', 's1', 0x14, 'sp'), ('sw', 's2', 0x10, 'sp'),
    ('addu', 's0', 'a0', 'zero'), ('addu', 's2', 'a1', 'zero'),
    ('beqz', 'a0', 'orig'), ('addu', 's1', 'a2', 'zero'),
    ('jal', 0x8005bb04), ('nop',),                             # kind of target: 2 castle, 3 clan, 4 person
    ('addiu', 'at', 'zero', 2), ('beq', 'v0', 'at', 'castle'), ('addiu', 'at', 'zero', 3),
    ('beq', 'v0', 'at', 'clan'), ('addiu', 'at', 'zero', 4),
    ('bne', 'v0', 'at', 'orig'), ('nop',),
    ('jal', 0x8005e124), ('addu', 'a0', 's2', 'zero'),
    ('b', 'fit'), ('nop',),
    'castle:',
    ('addu', 'a0', 's2', 'zero'), ('jal', 0x80056264), ('addiu', 'a1', 'zero', 2),
    ('b', 'fit'), ('nop',),
    'clan:',
    ('jal', 0x8005cabc), ('addu', 'a0', 's2', 'zero'),
    ('b', 'fit'), ('nop',),
    'orig:',
    ('addu', 'a0', 's0', 'zero'), ('jal', 0x8005bcc0), ('addu', 'a1', 's2', 'zero'),
    ('b', 'ret'), ('nop',),
    'fitpage:',                                                # FITNAME for the EXE pick list (s1 = its object)
    ('lw', 'v0', 0x10, 's1'), ('nop',),                        # page: 0 abilities (114 px), else skills (92)
    ('beqz', 'v0', 'fitname'), ('addiu', 'a1', 'zero', 114),
    ('b', 'fitname'), ('addiu', 'a1', 'zero', 92),
]
TARGET = asm.labels(FITNAME, FIT_LINES)['target']
FITPAGE = asm.labels(FITNAME, FIT_LINES)['fitpage']

# code rewritten in place: (image tag, start, end, lines); padded with nops
CODE = [
    # person detail, skills: 4 columns x 3 rows of 24-px labels -> 3 columns x 4 rows of 64-px labels
    # (skill s: column s / 4 at x = 10 + 100 col, row s % 4 at y = 158 + 13 row; level slot at x + 64).
    # Setup of the 36 level icons (i = s1: skill i / 3, icon i % 3) before the call at 0x8003a314:
    ('PROG', 0x8003a288, 0x8003a314, [
        ('addiu', 'v0', 'zero', 7), ('sw', 'v0', 0x10, 'sp'), ('sw', 'zero', 0x14, 'sp'),
        ('addiu', 'a0', 's1', 0x1f), ('addiu', 'a1', 's1', 3),
        ('addiu', 'v0', 'zero', 3), ('divu', 's1', 'v0'), ('mflo', 't0'), ('mfhi', 't1'),
        ('srl', 't2', 't0', 2), ('andi', 't3', 't0', 3),
        ('addiu', 'v0', 'zero', 100), ('multu', 't2', 'v0'), ('mflo', 'a2'),
        ('sll', 'v0', 't1', 3), ('sll', 't1', 't1', 2), ('addu', 'v0', 'v0', 't1'),
        ('addu', 'a2', 'a2', 'v0'), ('addiu', 'a2', 'a2', 74),
        ('sll', 'v0', 't3', 3), ('sll', 'v1', 't3', 2), ('addu', 'v0', 'v0', 'v1'), ('addu', 'v0', 'v0', 't3'),
        ('addiu', 'a3', 'v0', 158),
    ]),
    # the draw loop (s = s1): slot strip, then the label from its sheet cell (gfx.skill_cell):
    # s < 5: (64, 132 + 12 s), else k = s - 5: (64 (k & 1), 12 (k >> 1))
    ('PROG', 0x8003b59c, 0x8003b670, [
        ('andi', 't3', 's1', 3), ('srl', 't2', 's1', 2),
        ('sll', 'v0', 't3', 3), ('sll', 'v1', 't3', 2), ('addu', 'v0', 'v0', 'v1'), ('addu', 'v0', 'v0', 't3'),
        ('addiu', 'v0', 'v0', 158), ('sw', 'v0', 0xa0, 'sp'), ('sw', 'v0', 0x10, 'sp'),
        ('addiu', 'v0', 'zero', 100), ('multu', 't2', 'v0'), ('mflo', 'v0'),
        ('addiu', 'v0', 'v0', 10), ('sw', 'v0', 0xa4, 'sp'), ('addiu', 'a3', 'v0', 64),
        ('addiu', 'v0', 'zero', 36), ('sw', 'v0', 0x14, 'sp'), ('addiu', 'v0', 'zero', 12), ('sw', 'v0', 0x18, 'sp'),
        ('addiu', 'a0', 's1', 0x73), ('addiu', 'a1', 'zero', 661), ('jal', 0x8003a174), ('addiu', 'a2', 'zero', 196),
        ('lw', 'v0', 0xa0, 'sp'), ('addiu', 'v1', 'zero', 64), ('sw', 'v0', 0x10, 'sp'), ('sw', 'v1', 0x14, 'sp'),
        ('addiu', 'v0', 'zero', 12), ('sw', 'v0', 0x18, 'sp'),
        ('addiu', 'a0', 's1', 0x5d),
        ('sltiu', 'at', 's1', 5), ('beqz', 'at', 'top'), ('addiu', 't0', 's1', -5),
        ('sll', 'v0', 's1', 3), ('sll', 'v1', 's1', 2), ('addu', 'v0', 'v0', 'v1'), ('addiu', 'a2', 'v0', 132),
        ('b', 'go'), ('addiu', 'a1', 'zero', 672),
        'top:',
        ('andi', 'v0', 't0', 1), ('sll', 'v0', 'v0', 5), ('addiu', 'a1', 'v0', 640),
        ('srl', 'v0', 't0', 1), ('sll', 'v1', 'v0', 3), ('sll', 'v0', 'v0', 2), ('addu', 'a2', 'v0', 'v1'),
        'go:',
        ('lw', 'a3', 0xa4, 'sp'), ('jal', 0x8003a0c8), ('nop',),
    ]),
    # new-game ability type panel (0x80074d90): skill name x = 0x98 + 64 * (i / 6) -> 142 / 234
    # ("Development", 63 px, touched the second column); 12 skills = 2 columns. The two skill marks
    # (12 px each) follow the name: SCREENS['ability panel marks']
    ('PROG', 0x80074e24, 0x80074e40, [
        ('sltiu', 'v0', 's0', 6), ('bnez', 'v0', 'col0'), ('addiu', 'a0', 'zero', 142),
        ('addiu', 'a0', 'zero', 234),
        'col0:',
    ]),
    # hover label 0x8007bae4 (map): box placement by quadrant, now clamped to the screen
    # (x in [0, 320 - width]); 0x38(sp) = quadrant (bit 1 = left of the cursor, bit 0 = above)
    ('PROG', 0x8007bd7c, 0x8007bea4, [
        ('lw', 'v0', 0xfc, 'sp'), ('lw', 'a1', 0x100, 'sp'),
        ('lw', 't0', 0xc, 's0'), ('lw', 't1', 8, 's0'),
        ('sll', 't0', 't0', 3), ('addiu', 't0', 't0', 16),         # box width
        ('sll', 't1', 't1', 4), ('addiu', 't1', 't1', 8),          # box height
        ('sltiu', 'at', 'v0', 0xa0), ('xori', 't2', 'at', 1), ('sll', 't2', 't2', 1),
        ('bnez', 'at', 'xr'), ('addu', 'v1', 'v0', 'zero'),
        ('subu', 'v1', 'v0', 't0'),
        'xr:',
        ('bgez', 'v1', 'c1'), ('addiu', 't3', 'zero', 320),
        ('addu', 'v1', 'zero', 'zero'),
        'c1:',
        ('subu', 't3', 't3', 't0'), ('slt', 'at', 't3', 'v1'),
        ('beqz', 'at', 'c2'), ('nop',),
        ('addu', 'v1', 't3', 'zero'),
        'c2:',
        ('sw', 'v1', 0, 's0'),
        ('sltiu', 'at', 'a1', 0x78), ('bnez', 'at', 'yt'), ('addiu', 'v0', 'a1', -8),
        ('subu', 'v0', 'a1', 't1'), ('ori', 't2', 't2', 1),
        'yt:',
        ('sw', 'v0', 4, 's0'), ('sw', 't2', 0x38, 'sp'),
    ]),
    # battle organisation header: the unit leader's name was at x = 92 (74 px to the rice label: "Sakuma
    # Nobum"); now right-aligned to x = 166 (vwf mwidth: width in 6-px cells)
    ('BATTLE', 0x801087bc, 0x8010880c, [
        ('jal', 0x800523bc), ('addu', 'a0', 's1', 'zero'),
        ('lui', 'a3', asm.hi(0x8014aea8)),
        ('beqz', 'v0', 'have'), ('addiu', 'a3', 'a3', asm.lo(0x8014aea8)),
        ('jal', 0x8005e124), ('addu', 'a0', 's1', 'zero'),
        ('addu', 'a3', 'v0', 'zero'),
        'have:',
        ('sw', 'a3', 0x44, 'sp'),
        ('jal', MWIDTH), ('addu', 'a0', 'a3', 'zero'),
        ('sll', 'v1', 'v0', 1), ('addu', 'v0', 'v1', 'v0'), ('sll', 'v0', 'v0', 1),
        ('addiu', 'a0', 'zero', 166), ('subu', 'a0', 'a0', 'v0'),
        ('addiu', 'a1', 'zero', 0x14), ('addiu', 'a2', 'gp', -0x7188),
        ('jal', 0x8007b614), ('lw', 'a3', 0x44, 'sp'),
    ]),
    # the same header redrawn when the cursor moves (0x801094bc; it overdrew the old name with a padded
    # "%-..s" at x = 92): leader id -> name, army name, then HDR_NAMES clears the text row and draws both
    ('BATTLE', 0x801094bc, 0x80109554, [
        ('lw', 'v0', 0xa0, 'sp'), ('nop',), ('lw', 'a0', 0, 'v0'),
        ('jal', 0x80138498), ('nop',),
        ('lw', 'v1', 0xa0, 'sp'), ('nop',), ('lw', 'v1', 0xc, 'v1'), ('nop',),
        ('jal', 0x801379bc), ('addu', 'a0', 'v1', 'v0'),
        ('sw', 'v0', 0x44, 'sp'),
        ('jal', 0x800523bc), ('addu', 'a0', 'v0', 'zero'),
        ('lui', 'a3', asm.hi(0x8014aea8)), ('beqz', 'v0', 'have'), ('addiu', 'a3', 'a3', asm.lo(0x8014aea8)),
        ('lw', 'a0', 0x44, 'sp'), ('nop',),
        ('jal', 0x8005e124), ('nop',),
        ('addu', 'a3', 'v0', 'zero'),
        'have:',
        ('sw', 'a3', 0x6c, 'sp'),
        ('lw', 'v0', 0xa0, 'sp'), ('nop',), ('lw', 'a0', 0, 'v0'),
        ('jal', 0x80136608), ('nop',),
        ('lw', 'a1', 0x6c, 'sp'),
        ('jal', HDR_NAMES), ('addu', 'a0', 'v0', 'zero'),
    ]),
    # HDR_NAMES(a0 = army name, a1 = leader name): in the free bytes after the full-name getter (names.py)
    ('PROG', HDR_NAMES, HDR_NAMES_END, [
        ('addiu', 'sp', 'sp', -0x28), ('sw', 'ra', 0x24, 'sp'), ('sw', 'a0', 0x18, 'sp'), ('sw', 'a1', 0x1c, 'sp'),
        ('addiu', 'a0', 'zero', 16), ('addiu', 'a1', 'zero', 20), ('addiu', 'a2', 'zero', 150),
        ('jal', 0x8007b6e4), ('addiu', 'a3', 'zero', 12),
        ('addiu', 'a0', 'zero', 16), ('addiu', 'a1', 'zero', 20), ('lw', 'a2', 0x18, 'sp'),
        ('jal', 0x8007b580), ('ori', 'a3', 'zero', 0xffff),
        ('lw', 'a0', 0x1c, 'sp'), ('nop',),
        ('jal', MWIDTH), ('nop',),
        ('sll', 'v1', 'v0', 1), ('addu', 'v0', 'v1', 'v0'), ('sll', 'v0', 'v0', 1),
        ('addiu', 'a0', 'zero', 166), ('subu', 'a0', 'a0', 'v0'), ('addiu', 'a1', 'zero', 20),
        ('lw', 'a2', 0x1c, 'sp'),
        ('jal', 0x8007b580), ('ori', 'a3', 'zero', 0xffff),
        ('lw', 'ra', 0x24, 'sp'), ('nop',), ('jr', 'ra'), ('addiu', 'sp', 'sp', 0x28),
    ]),
    # officer pick list (SCREENS['officer list']): ability column i at cell 25 + 3 i (was 0x13 + 4 i);
    # 0x4c(sp) = 3 i, the head x follows from it
    ('MAPPOINT', 0x80149f90, 0x80149fa4, [
        ('sll', 'v0', 's1', 1), ('addu', 'v0', 'v0', 's1'), ('sw', 'v0', 0x4c, 'sp'), ('addiu', 'a1', 'v0', 25),
    ]),
    # ... ability values at x + 206 + 24 i (was x + 0xa2 + 32 i)
    ('MAPPOINT', 0x8014a124, 0x8014a164, [
        ('addu', 'a0', 's2', 'zero'), ('lw', 'a1', 0x34, 'sp'), ('jal', 0x80146c00), ('nop',),
        ('addu', 'a3', 'v0', 'zero'), ('lw', 'a0', 0, 's0'),
        ('sll', 'v1', 's2', 1), ('addu', 'v1', 'v1', 's2'), ('sll', 'v1', 'v1', 3),
        ('addu', 'a0', 'a0', 'v1'), ('addiu', 'a0', 'a0', 206),
        ('lw', 'a1', 0x3c, 'sp'), ('jal', 0x8007b614), ('addiu', 'a2', 'gp', -0x681c),
    ]),
    # ... header cursor on ability column i (1-4): x = 32 (i - 1) + 169, w 30 -> 24 i + 185, w 22
] + [('MAPPOINT', lo, lo + 0x2c, [
        ('sw', 'zero', 0x10, 'sp'), ('lw', 'v0', off, 'sp'), ('addiu', 'at', 'zero', 7), ('sw', 'at', 0x14, 'sp'),
        ('sll', 'at', 'v0', 1), ('addu', 'v0', 'v0', 'at'), ('sll', 'v0', 'v0', 3), ('addiu', 'a0', 'v0', 185),
        ('addiu', 'a1', 'zero', 0x21), ('addiu', 'a2', 'zero', 22), ('addiu', 'a3', 'zero', 0xe),
    ]) for lo, off in ((0x8014a640, 0x34), (0x8014a8e0, 0x3c))] + [
    # ... names through FITNAME (114 px: nothing is cut; 92 px on the skills page)
    ('MAPPOINT', 0x8014a0c4, 0x8014a0cc, [('jal', FITNAME), ('addiu', 'a1', 'zero', 114)]),
    ('MAPPOINT', 0x8014a304, 0x8014a30c, [('jal', FITNAME), ('addiu', 'a1', 'zero', 92)]),
    ('PROG', FITNAME, nameentry.AREA[1], FIT_LINES),
    # 'vassal missions': officer and target of a row
    ('MAPPOINT', 0x80148c30, 0x80148c38, [('jal', FITNAME), ('addiu', 'a1', 'zero', 78)]),
    ('MAPPOINT', 0x80148c94, 0x80148ca4, [
        ('lw', 'a0', 0x30, 'sp'), ('lw', 'a1', 0x34, 'sp'), ('jal', TARGET), ('addiu', 'a2', 'zero', 54)]),
]
# BATTLE field header 0x80122d2c (two 72-px textures: army name, "Men:", "Mor:"): the family without " Army"
# ("Hatakeyama Army" is 88 px); a leaderless army keeps the getter's "Independents". The colour choice before
# the name is rewritten shorter to make room (both sites are the same code).
CODE += [('BATTLE', va, va + 0x60, [
    ('jal', 0x80138d4c), ('addu', 'a0', 's0', 'zero'),
    ('sltiu', 'v0', 'v0', 1), ('addiu', 'a0', 'v0', 1),               # colour 1 / 2
    ('jal', 0x8007a848), ('addu', 'a1', 'zero', 'zero'),
    ('jal', 0x80136710), ('addu', 'a0', 's0', 'zero'),                # leader (0xff = none)
    ('sltiu', 'at', 'v0', 0xe6), ('beqz', 'at', 'full'), ('addu', 'a0', 'v0', 'zero'),
    ('jal', 0x8005df44), ('nop',),                                    # family
    ('b', 'draw'), ('nop',),
    'full:',
    ('jal', 0x80136608), ('addu', 'a0', 's0', 'zero'),
    'draw:',
    ('addu', 'a0', 'zero', 'zero'), ('addu', 'a1', 'zero', 'zero'), ('addiu', 'a2', 'gp', -0x7084),
    ('jal', 0x8007b614), ('addu', 'a3', 'v0', 'zero'),
]) for va in (0x80122ef0, 0x80123018)]
# quantity box (0x8008c874 redraws unit + digits after every change): the unit loses its final "s" while the
# value is 1 ("001 day"). The unit's last byte is swapped for a figure space in place for the draw (a blank as
# wide as a digit: it also wipes the old "s") and put back. Also the colour choice after it, shortened.
CODE.append(('PROG', 0x8008c894, 0x8008c954, [
    ('jal', 0x8008c344), ('nop',), ('addu', 's2', 'v0', 'zero'),          # the value
    ('lw', 'a0', 0x28, 'sp'), ('jal', 0x80086850), ('nop',),              # strlen(unit)
    ('lw', 'a0', 0x28, 'sp'),
    ('sll', 'v1', 'v0', 1), ('addu', 'v1', 'v1', 'v0'), ('sll', 'v1', 'v1', 1),
    ('addu', 's1', 'a0', 'v0'), ('addiu', 's1', 's1', -1),                # s1 -> last byte
    ('lw', 't0', -0x63ac, 'gp'), ('lw', 'a1', -0x63a8, 'gp'), ('addiu', 't0', 't0', 0x78),
    ('subu', 's0', 't0', 'v1'), ('sw', 's0', -0x63a4, 'gp'), ('addiu', 'a1', 'a1', 0x1a),
    ('jal', 0x8007a8b4), ('addu', 'a0', 's0', 'zero'),
    ('lbu', 't1', 0, 's1'), ('addiu', 'at', 'zero', 1),
    ('bne', 's2', 'at', 'plain'), ('addiu', 'at', 'zero', 0xb3),          # "s" (text.enc)
    ('bne', 't1', 'at', 'plain'), ('nop',),
    ('addiu', 'at', 'zero', 0x7f), ('sb', 'at', 0, 's1'),                 # vwf.FIGSP
    'plain:',
    ('lw', 'a0', 0x28, 'sp'), ('jal', 0x8007b4e0), ('ori', 'a1', 'zero', 0xffff),
    ('lbu', 't1', 0, 's1'), ('addiu', 'at', 'zero', 0x7f),
    ('bne', 't1', 'at', 'colour'), ('addiu', 'at', 'zero', 0xb3),
    ('sb', 'at', 0, 's1'),
    'colour:',                                                            # out of range: colour 2, else 8
    ('lw', 'v0', 0x2c, 'sp'), ('lw', 'v1', 0x30, 'sp'), ('sltu', 'at', 's2', 'v0'), ('sltu', 'v0', 'v1', 's2'),
    ('or', 'at', 'at', 'v0'), ('addiu', 'a0', 'zero', 8), ('beqz', 'at', 'set'), ('nop',),
    ('addiu', 'a0', 'zero', 2),
    'set:',
    ('jal', 0x8007a848), ('addu', 'a1', 'zero', 'zero'),
]))
# mission works + its officer pick list (SCREENS 'mission works' / 'mission officers')
CODE += [
    ('PROG', 0x80023e88, 0x80023e90, [('jal', FITNAME), ('addiu', 'a1', 'zero', 90)]),
    ('PROG', 0x800249e4, 0x800249ec, [('jal', FITPAGE), ('nop',)]),
    # ability head boxes: cell 4 i + 18 -> 3 i + 25; head text x 32 i + 164 -> 24 i + 210
    ('PROG', 0x8002485c, 0x8002486c, [('sll', 'v0', 's0', 1), ('addu', 'v0', 'v0', 's0'), ('addiu', 'a1', 'v0', 25)]),
    ('PROG', 0x80024880, 0x800248ac, [
        ('sll', 'v1', 's0', 3), ('sll', 'v0', 's0', 4), ('addu', 'v0', 'v0', 'v1'), ('addiu', 'a0', 'v0', 210),
        ('srl', 'v1', 'v1', 1), ('lui', 'at', 0x800b), ('addu', 'at', 'at', 'v1'), ('lw', 'a2', 0x2628, 'at'),
        ('ori', 'a3', 'zero', 0xffff), ('jal', 0x8007b580), ('addiu', 'a1', 'zero', 0x22)]),
    # ability values of a row: x 32 i + 170 -> 24 i + 217 (the whole loop)
    ('PROG', 0x80024a50, 0x80024aa0, [
        ('addu', 's2', 'zero', 'zero'),
        'loop:',
        ('lw', 'a0', 0x34, 'sp'), ('jal', 0x800531f8), ('addu', 'a1', 's2', 'zero'),
        ('sll', 'v1', 's2', 3), ('sll', 'at', 's2', 4), ('addu', 'v1', 'v1', 'at'), ('addiu', 'a0', 'v1', 217),
        ('lw', 'a1', 0x3c, 'sp'), ('addiu', 'a2', 'gp', -0x7d3c), ('jal', 0x8007b614), ('addiu', 'a3', 'v0', 1),
        ('addiu', 's2', 's2', 1), ('sltiu', 'at', 's2', 4), ('bnez', 'at', 'loop'), ('nop',),
        ('b', 0x80024b10), ('nop',)]),
]
FREE = [('PROG', HDR_NAMES, HDR_NAMES_END)]     # CODE ranges that must be empty (zero) before they are written

# raw bytes (formats that progstr does not own): (image tag, address, old, new)
BYTES = [
    ('PROG', 0x800cf51c, b'%6s\0', b'%s\0\0'),     # castle info words: left-aligned
]


def apply(files, only=None):
    """files: {tag: bytearray} (PROG, BATTLE, MAPPOINT). Returns the number of constants changed."""
    n = 0
    for name, (tag, edits) in SCREENS.items():
        if only and name not in only:
            continue
        b = files[tag]
        for va, old, new in edits:
            o = va - PROG_BASE + PROG_FOFF if tag == 'PROG' else va - OVL_BASE
            w = struct.unpack_from('<I', b, o)[0]
            if w >> 26 not in (0x09, 0x0D) or w & 0xFFFF != old & 0xFFFF:
                raise ValueError('layout %r: %s:%08x is %08x, expected an addiu / ori with %d' % (name, tag, va, w, old))
            struct.pack_into('<I', b, o, (w & 0xFFFF0000) | (new & 0xFFFF))
            n += 1
    # strategy text 0x8005cc48, clan target: "Take %s" (gp-0x7708) -> progstr.NEW 'strategy_clan'
    # (lui a1 at the gp load, addiu a1 in the empty delay slot of the sprintf call)
    import progstr
    va = progstr.ADDR.get('NEW:strategy_clan')
    late = [] if va is None else [
        ('PROG', 0x8005cd1c, 0x278588f8, 0x3c050000 | ((va + 0x8000) >> 16 & 0xFFFF)),
        ('PROG', 0x8005cd28, 0, 0x24a50000 | (va & 0xFFFF))]
    va = progstr.ADDR.get('NEW:music_help')       # Music Player help text: lui / addiu a1 at 0x8002105c
    if va is not None:
        late += [('PROG', 0x8002105c, 0x3c05800b, 0x3c050000 | ((va + 0x8000) >> 16 & 0xFFFF)),
                 ('PROG', 0x80021060, 0x24a51848, 0x24a50000 | (va & 0xFFFF))]
    raw = BYTES + [(t, a, struct.pack('<I', o), struct.pack('<I', w)) for t, a, o, w in WORDS + late]
    for tag, va, old, new in raw:
        b = files[tag]
        o = va - PROG_BASE + PROG_FOFF if tag == 'PROG' else va - OVL_BASE
        if bytes(b[o:o + len(old)]) != old or len(new) != len(old):
            raise ValueError('layout bytes: %s:%08x is %r' % (tag, va, bytes(b[o:o + len(old)])))
        b[o:o + len(new)] = new
    # council 0 @214 "{p00}: I leave your castles to each of you" (MAPPOINT 0x8010a97c): the given names of
    # every castle lord at the council are joined in a 100-byte stack buffer (sp+0x1ec; ids at sp+0x20,
    # count s2). English names fill it with 9 lords (the Japanese with 10-16), and 9 names are also all the
    # window holds: more than 8 lords -> progstr.NEW 'all_lords'. The loop is rewritten in place.
    code = list(CODE)
    va = progstr.ADDR.get('NEW:all_lords')
    if va is not None:
        code.append(('MAPPOINT', 0x8010aa4c, 0x8010aab4, [
            ('sltiu', 'at', 's2', 9), ('bnez', 'at', 'cond'), ('addu', 's0', 'zero', 'zero'),
            ('addiu', 'a0', 'sp', 0x1ec), ('lui', 'a1', (va + 0x8000) >> 16 & 0xFFFF),
            ('jal', 0x800868b4), ('addiu', 'a1', 'a1', (va & 0xFFFF) - (0x10000 if va & 0x8000 else 0)),
            ('b', 'end'), ('nop',),
            'loop:',
            ('sll', 'v0', 's0', 1), ('addu', 'v0', 'sp', 'v0'), ('jal', 0x8005e034), ('lhu', 'a0', 0x20, 'v0'),
            ('addiu', 'a0', 'sp', 0x1ec), ('jal', 0x80086a3c), ('addu', 'a1', 'v0', 'zero'),
            ('addiu', 'v0', 's2', -1), ('beq', 's0', 'v0', 'skip'), ('nop',),
            ('addiu', 'a0', 'sp', 0x1ec), ('jal', 0x80086a3c), ('addiu', 'a1', 'gp', -0x6ba0),
            'skip:',
            ('addiu', 's0', 's0', 1),
            'cond:',
            ('sltu', 'at', 's0', 's2'), ('bnez', 'at', 'loop'), ('nop',),
            'end:',
        ]))
    for tag, lo, hi, lines in code:
        c = asm.assemble(lo, lines)
        assert len(c) <= hi - lo, 'layout code %08x: %d bytes over' % (lo, len(c) - (hi - lo))
        o = lo - PROG_BASE + PROG_FOFF if tag == 'PROG' else lo - OVL_BASE
        assert (tag, lo, hi) not in FREE or not any(files[tag][o:o + hi - lo]), 'layout code %08x: not free' % lo
        files[tag][o:o + hi - lo] = c.ljust(hi - lo, b'\0')
    return n
