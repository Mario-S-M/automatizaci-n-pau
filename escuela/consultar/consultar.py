"""Consulta (solo lectura) del formulario real de Book It Escuelas.

`scrape_form` abre el formulario de alta o de modificacion y LEE sus valores
y opciones actuales por atributo `name`. No modifica ni envia nada: es la
fuente de datos tanto para precargar el HTML de "Editar" con la informacion
real de la escuela, como para conocer los catalogos (estados, sucursales,
usuarios de atencion, etc.) al mostrar el HTML de "Insertar".

`escanear_catalogo_rapido` lee los 4 campos de duplicados de TODAS las escuelas
en paralelo via HTTP (requests + BeautifulSoup) en vez de navegar una por una
con Playwright, reutilizando la misma sesion (cookies) del navegador ya logueado.
Es ~10x mas rapido: N escuelas en segundos en vez de minutos.
"""

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import requests
from bs4 import BeautifulSoup

import config
from escuela.campos import campos_planos
from escuela.navegador import BOOKIT_ESCUELAS_URL, abrir_form


def scrape_form(page, id_escuela):
    """Abre el formulario real (alta si id_escuela=="0", edicion en caso
    contrario) y LEE sus valores/opciones actuales por atributo `name`. No
    modifica ni envia nada.

    Devuelve {"valores": {...}, "opciones": {...}, "bloqueados": [...]}.
    `bloqueados` son los `name` que el sistema real trae `disabled` en este
    modo de forma PERMANENTE (ej. "sucursal" al editar: no se puede
    reasignar tras el alta). Los campos con disable DINAMICO por cascada
    (packpar, tipo_packing: dependen de packing) se excluyen de aqui: el
    JS los habilita/deshabilita en vivo segun el estado de packing."""
    abrir_form(page, id_escuela)

    _DINAMICOS = {"packpar", "tipo_packing"}
    valores = {}
    opciones = {}
    bloqueados = []
    for campo in campos_planos():
        if campo["only_edit"] and str(id_escuela) == "0":
            continue
        name = campo["name"]
        loc = page.locator(f"#modulo [name='{name}']")
        if loc.count() == 0:
            continue

        if loc.is_disabled() and name not in _DINAMICOS:
            bloqueados.append(name)

        if campo["widget"] == "checkbox":
            valores[name] = loc.is_checked()
        elif campo["widget"] == "select":
            valores[name] = loc.input_value()
            opciones[name] = [
                (opcion.get_attribute("value"), (opcion.inner_text() or "").strip())
                for opcion in loc.locator("option").all()
            ]
        else:
            valores[name] = loc.input_value()

    return {"valores": valores, "opciones": opciones, "bloqueados": bloqueados}


def escanear_catalogo(page, colegios):
    """Recorre TODAS las escuelas (excepto la opcion vacia del selector) y lee
    solo los 4 campos usados por el HTML propio para avisar de duplicados
    ANTES de enviar: nombre, bbva, codigoweb, usuario. Se llama una sola vez
    al iniciar la app (`escuela/app.py`); el sistema real ya rechaza
    duplicados al guardar, pero eso solo se sabe despues de enviar.

    `colegios` es la lista `[(id, texto), ...]` que devuelve `abrir_landing`.
    Devuelve `[{"id", "nombre", "bbva", "codigoweb", "usuario"}, ...]`."""
    catalogo = []
    total = len(colegios)
    for i, (id_escuela, texto) in enumerate(colegios, start=1):
        print(f"    [{i}/{total}] Leyendo {texto}...")
        datos = scrape_form(page, id_escuela)
        valores = datos["valores"]
        catalogo.append(
            {
                "id": id_escuela,
                "nombre": valores.get("nombre", ""),
                "bbva": valores.get("bbva", ""),
                "codigoweb": valores.get("codigoweb", ""),
                "usuario": valores.get("usuario", ""),
                "desactivado": "deshabilitado" in texto.lower(),
            }
        )
    return catalogo


# ---------------------------------------------------------------------------
# Version paralela: requests + BeautifulSoup en vez de Playwright una por una.
# Reutiliza las cookies del contexto Playwright ya logueado para lanzar todos
# los POSTs al endpoint "modificarEscuela" en paralelo. ~10x mas rapido.
# ---------------------------------------------------------------------------

_CAMPOS_DUPLICADO = ("nombre", "bbva", "codigoweb", "usuario")


def _parsear_campos_escuela(html, id_escuela, texto=""):
    """Parser ligero con BeautifulSoup: extrae solo los 4 campos de duplicado
    (nombre, bbva, codigoweb, usuario) del HTML que devuelve el POST
    modificarEscuela. No abre el navegador ni ejecuta JS: el servidor ya envio
    el <form> con los values poblados, asi que basta buscar por atributo name."""
    soup = BeautifulSoup(html, "lxml")
    cont = soup.find(id="modulo") or soup
    valores = {}
    for name in _CAMPOS_DUPLICADO:
        el = cont.find(attrs={"name": name})
        if el is None:
            valores[name] = ""
        elif el.name == "select":
            sel_opt = el.find("option", selected=True)
            valores[name] = sel_opt.get("value", "") if sel_opt else ""
        else:
            valores[name] = el.get("value", "") or ""
    return {
        "id": str(id_escuela),
        "nombre": valores.get("nombre", ""),
        "bbva": valores.get("bbva", ""),
        "codigoweb": valores.get("codigoweb", ""),
        "usuario": valores.get("usuario", ""),
        "desactivado": "deshabilitado" in texto.lower(),
    }


def escanear_catalogo_rapido(page, colegios, max_workers=15):
    """Version paralela de escanear_catalogo: lanza todos los POSTs al
    endpoint modificarEscuela en paralelo via requests, reutilizando las
    cookies de sesion del contexto Playwright ya logueado. Parsea cada
    respuesta con BeautifulSoup (no abre el navegador ni ejecuta JS).

    `colegios` es la lista `[(id, texto), ...]` que devuelve `abrir_landing`.
    Devuelve `[{"id", "nombre", "bbva", "codigoweb", "usuario"}, ...]` --- el
    mismo formato que `escanear_catalogo` (version lenta con Playwright).

    `max_workers` controla el paralelismo (15 por defecto: buen balance para
    50-200 escuelas sin saturar el servidor)."""
    cookies = page.context.cookies(config.BASE_URL)
    cookie_jar = {c["name"]: c["value"] for c in cookies}
    ua = page.evaluate("() => navigator.userAgent")
    headers = {"User-Agent": ua, "Referer": BOOKIT_ESCUELAS_URL}

    def _uno(id_escuela, texto=""):
        payload = {"boton": "modificarEscuela", "idEscuela": str(id_escuela)}
        for intento in range(2):
            try:
                r = requests.post(
                    BOOKIT_ESCUELAS_URL,
                    data=payload,
                    cookies=cookie_jar,
                    headers=headers,
                    timeout=20,
                )
                if r.status_code == 200:
                    return _parsear_campos_escuela(r.text, id_escuela, texto)
            except requests.RequestException:
                if intento == 1:
                    raise
        return _parsear_campos_escuela("", id_escuela, texto)

    total = len(colegios)
    catalogo = [None] * total
    completados = 0

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_uno, id_, _texto): i for i, (id_, _texto) in enumerate(colegios)}
        for fut in as_completed(futures):
            i = futures[fut]
            completados += 1
            id_, texto = colegios[i]
            try:
                catalogo[i] = fut.result()
            except Exception as exc:
                print(f"    [!] Error leyendo {texto}: {exc}")
                catalogo[i] = {
                    "id": id_,
                    "nombre": "",
                    "bbva": "",
                    "codigoweb": "",
                    "usuario": "",
                    "desactivado": False,
                }
            print(f"    [{completados}/{total}] {texto}")

    return catalogo
