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
import json
import time
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
from escuela.ui.render import render_campos_html, render_editar, render_historial, render_insertar, render_menu
from escuela.ui.servidor import ServidorEscuela


# ---------------------------------------------------------------------------
# Historial en archivos planos (TXT/JSON) - NO base de datos.
# Carpeta `historial/` (gitignored, local por maquina):
#   - acciones.log: append de cada alta/edicion (auditoria, legible)
#   - recientes.json: ultimas 20 escuelas tocadas (para selector rapido)
#   - borradores/<id>.json: borrador del formumping en curso, auto-save.
# Permite al usuario "jal back": restaurar datos de una alta/edicion anterior.
# ---------------------------------------------------------------------------
_HIST_DIR = _PROJECT_ROOT / "historial"
_BORR_DIR = _HIST_DIR / "borradores"


def _asegurar_hist_dirs():
    _HIST_DIR.mkdir(exist_ok=True)
    _BORR_DIR.mkdir(exist_ok=True)


def _leer_json(ruta, default):
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _escribir_json(ruta, data):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def registrar_accion(accion, id_escuela, nombre, valores, extra=""):
    """Appendiza una linea al log TXT. Legible por humano."""
    _asegurar_hist_dirs()
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{ts}] {accion} | id={id_escuela} | {nombre}"
    if extra:
        linea += f" | {extra}"
    linea += "\n"
    with open(_HIST_DIR / "acciones.log", "a", encoding="utf-8") as f:
        f.write(linea)
    # Tambien guardar snapshot completo en JSON para "jal back"
    snap = {
        "ts": ts,
        "accion": accion,
        "id": str(id_escuela),
        "nombre": nombre,
        "valores": valores,
        "extra": extra,
    }
    snaps = _leer_json(_HIST_DIR / "snapshots.json", [])
    snaps.append(snap)
    # Limitar a 50 snapshots para no crecer indefinidamente
    snaps = snaps[-50:]
    _escribir_json(_HIST_DIR / "snapshots.json", snaps)


def registrar_reciente(id_escuela, nombre):
    """Mantiene lista de ultimas 20 escuelas tocadas."""
    _asegurar_hist_dirs()
    recientes = _leer_json(_HIST_DIR / "recientes.json", [])
    # Quitar si ya estaba (para mover al final)
    recientes = [r for r in recientes if str(r.get("id")) != str(id_escuela)]
    recientes.append({"id": str(id_escuela), "nombre": nombre, "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
    recientes = recientes[-20:]
    _escribir_json(_HIST_DIR / "recientes.json", recientes)


def guardar_borrador(clave, valores):
    """Guarda el borrador del formulario en curso. `clave` es
    'insertar' o 'editar:<id_escuela>'."""
    _asegurar_hist_dirs()
    _escribir_json(_BORR_DIR / f"{_sanitizar_clave(clave)}.json", {
        "valores": valores,
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
    })


def cargar_borrador(clave):
    """Lee el borrador guardado para `clave`. Devuelve {valores, ts} o None."""
    _asegurar_hist_dirs()
    ruta = _BORR_DIR / f"{_sanitizar_clave(clave)}.json"
    return _leer_json(ruta, None)


def _sanitizar_clave(clave):
    # caracteres seguros para nombre de archivo
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in clave)


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
            # Cargar nombre Escuela para el log (en Insertar es el valor del
            # campo "nombre"; en Editar el texto del selector).
            nombre_escuela = valores.get("nombre", "") if str(id_escuela) == "0" else ""
            if not nombre_escuela and str(id_escuela) != "0":
                sel = page.locator("select[name='idEscuela'] option[value='" + str(id_escuela) + "']").first
                try:
                    nombre_escuela = sel.inner_text() if sel.count() else str(id_escuela)
                except Exception:
                    nombre_escuela = str(id_escuela)
            res = guardar_form(page, id_escuela, valores, dry_run=dry_run)
            # ---- Registro en historial (TXT + JSON) ----
            # Dry-run tambien se registra (es una "practica"); real ζω ́ηζει mas info.
            if res.get("ok"):
                accion = "alta-practica" if (dry_run and str(id_escuela) == "0") else (
                    "alta-real" if str(id_escuela) == "0" else (
                        "edicion-practica" if dry_run else "edicion-real"
                    )
                )
                try:
                    registrar_accion(accion, id_escuela, nombre_escuela, valores, extra="dryRun=" + str(dry_run))
                    if not dry_run:
                        registrar_reciente(id_escuela, nombre_escuela)
                except Exception as exc:
                    print(f"    [!] No se pudo registrar en historial: {exc}")
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
            "/historial": render_historial(),
        }
        servidor = ServidorEscuela(paginas, on_cargar=on_cargar, on_enviar=on_enviar)

        # ---- Endpoints extra para historial/borradores/recientes ----
        def on_historial_listar(payload):
            """Devuelve lista de snapshots (para restaurar) y recientes."""
            snaps = _leer_json(_HIST_DIR / "snapshots.json", [])
            recientes = _leer_json(_HIST_DIR / "recientes.json", [])
            return {"ok": True, "snapshots": snaps[-50:], "recientes": recientes}

        def on_historial_borrador_guardar(payload):
            clave = payload.get("clave", "insertar")
            valores = payload.get("valores", {})
            guardar_borrador(clave, valores)
            return {"ok": True}

        def on_historial_borrador_cargar(payload):
            clave = payload.get("clave", "insertar")
            data = cargar_borrador(clave)
            return {"ok": True, "borrador": data}

        def on_historial_guardar_ahora(payload):
            """Guarda el estado actual del formulario como snapshot en historial
            (para que aparezca en la pagina de Historial aunque no se haya
            completado el envio)."""
            valores = payload.get("valores", {})
            id_escuela = payload.get("idEscuela", "0")
            nombre = payload.get("nombre", "")
            try:
                registrar_accion("guardado-manual", id_escuela, nombre, valores, extra="guardado manual desde formulario")
                return {"ok": True}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

        servidor.registrar_post("/historial/listar", on_historial_listar)
        servidor.registrar_post("/historial/borrador/guardar", on_historial_borrador_guardar)
        servidor.registrar_post("/historial/borrador/cargar", on_historial_borrador_cargar)
        servidor.registrar_post("/historial/guardar-ahora", on_historial_guardar_ahora)
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
