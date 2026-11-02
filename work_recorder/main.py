import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Silenciar avisos benignos de symlinks de Hugging Face en Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# Asegurar que tanto la raíz del proyecto como work_recorder estén en sys.path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Cargar variables de entorno (.env de la raíz y local si existiera)
load_dotenv(project_root / ".env")
load_dotenv(current_dir / ".env")

from work_recorder.ui.app import WorkRecorderApp


def main():
    app = WorkRecorderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
