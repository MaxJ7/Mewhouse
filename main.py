#!/usr/bin/env python3
"""
Mewhouse — Mewgenics Room Layout Optimizer
==========================================
Entry point. Launches the GUI application.

Usage:
    python main.py
"""

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)


def main() -> None:
    try:
        import tkinter  # noqa: F401
    except ImportError:
        print(
            "ERROR: tkinter is not installed.\n"
            "On Debian/Ubuntu: sudo apt-get install python3-tk\n"
            "On Fedora:        sudo dnf install python3-tkinter",
            file=sys.stderr,
        )
        sys.exit(1)

    from src.gui.app import MewhouseApp
    app = MewhouseApp()
    app.mainloop()


if __name__ == "__main__":
    main()
