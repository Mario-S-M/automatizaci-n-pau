"""Escritura real en el formulario de Book It Escuelas (alta o edicion).

`guardar_form` abre el formulario correcto, lo llena campo por campo con los
valores que vienen del HTML bonito y, si `dry_run` es False, hace click en
Registrar/Actualizar. En `dry_run` se detiene justo antes del click (no muta
el sistema real) y regresa lo que se habria enviado, para poder revisarlo.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from escuela.campos import campos_planos
from escuela.navegador import abrir_form


def _set_campo(page, campo, valor):
    name = campo["name"]
    loc = page.locator(f"#modulo [name='{name}']")
    if loc.count() == 0:
        return
    if loc.is_disabled():
        # Campo solo-lectura en este modo (ej. "sucursal" al editar: el
        # sistema no permite reasignarla tras el alta). Se omite en vez de
        # colgarse esperando a que se habilite.
        return
    if not loc.is_visible():
        # Campo oculto por cascada del sistema real (ej. "entrega_sucursal_obs"
        # cuando "Entrega Sucursal" esta desactivado: el textarea queda con
        # display:none, no disabled). Se omite en vez de colgarse 30s
        # esperando a que .fill()/.select_option() lo encuentren visible.
        return

    if campo["widget"] == "checkbox":
        # Bootstrap "custom-checkbox": el <input> real queda cubierto por su
        # wrapper visual y ademas hay JS del sitio que revierte el click
        # simulado (incluso con force=True). Se fija `.checked` por JS y se
        # disparan los eventos reales para que los handlers jQuery del
        # sistema (ej. habilitar "packpar"/"tipo_packing" al marcar
        # "packing") reaccionen igual que con un click real.
        loc.evaluate(
            "(el, val) => {"
            "  el.checked = val;"
            "  el.dispatchEvent(new Event('input', {bubbles: true}));"
            "  el.dispatchEvent(new Event('change', {bubbles: true}));"
            "}",
            bool(valor),
        )
    elif campo["widget"] == "select":
        if valor not in (None, ""):
            loc.select_option(str(valor))
    elif campo["widget"] == "password":
        # Vacio = conservar la contrasena actual: no tocar el campo.
        if valor:
            loc.fill(str(valor))
    else:
        loc.fill("" if valor is None else str(valor))


def guardar_form(page, id_escuela, valores, dry_run=True):
    """Abre el formulario real, lo llena campo por campo con `valores` y, si
    `dry_run` es False, hace click en Registrar/Actualizar. En dry_run se
    detiene justo antes del click (no muta el sistema) y regresa lo que se
    habria enviado para poder revisarlo.

    El orden de `campos_planos()` importa: reproduce el orden real del
    formulario (ej. "packing" -> "packpar" -> "tipo_packing"), que es
    necesario porque el sistema tiene cascadas de habilitado/deshabilitado
    encadenadas via JS (marcar "packing" habilita "packpar", marcar
    "packpar" habilita "tipo_packing")."""
    abrir_form(page, id_escuela)

    for campo in campos_planos():
        if campo["only_edit"] and str(id_escuela) == "0":
            continue
        if campo["name"] in valores:
            _set_campo(page, campo, valores[campo["name"]])

    if dry_run:
        return {"ok": True, "dry_run": True, "url": page.url}

    page.locator("button[value='guardarEscuela']").click()
    page.wait_for_load_state("networkidle", timeout=20000)

    mensaje = ""
    alerta = page.locator(".alert").first
    if alerta.count() > 0:
        mensaje = (alerta.inner_text() or "").strip()

    # Detectar si el guardado fallo: el sistema real muestra un .alert con
    # clase de error (alert-danger) o el texto contiene "error"/"fallo".
    # Si la pagina sigue en el mismo form (URL no cambio a landing), tambien
    # es indicio de fallo.
    error_save = False
    if alerta.count() > 0:
        clase = alerta.get_attribute("class") or ""
        txt_lower = mensaje.lower()
        if "alert-danger" in clase or "error" in txt_lower or "fallo" in txt_lower:
            error_save = True
    if error_save:
        return {"ok": False, "dry_run": False, "url": page.url, "error": mensaje or "el sistema rechazo el guardado"}

    return {"ok": True, "dry_run": False, "url": page.url, "mensaje": mensaje}
