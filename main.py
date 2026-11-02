import os
import sys
import ctypes

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
from ui.app import App


def main():
    # Mejorar la nitidez en pantallas de alta resolución en Windows
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
