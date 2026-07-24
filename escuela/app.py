"""Escuela - app unificada de Book It Escuelas (un solo comando).

Un solo login, un solo servidor local, y una barra lateral en el HTML para
ir y volver entre Menu / Insertar / Editar sin reiniciar nada. El modo
--dry-run ya no es un flag de terminal: es un interruptor visible en cada
pantalla, ENCENDIDO por defecto (seguro: no guarda nada real hasta que lo
apagues a proposito).

Uso:
    python3 escuela/app.py
"""

import sys
import threading
import webbrowser
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from playwright.sync_api import sync_playwright

from autenticacion.login import iniciar_sesion
from escuela.consultar.consultar import escanear_catalogo, escanear_catalogo_rapido, scrape_form
from escuela.campos import nombres_solo_edit
from escuela.guardar.guardar import guardar_form
from escuela.navegador import abrir_landing
from escuela.ui.reglas import aplicar_defaults_insertar, config_js
from escuela.ui.render import render_campos_html, render_editar, render_insertar, render_menu
from escuela.ui.servidor import ServidorEscuela


def main():
    print("=" * 55)
    print("   ESCUELA - Book It (menu unificado)")
    print("=" * 55)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        page = browser.new_page()

        iniciar_sesion(page)

        print()
        print("[+] Leyendo catalogos (colegios, formulario de alta)...")
        colegios = abrir_landing(page)
        datos_alta = scrape_form(page, "0")
        datos_alta["valores"] = aplicar_defaults_insertar(datos_alta["valores"])
        print(f"    {len(colegios)} colegios disponibles")

        print("[+] Escaneando escuelas existentes (para avisar de duplicados)...")
        try:
            catalogo = escanear_catalogo_rapido(page, colegios)
            print(f"    Catalogo listo ({len(catalogo)} escuelas, lectura en paralelo).")
        except Exception as exc:
            print(f"    [!] Lectura rapida fallo ({exc}). Usando Playwright lento...")
            catalogo = escanear_catalogo(page, colegios)
            print(f"    Catalogo listo ({len(catalogo)} escuelas).")
        cfg = config_js()

        def on_cargar(payload):
            id_escuela = payload.get("idEscuela")
            if not id_escuela:
                return {"ok": False, "error": "idEscuela vacio"}
            datos = scrape_form(page, id_escuela)
            campos_html = render_campos_html(
                "editar", datos["valores"], datos["opciones"], datos.get("bloqueados")
            )
            return {"ok": True, "html": campos_html, "valores": datos["valores"]}

        def on_enviar(payload):
            id_escuela = payload.get("idEscuela", "0")
            valores = payload.get("valores", {})
            # El modo prueba se controla desde el interruptor del HTML, no
            # desde un flag de terminal. Por defecto (si el front no lo manda
            # por alguna razon) se asume dry_run=True: mas vale de mas que
            # arriesgar un guardado real accidental.
            dry_run = payload.get("dryRun", True)
            res = guardar_form(page, id_escuela, valores, dry_run=dry_run)
            # Tras un ALTA real (no dry_run, idEscuela=="0"), el sistema
            # devuelve al landing con la nueva escuela ya en el selector.
            # La detectamos por diferencia vs el catalogo que teniamos y se
            # la devolvemos al front como nuevo_id, para que redirija a
            # Editar y el usuario complete los campos solo-edicion sin tener
            # que ir a Editar y elegirla a mano.
            if res.get("ok") and not dry_run and str(id_escuela) == "0":
                try:
                    colegios2 = abrir_landing(page)
                    ids_previos = {str(e["id"]) for e in catalogo}
                    nuevo = next((c for c in colegios2 if str(c[0]) not in ids_previos), None)
                    if nuevo:
                        res["nuevo_id"] = str(nuevo[0])
                        res["nuevo_texto"] = nuevo[1]
                        print(f"    [+] Alta exitosa -> nueva escuela id={nuevo[0]} ({nuevo[1]})")
                        # Re-renderizar /editar con la lista actualizada de
                        # colegios para que el selector incluya la escuela
                        # nueva. Sin esto, el redirect a /editar?nuevo=<id>
                        # serviria un HTML pre-renderizado sin la escuela nueva
                        # en el <select> y el auto-load nunca dispararia.
                        paginas["/editar"] = render_editar(colegios2, catalogo, cfg)
                        # Paso 2 automatico: abrir el form de EDICION de la
                        # escuela recien creada y setear SOLO los campos
                        # solo-edicion (celular, repa, etc.) con los valores
                        # que el usuario elegio en el form de Insertar. El
                        # sistema real no acepta esos campos al Registrar, asi
                        # que van en una segunda pasada. Si todos esos valores
                        # vienen vacios/default, se omite el paso 2.
                        valores_solo_edit = {
                            k: v for k, v in valores.items()
                            if k in set(nombres_solo_edit())
                        }
                        hay_algo = any(v not in (None, "", False, "0") for v in valores_solo_edit.values())
                        if hay_algo:
                            print(f"    [+] Paso 2: aplicando opciones adicionales a la escuela nueva...")
                            res2 = guardar_form(page, str(nuevo[0]), valores_solo_edit, dry_run=False)
                            if not res2.get("ok"):
                                res["paso2_error"] = res2.get("error", "error desconocido")
                                print(f"    [!] Paso 2 fallo: {res.get('paso2_error')}")
                            else:
                                print(f"    [+] Paso 2 OK: opciones adicionales aplicadas.")
                        else:
                            print(f"    [+] Paso 2 omitido (opciones adicionales vacias).")
                    else:
                        print(f"    [!] No se detecto una escuela nueva en el landing.")
                except Exception as exc:
                    print(f"    [!] No se pudo detectar la nueva escuela: {exc}")
                    import traceback
                    traceback.print_exc()
            return res

        paginas = {
            "/": render_menu(),
            "/insertar": render_insertar(datos_alta, catalogo, cfg),
            "/editar": render_editar(colegios, catalogo, cfg),
        }
        servidor = ServidorEscuela(paginas, on_cargar=on_cargar, on_enviar=on_enviar)
        puerto = servidor.iniciar()
        url = f"http://127.0.0.1:{puerto}/"
        print(f"[+] Listo -> {url}")
        webbrowser.open(url)

        salir = threading.Event()

        def esperar_enter():
            input()
            salir.set()

        print()
        print("=> Usa el menu del HTML para ir y volver entre Insertar y Editar.")
        print("=> El interruptor de 'modo prueba' esta en cada pantalla (encendido = seguro).")
        print("=> Cuando termines, regresa aqui y presiona Enter para cerrar todo.")
        threading.Thread(target=esperar_enter, daemon=True).start()

        while not salir.is_set():
            servidor.procesar_pendientes()

        servidor.detener()
        browser.close()
        print("Fin.")


if __name__ == "__main__":
    main()
