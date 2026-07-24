import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from playwright.sync_api import sync_playwright
import config


def iniciar_sesion(page):
    """Realiza el login en el navegador abierto.
    Lanza RuntimeError si las credenciales son rechazadas.
    """
    print("[1/4] Abriendo pagina de login...")
    print(f"     -> {config.BASE_URL}")
    page.goto(config.BASE_URL)

    print("[2/4] Escribiendo correo electronico...")
    page.locator("input[name='email']").fill(config.EMAIL)

    print("[3/4] Escribiendo contrasena...")
    page.locator("input[name='password']").fill(config.PASSWORD)

    print("[4/4] Enviando formulario...")
    page.locator("#IS").click()
    page.wait_for_load_state("networkidle", timeout=15000)

    if "login.php" in page.url:
        raise RuntimeError("Login fallo: credenciales rechazadas.")

    print(f"[+] Login exitoso -> {page.url}")
    return page


if __name__ == "__main__":
    print("=" * 55)
    print("   LOGIN - Prueba independiente")
    print("=" * 55)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1500)
        page = browser.new_page()
        iniciar_sesion(page)
        print("\n=> Navegador abierto. Presiona Enter para cerrar.")
        input()
        browser.close()
        print("Fin.")