import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from playwright.sync_api import sync_playwright
import config
from autenticacion.login import iniciar_sesion


BOOKIT_ESCUELAS_URL = config.BASE_URL + "/Secciones/Book_It/bookit"


def main():
    print("=" * 55)
    print("   NAVEGACION - Book It Escuelas")
    print("=" * 55)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1500)
        page = browser.new_page()

        iniciar_sesion(page)

        print()
        print("[5/5] Navegando a Book It Escuelas...")
        print(f"     -> {BOOKIT_ESCUELAS_URL}")
        page.goto(BOOKIT_ESCUELAS_URL, wait_until="domcontentloaded")
        # Nota: "text=Book It Escuelas" hace match con 2 elementos (el link
        # oculto del menu lateral y el <h2> del titulo de la pagina). Se usa
        # el h2 explicitamente para evitar esperar por el elemento oculto.
        page.wait_for_selector("h2.page-title", timeout=15000)
        print(f"[+] En Book It Escuelas -> {page.url}")

        print()
        print("=> Navegador abierto. Presiona Enter para cerrar.")
        input()

        browser.close()
        print("Fin.")


if __name__ == "__main__":
    main()
