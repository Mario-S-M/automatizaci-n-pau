"""Navegacion compartida hacia el formulario real de Book It Escuelas.

Tanto `escuela.consultar` (solo lectura) como `escuela.guardar` (escritura)
necesitan llegar al mismo lugar: el landing de la seccion y, desde ahi, al
formulario de alta o de modificacion de una escuela. Esa parte se centraliza
aqui para no duplicarla.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import config

BOOKIT_ESCUELAS_URL = config.BASE_URL + "/Secciones/Book_It/bookit"


def abrir_landing(page):
    """Navega al landing de Book It Escuelas y devuelve la lista de colegios
    del selector `idEscuela` como [(value, texto), ...]."""
    page.goto(BOOKIT_ESCUELAS_URL, wait_until="domcontentloaded")
    page.wait_for_selector("h2.page-title", timeout=15000)

    colegios = []
    for opcion in page.locator("select[name='idEscuela'] option").all():
        valor = opcion.get_attribute("value")
        texto = (opcion.inner_text() or "").strip()
        if valor:
            colegios.append((valor, texto))
    return colegios


def _abrir_form_alta(page):
    abrir_landing(page)
    page.locator("button[value='registrarEscuela']").click()
    page.wait_for_load_state("networkidle", timeout=20000)
    page.wait_for_selector("#modulo form", timeout=15000)


def _abrir_form_edicion(page, id_escuela):
    abrir_landing(page)
    page.select_option("select[name='idEscuela']", str(id_escuela))
    page.locator("button[value='modificarEscuela']").click()
    page.wait_for_load_state("networkidle", timeout=20000)
    page.wait_for_selector("#modulo form", timeout=15000)


def abrir_form(page, id_escuela):
    """Abre el formulario real: alta si `id_escuela == "0"`, edicion en caso
    contrario. Punto de entrada unico usado por consultar y guardar."""
    if str(id_escuela) == "0":
        _abrir_form_alta(page)
    else:
        _abrir_form_edicion(page, id_escuela)
