"""
Robert Henning's, Python Print-Utils (Proudly R6b), 2026
PrintUtils.py

Utilities for CLI rendering using ANSI escape sequences.

This module provides:
- Progress bar rendering (Outdated)
- Line clearing utilities
- Structured printing for dict and list
- Structured string for dict and list
- Other utilities
- An full menu
- Visual Debugging (undocumented)

Compatibility:
- Requires ANSI-compatible terminal (Linux, macOS, modern Windows)
- 24 Bit color mode
- UTF-8

Author: Robert Henning
Licence : MIT, 2026
Repos : https://github.com/AndrewReed-17/RHs_PyPrintUtils
"""

from __future__ import annotations

import sys
import time
import os
import shutil
from typing import Any, Dict, List


__all__ = [
    "menu_mk_i",
    "get_terminal_size",
    "replace_with_void",
    "clear_progressbar",
    "progressbar",
    "clear_cli",
    "print_dict",
    "print_list",
]

# ---------------------------------------------------------------------------
# ANSI Coded G-UI
# ---------------------------------------------------------------------------

def menu_mk_i(
    tpl_terminal_size: tuple,
    str_title: str,
    dict_options: dict,
    str_message: str = "",
    int_select: bool = False
) -> list[str] | str | None:
    """
    ANSI terminal menu.

    - SPACE toggles selection / deselection
    - ENTER validates
    - Q or ESC quits
    - Help is wrapped
    - Footer is kept on its own line
    """
    import os
    import sys
    import textwrap

    if not dict_options:
        return None

    # --------------------------------------------------
    # Terminal size
    # --------------------------------------------------
    if tpl_terminal_size is None:
        int_cols, int_rows = get_terminal_size()
    else:
        int_cols, int_rows = tpl_terminal_size

    lst_options = list(dict_options.items())
    int_count = len(lst_options)

    # --------------------------------------------------
    # ANSI helpers
    # --------------------------------------------------
    def _move(x: int, y: int) -> None:
        sys.stdout.write(f"\033[{y};{x}H")

    def _hide_cursor() -> None:
        sys.stdout.write("\033[?25l")

    def _show_cursor() -> None:
        sys.stdout.write("\033[?25h")

    def _reverse_on() -> None:
        sys.stdout.write("\033[7m")

    def _reverse_off() -> None:
        sys.stdout.write("\033[0m")

    def _box(x: int, y: int, w: int, h: int) -> None:
        if w < 4 or h < 3:
            return

        _move(x, y)
        sys.stdout.write("┌" + "─" * (w - 2) + "┐")
        for i in range(1, h - 1):
            _move(x, y + i)
            sys.stdout.write("│" + " " * (w - 2) + "│")
        _move(x, y + h - 1)
        sys.stdout.write("└" + "─" * (w - 2) + "┘")

    def _cleanup_exit() -> None:
        _show_cursor()
        sys.stdout.write("\033[0m")
        clear_cli()
        sys.stdout.flush()

    # --------------------------------------------------
    # Key reading
    # --------------------------------------------------
    if os.name == "nt":
        import msvcrt

        def _read_key() -> str | None:
            c = msvcrt.getwch()

            if c in ("\r", "\n"):
                return "ENTER"
            if c == " ":
                return "SPACE"
            if c in ("q", "Q"):
                return "QUIT"
            if c == "\x1b":
                return "ESC"

            if c in ("\x00", "\xe0"):
                c2 = msvcrt.getwch()
                return {
                    "H": "UP",
                    "P": "DOWN",
                    "I": "PAGE_UP",
                    "Q": "PAGE_DOWN",
                }.get(c2, None)

            return None

    else:
        import termios
        import tty

        def _read_key() -> str | None:
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)

            try:
                tty.setraw(fd)
                c = sys.stdin.read(1)

                if c in ("\r", "\n"):
                    return "ENTER"
                if c == " ":
                    return "SPACE"
                if c in ("q", "Q"):
                    return "QUIT"
                if c == "\x1b":
                    c2 = sys.stdin.read(1)

                    if c2 != "[":
                        return "ESC"

                    c3 = sys.stdin.read(1)

                    if c3 == "A":
                        return "UP"
                    if c3 == "B":
                        return "DOWN"
                    if c3 == "5":
                        sys.stdin.read(1)
                        return "PAGE_UP"
                    if c3 == "6":
                        sys.stdin.read(1)
                        return "PAGE_DOWN"

                    return None

                return None

            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

    # --------------------------------------------------
    # Layout helpers
    # --------------------------------------------------
    def _help_lines() -> list[str]:
        help_line = (
            "SPACE=Select/Deselect   ENTER=Validate   "
            "↑↓=Move   PgUp/PgDn=Page   Q=Quit"
        )
        return textwrap.wrap(help_line, width=max(10, int_cols - 4))

    def _message_lines() -> list[str]:
        if not str_message.strip():
            return []
        return textwrap.wrap(str_message, width=max(10, int_cols - 4))

    def _layout_top_rows() -> tuple[int, int, int]:
        """
        Returns:
            (help_end_row, list_start_row, footer_row)
        """
        footer_row = int_rows

        help_start_row = 6
        hl = _help_lines()
        ml = _message_lines()

        row = help_start_row + len(hl)

        # Reserve the message block only on page 1, but keep layout stable
        if ml:
            row += len(ml) + 1  # +1 blank line after message

        row += 1  # separator row

        list_start_row = row
        return help_start_row, list_start_row, footer_row

    help_start_row, list_start_row, footer_row = _layout_top_rows()
    int_available_rows = max(1, footer_row - list_start_row)

    def _page_count() -> int:
        return max(1, (int_count + int_available_rows - 1) // int_available_rows)

    def _page_slice(page: int) -> tuple[int, int]:
        start = page * int_available_rows
        end = min(int_count, start + int_available_rows)
        return start, end

    # --------------------------------------------------
    # Rendering
    # --------------------------------------------------
    def _render(page: int, current_index: int, selected: set[int]) -> None:
        clear_cli()
        _hide_cursor()

        pcount = _page_count()
        page = max(0, min(page, pcount - 1))
        start, end = _page_slice(page)

        # Title box centered
        title_box_w = min(int_cols - 4, max(len(str_title) + 8, 24))
        title_box_w = max(24, title_box_w)
        title_box_x = max(1, (int_cols - title_box_w) // 2 + 1)

        _box(title_box_x, 2, title_box_w, 3)

        clipped_title = str_title[: max(0, title_box_w - 4)]
        title_x = title_box_x + max(2, (title_box_w - len(clipped_title)) // 2)
        _move(title_x, 3)
        sys.stdout.write(clipped_title)

        # Wrapped help
        row = help_start_row
        for line in _help_lines():
            _move(2, row)
            sys.stdout.write(line[: max(0, int_cols - 4)])
            row += 1

        # Message only on first page, but the layout space is already reserved
        if str_message.strip():
            row += 1
            for line in _message_lines():
                _move(2, row)
                sys.stdout.write(line[: max(0, int_cols - 4)])
                row += 1

        # Separator just before list
        _move(1, list_start_row - 1)
        sys.stdout.write("─" * max(0, int_cols - 1))

        # Options, never beyond footer row
        for i in range(start, end):
            label, _ = lst_options[i]
            mark = "■" if i in selected else " "
            txt = f"[{mark}] {label}"[: max(0, int_cols - 4)]

            y = list_start_row + (i - start)
            if y >= footer_row:
                break

            _move(2, y)
            if i == current_index:
                _reverse_on()
                sys.stdout.write(txt)
                _reverse_off()
            else:
                sys.stdout.write(txt)

        # Footer on its own line
        footer = f"Page {page + 1}/{pcount}"
        _move(2, footer_row)
        sys.stdout.write(" " * max(0, int_cols - 3))
        _move(2, footer_row)
        sys.stdout.write(footer[: max(0, int_cols - 4)])

        sys.stdout.flush()

    # --------------------------------------------------
    # Main loop
    # --------------------------------------------------
    page = 0
    current_index = 0
    selected: set[int] = set()

    try:
        while True:
            _render(page, current_index, selected)
            key = _read_key()

            pcount = _page_count()

            if key in ("ESC", "QUIT"):
                _cleanup_exit()
                return "QUIT"

            elif key == "UP":
                current_index -= 1
                if current_index < 0:
                    current_index = int_count - 1
                page = current_index // int_available_rows

            elif key == "DOWN":
                current_index += 1
                if current_index >= int_count:
                    current_index = 0
                page = current_index // int_available_rows

            elif key == "PAGE_UP":
                page = max(0, page - 1)
                current_index = page * int_available_rows

            elif key == "PAGE_DOWN":
                page = min(pcount - 1, page + 1)
                current_index = page * int_available_rows

            elif key == "SPACE":
                if current_index in selected:
                    selected.remove(current_index)
                else:
                    if not int_select:
                        selected.clear()
                    selected.add(current_index)

            elif key == "ENTER":
                if int_select:
                    chosen_indices = sorted(selected)
                    chosen_labels = [lst_options[i][0] for i in chosen_indices]

                    for i in chosen_indices:
                        _, func = lst_options[i]
                        if callable(func):
                            func()

                    _cleanup_exit()
                    return chosen_labels

                chosen_index = current_index
                if chosen_index not in range(int_count):
                    chosen_index = 0

                label, func = lst_options[chosen_index]
                if callable(func):
                    func()

                _cleanup_exit()
                return label

    finally:
        _show_cursor()
        sys.stdout.write("\033[0m")
        sys.stdout.flush()
        clear_cli()

def deg_place_24b_color(tpl_terminal_size: tuple) -> None:
    cols, rows = tpl_terminal_size
    import colorsys

    for int_rows in range(rows):
        line = ""
        for int_cols in range(cols):
            t = (int_cols + int_rows) / (cols + rows - 2)

            # HSV hue sweep
            R, G, B = colorsys.hsv_to_rgb(t, 1, 1)
            R = int(R * 255)
            G = int(G * 255)
            B = int(B * 255)

            line += f"\033[48;2;{R};{G};{B}m \033[0m"
        print(line)

    return


def deg_place_8b_color(tpl_terminal_size: tuple) -> None:
    cols, rows = tpl_terminal_size

    for int_rows in range(rows):
        line = ""
        for int_cols in range(cols):
            # Normalized diagonal gradient position (0 → 1)
            t = (int_cols + int_rows) / (cols + rows - 2)

            # Map t to a hue in the 8-bit color cube (16–231)
            # 216 colors arranged as a 6×6×6 RGB cube
            hue_index = int(t * 215) + 16

            line += f"\033[48;5;{hue_index}m \033[0m"
        print(line)

    return

def deg_place_4b_color(tpl_terminal_size:tuple) -> None :
    bg_colors = [40, 41, 42, 43, 44, 45, 46, 47]

    for int_rows in range(0, tpl_terminal_size[1]-1, 1) :
        line = ""
        for int_cols in range(0, tpl_terminal_size[0]-1, 1) :
            t = (int_cols + int_rows) / (tpl_terminal_size[1] + tpl_terminal_size[0] -2)
            idx = int(t * (len(bg_colors)-1))
            color = bg_colors[idx]
            line += f"\033[{color}m \033[0m"
        print(line)

    return

def deg_place_corner(terminal_size:tuple) -> None :
    default_pos = 0
    print(f"\033[{default_pos};{default_pos}HT-L") #Top Left
    print(f"\033[{default_pos};{terminal_size[0]}HR") #Top Right
    print(f"\033[{terminal_size[1]-1};{default_pos}HB-L") #Bottom Left
    print(f"\033[{terminal_size[1]-1};{terminal_size[0]}HR") #Bottom Right
    return

# ---------------------------------------------------------------------------
# Core ANSI utilities
# ---------------------------------------------------------------------------

def get_terminal_size() -> tuple :
    """
    Maid by R. H.
    Date : 2026-06-18T14:35
    Updated : 2026-06-18T14:35

    Maid with IA : No
    Assisted by IA : No

    Credit : granitosaurus, https://www.reddit.com/r/Python/comments/5q7b36/getting_terminal_size_in_python/

    Returns:
        tuple: Colums by Width
    """
    for fd in (1, 2, 0):
        try:
            size = os.get_terminal_size(fd)
            return size.columns, size.lines
        except OSError:
            pass
    # fallback
    return 80, 24


COLS = get_terminal_size()[0]

def replace_with_void(lines: int) -> None:
    """
    Clear the last `lines` lines from the terminal.

    Parameters
    ----------
    lines : int
        Number of lines to erase above the current cursor position.

    Notes
    -----
    Uses ANSI escape sequences:
    - \\033[F : move cursor up
    - \\033[2K : clear line
    - \\033[E : move cursor down
    """
    if lines <= 0:
        return

    sys.stdout.write("\033[F" * lines)

    for _ in range(lines):
        sys.stdout.write("\033[2K")
        sys.stdout.write("\033[E")

    sys.stdout.write("\033[F" * lines)
    sys.stdout.flush()


def clear_progressbar(lines: int = 3) -> None:
    """
    Clear a previously printed progress bar block.

    Parameters
    ----------
    lines : int, optional
        Number of lines used by the progress bar (default is 3).
    """
    for _ in range(lines):
        sys.stdout.write("\033[2K\033[E")

    sys.stdout.write("\033[F" * lines)
    sys.stdout.flush()


def clear_cli() -> None:
    """
    Clear the entire terminal screen and reset cursor position.
    """
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Progress bar
# ---------------------------------------------------------------------------

def progressbar(max_value: int, value: int, start_time: float) -> None:
    """
    Render a 3-line progress bar in-place.

    Parameters
    ----------
    max_value : int
        Total expected value (completion target).
    value : int
        Current progress value.
    start_time : float
        Timestamp (from time.time()) marking the start.

    Behavior
    --------
    Displays:
    - Spinner
    - Percentage
    - Progress bar
    - Speed (units/sec)
    - ETA (seconds)

    Notes
    -----
    This function overwrites previous output using ANSI cursor movement.
    """

    if max_value <= 0:
        raise ValueError("max_value must be > 0")

    spinner = ("|", "/", "-", "\\")
    bar_length = 20

    # Move cursor to beginning of block
    sys.stdout.write("\033[F" * 3)

    percent = int((value / max_value) * 100)
    spin = spinner[value % len(spinner)]

    filled = int(bar_length * percent / 100)
    bar = "=" * filled + "-" * (bar_length - filled)

    elapsed = time.time() - start_time
    speed = value / elapsed if elapsed > 0 else 0.0
    eta = (max_value - value) / speed if speed > 0 else 0.0

    print(f" $ Operating {spin}")
    print(f"  - {percent:02d}% [{bar}]")
    print(f"  - Speed : {speed:.2f}/s, ETA : {int(eta):02d}s")

    sys.stdout.write("\033[F" * 3)


# ---------------------------------------------------------------------------
# Structured printing
# ---------------------------------------------------------------------------

def print_dict(data: Dict[Any, Any], index = -1, limit: int = COLS) -> None:
    """
    Pretty-print a dictionary or a sub-dictionary.

    Parameters
    ----------
    data : dict
        Dictionary to display.
    index : any, optional
        If not -1, attempts to access data[index].
    limit : int, optional
        Maximum line width before truncation.

    Notes
    -----
    Empty values are replaced with '!ERR_NO_VALUE!'.
    """

    target = data if index == -1 else data.get(index, {})

    processed = {
        str(k): (v if str(v) else "!ERR_NO_VALUE!")
        for k, v in target.items()
    }

    max_key_len = max((len(k) for k in processed), default=0)

    for key, value in processed.items():
        line = f"  - {key:<{max_key_len}} | {value}"

        if len(line) > limit:
            line = line[: limit - 3] + "..."

        print(line)


def print_list(data: List[Any], index: int = -1, limit: int = COLS) -> None:
    """
    Pretty-print a list or a nested list.

    Parameters
    ----------
    data : list
        List to display.
    index : int, optional
        If not -1, prints data[index] assuming nested structure.
    limit : int, optional
        Maximum line width before truncation.
    """

    target = data if index == -1 else data[index]

    for element in target:

        line = "  - " + str(element)

        if len(line) > limit:
            line = line[: limit - 3] + "..."

        print(line)

# ---------------------------------------------------------------------------
# Structured string
# ---------------------------------------------------------------------------

def string_dict(data: Dict[Any, Any], index = -1, limit: int = COLS) -> str:
    """
    Pretty-print a dictionary or a sub-dictionary.

    Parameters
    ----------
    data : dict
        Dictionary to display.
    index : any, optional
        If not -1, attempts to access data[index].
    limit : int, optional
        Maximum line width before truncation.

    Notes
    -----
    Empty values are replaced with '!ERR_NO_VALUE!'.
    """
    string = ""

    target = data if index == -1 else data.get(index, {})

    processed = {
        str(k): (v if str(v) else "!ERR_NO_VALUE!")
        for k, v in target.items()
    }

    max_key_len = max((len(k) for k in processed), default=0)

    for key, value in processed.items():
        line = f"  - {key:<{max_key_len}} | {value}"

        if len(line) > limit:
            line = line[: limit - 3] + "..."

        string = string + line + "\n"
    return string

def string_list(data: List[Any], index: int = -1, limit: int = COLS) -> str:
    """
    Pretty-print a list or a nested list.

    Parameters
    ----------
    data : list
        List to display.
    index : int, optional
        If not -1, prints data[index] assuming nested structure.
    limit : int, optional
        Maximum line width before truncation.
    """

    string = ""

    target = data if index == -1 else data[index]

    for element in target:

        line = "  - " + str(element)

        if len(line) > limit:
            line = line[: limit - 3] + "..."

        string = string + line + "\n"
    return string
