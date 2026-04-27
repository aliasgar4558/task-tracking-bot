#!/usr/bin/env python3
"""Desktop window for the Daily Task Logger (tkinter).

This file stays for backwards compatibility.
Prefer installing and using `taskbot-gui`.
"""

from __future__ import annotations

from taskbot.gui import main as gui_main


def main() -> None:
    gui_main()


if __name__ == "__main__":
    main()
