import ctypes
from ctypes import wintypes
from typing import List, Dict, Optional, Any

user32 = ctypes.windll.user32

# Tipos de funciones Win32
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def list_visible_windows() -> List[Dict[str, Any]]:
    """
    Enumera todas las ventanas visibles de primer nivel en el escritorio del usuario.
    Devuelve una lista de diccionarios: [{'hwnd': int, 'title': str}, ...]
    """
    windows: List[Dict[str, Any]] = []

    # Títulos típicos de ventanas del sistema o de fondo que no son aplicaciones de usuario
    ignored_titles = {
        "program manager",
        "settings",
        "configuración",
        "default ime",
        "msctfime ui",
        "windows input experience",
        "task view",
    }

    def enum_callback(hwnd: wintypes.HWND, lparam: wintypes.LPARAM) -> bool:
        # Verificar si la ventana está marcada como visible
        if not user32.IsWindowVisible(hwnd):
            return True

        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True

        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()

        if not title:
            return True

        # Ignorar ventanas comunes del sistema operativo
        if title.lower() in ignored_titles:
            return True

        # Verificar que no sea una ventana de tamaño cero (invisibles o de fondo)
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        if width <= 50 or height <= 50:
            return True

        windows.append({"hwnd": int(hwnd), "title": title})
        return True

    cb = WNDENUMPROC(enum_callback)
    user32.EnumWindows(cb, 0)

    # Ordenar alfabéticamente por título
    windows.sort(key=lambda w: w["title"].lower())
    return windows


def find_window_by_partial_title(partial_query: str) -> Optional[Dict[str, Any]]:
    """
    Busca la primera ventana visible cuyo título contenga 'partial_query' (case-insensitive).
    """
    if not partial_query:
        return None

    query = partial_query.strip().lower()
    for win in list_visible_windows():
        if query in win["title"].lower():
            return win

    return None
