"""HTML bonito local para la app unificada de Escuela (CSS + render server-side).

No depende de ninguna libreria externa (solo stdlib `html.escape`). El HTML
generado es autocontenido: incluye su propio CSS y JS inline (sin CDNs), con
una barra lateral (sidebar) para ir y volver entre Menu / Insertar / Editar
sin recargar el proceso de Python (misma sesion de Playwright, mismo login).

La logica del modal de diferencias vive aparte, en `escuela.diff.diff`
(`DIFF_JS`), y se inserta aqui dentro del script final de cada pagina.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import json
from html import escape

from escuela.campos import GRUPOS, campos_para, etiquetas
from escuela.diff.diff import DIFF_JS
from escuela.ui.reglas import REGLAS_JS

CSS = """
:root {
    --bg: #f4f5f7;
    --card-bg: #ffffff;
    --borde: #e2e5eb;
    --texto: #1f2430;
    --texto-suave: #6b7280;
    --primario: #2f6fed;
    --primario-oscuro: #1f52c4;
    --exito: #1a9e6b;
    --peligro: #d93b3b;
    --aviso: #b8860b;
    --sombra: 0 1px 3px rgba(15, 23, 42, 0.08), 0 8px 24px rgba(15, 23, 42, 0.06);
}
* { box-sizing: border-box; }
body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--texto);
}

/* ---------- layout general: sidebar + contenido ---------- */
.layout { display: flex; align-items: flex-start; min-height: 100vh; }
.sidebar {
    width: 220px;
    flex-shrink: 0;
    background: #182236;
    color: #cbd5e1;
    padding: 22px 14px;
    position: sticky;
    top: 0;
    height: 100vh;
    box-sizing: border-box;
}
.sidebar .marca {
    color: #fff;
    font-weight: 700;
    font-size: 14.5px;
    margin: 0 0 22px;
    padding: 0 10px;
    line-height: 1.3;
}
.sidebar nav { display: flex; flex-direction: column; gap: 3px; }
.sidebar nav a {
    color: #cbd5e1;
    text-decoration: none;
    padding: 10px 12px;
    border-radius: 8px;
    font-size: 13.5px;
    font-weight: 500;
}
.sidebar nav a:hover { background: rgba(255, 255, 255, 0.08); color: #fff; }
.sidebar nav a.activo { background: var(--primario); color: #fff; }
.contenido { flex: 1; min-width: 0; }

header.top {
    background: var(--card-bg);
    border-bottom: 1px solid var(--borde);
    padding: 20px 32px;
    position: sticky;
    top: 0;
    z-index: 5;
}
header.top h1 { margin: 0; font-size: 20px; font-weight: 650; }
header.top p { margin: 4px 0 0; color: var(--texto-suave); font-size: 13px; }
main {
    max-width: 880px;
    margin: 0 auto;
    padding: 28px 20px 100px;
}

/* ---------- pantalla de Menu ---------- */
.menu-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 4px; }
.menu-card {
    background: var(--card-bg);
    border: 1px solid var(--borde);
    border-radius: 14px;
    padding: 26px 22px;
    box-shadow: var(--sombra);
    text-decoration: none;
    color: var(--texto);
    display: flex;
    flex-direction: column;
    gap: 8px;
    transition: border-color 0.15s;
}
.menu-card:hover { border-color: var(--primario); }
.menu-card .icono { font-size: 26px; }
.menu-card h3 { margin: 0; font-size: 16px; }
.menu-card p { margin: 0; color: var(--texto-suave); font-size: 13px; line-height: 1.4; }
@media (max-width: 620px) { .menu-grid { grid-template-columns: 1fr; } }

/* ---------- interruptor de modo prueba ---------- */
.toggle-card {
    display: flex;
    align-items: center;
    gap: 14px;
    background: var(--card-bg);
    border: 1px solid var(--borde);
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 18px;
    box-shadow: var(--sombra);
}
.switch-grande { position: relative; display: inline-block; width: 46px; height: 26px; flex-shrink: 0; }
.switch-grande input { opacity: 0; width: 0; height: 0; }
.switch-grande .slider {
    position: absolute; cursor: pointer; inset: 0;
    background: var(--peligro); border-radius: 999px; transition: 0.15s;
}
.switch-grande .slider::before {
    content: ""; position: absolute; width: 20px; height: 20px; left: 3px; bottom: 3px;
    background: white; border-radius: 50%; transition: 0.15s;
}
.switch-grande input:checked + .slider { background: var(--aviso); }
.switch-grande input:checked + .slider::before { transform: translateX(20px); }
#modo-texto { font-size: 13.5px; font-weight: 700; }
.toggle-card .ayuda { font-size: 12px; color: var(--texto-suave); margin-top: 2px; }

/* ---------- formulario ---------- */
.selector-card {
    background: var(--card-bg);
    border: 1px solid var(--borde);
    border-radius: 12px;
    box-shadow: var(--sombra);
    padding: 20px 24px;
    margin-bottom: 20px;
}
.selector-card label { font-weight: 600; font-size: 13px; display: block; margin-bottom: 8px; }
.selector-card select {
    width: 100%;
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid var(--borde);
    font-size: 14px;
    background: #fff;
}
.aviso-vacio {
    text-align: center;
    color: var(--texto-suave);
    padding: 40px 12px;
    font-size: 14px;
}
fieldset.grupo {
    background: var(--card-bg);
    border: 1px solid var(--borde);
    border-radius: 12px;
    box-shadow: var(--sombra);
    padding: 4px 24px 18px;
    margin: 0 0 18px;
}
fieldset.grupo legend {
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--primario);
    padding: 0 6px;
}
.campo-fila {
    display: grid;
    grid-template-columns: 220px 1fr;
    gap: 16px;
    align-items: center;
    padding: 10px 0;
    border-top: 1px solid #f0f1f4;
}
.campo-fila:first-of-type { border-top: none; }
.campo-fila.checkbox { align-items: center; }
.campo-fila label.etiqueta {
    font-size: 13.5px;
    font-weight: 600;
    color: #374151;
}
.req { color: var(--peligro); margin-left: 3px; }
.campo-fila input[type=text],
.campo-fila input[type=password],
.campo-fila input[type=number],
.campo-fila input[type=time],
.campo-fila select,
.campo-fila textarea {
    width: 100%;
    padding: 9px 11px;
    border-radius: 8px;
    border: 1px solid var(--borde);
    font-size: 14px;
    font-family: inherit;
    background: #fff;
}
.campo-fila textarea { resize: vertical; min-height: 44px; }
.campo-fila input:disabled,
.campo-fila select:disabled,
.campo-fila textarea:disabled {
    background: #f3f4f6; color: var(--texto-suave); cursor: not-allowed;
}
.switch { position: relative; display: inline-block; width: 42px; height: 24px; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider {
    position: absolute; cursor: pointer; inset: 0;
    background: #d1d5db; border-radius: 999px; transition: 0.15s;
}
.slider::before {
    content: ""; position: absolute; width: 18px; height: 18px; left: 3px; bottom: 3px;
    background: white; border-radius: 50%; transition: 0.15s;
}
.switch input:checked + .slider { background: var(--exito); }
.switch input:checked + .slider::before { transform: translateX(18px); }
.barra-acciones {
    position: sticky;
    bottom: 0;
    background: var(--card-bg);
    border-top: 1px solid var(--borde);
    padding: 14px 24px;
    display: flex;
    gap: 12px;
    justify-content: flex-end;
    border-radius: 12px;
    box-shadow: var(--sombra);
}
button.boton {
    border: none;
    border-radius: 8px;
    padding: 11px 20px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
}
button.primario { background: var(--primario); color: white; }
button.primario:hover { background: var(--primario-oscuro); }
button.primario:disabled { background: #a9bce8; cursor: not-allowed; }
button.primario.peligro { background: var(--peligro); }
button.primario.peligro:hover { background: #b52e2e; }
button.secundario { background: #eef0f4; color: var(--texto); }
#banner {
    margin-top: 14px;
    padding: 12px 16px;
    border-radius: 8px;
    font-size: 13.5px;
    display: none;
}
#banner.ok { display: block; background: #e6f7ef; color: var(--exito); border: 1px solid #b7e9d1; }
#banner.err { display: block; background: #fdecec; color: var(--peligro); border: 1px solid #f5c2c2; }
#banner.dry { display: block; background: #fff6e0; color: #916c00; border: 1px solid #f0deA0; }
.modal-fondo {
    display: none;
    position: fixed; inset: 0; background: rgba(15, 23, 42, 0.45);
    align-items: center; justify-content: center; z-index: 20; padding: 20px;
}
.modal-fondo.visible { display: flex; }
.modal {
    background: white; border-radius: 14px; max-width: 620px; width: 100%;
    max-height: 82vh; display: flex; flex-direction: column; box-shadow: var(--sombra);
}
.modal header { padding: 20px 24px 4px; }
.modal header h2 { margin: 0 0 4px; font-size: 17px; }
.modal header p { margin: 0; color: var(--texto-suave); font-size: 13px; }
.modal .cuerpo { padding: 12px 24px; overflow-y: auto; }
.aviso-real {
    background: #fdecec; color: var(--peligro); border: 1px solid #f5c2c2;
    padding: 10px 12px; border-radius: 8px; font-size: 13px; font-weight: 700;
    margin-bottom: 10px;
}
.diff-fila {
    display: grid; grid-template-columns: 1fr 1fr; gap: 10px;
    padding: 10px 0; border-top: 1px solid #f0f1f4; font-size: 13.5px;
}
.diff-fila:first-child { border-top: none; }
.diff-fila .etiqueta { grid-column: 1 / -1; font-weight: 700; color: #374151; margin-bottom: 2px; }
.diff-antes { color: var(--peligro); text-decoration: line-through; opacity: 0.75; }
.diff-despues { color: var(--exito); font-weight: 600; }
.modal footer {
    padding: 14px 24px; display: flex; gap: 10px; justify-content: flex-end;
    border-top: 1px solid var(--borde);
}
.sin-cambios { color: var(--texto-suave); font-size: 13.5px; padding: 20px 0; text-align: center; }
"""

_RUTAS = {"menu": "/", "insertar": "/insertar", "editar": "/editar", "historial": "/historial"}
_ETIQUETAS_NAV = {"menu": "Menu", "insertar": "Insertar escuela", "editar": "Editar escuela", "historial": "Historial"}


def _sidebar_html(activo):
    enlaces = "".join(
        f'<a href="{ruta}" class="{"activo" if clave == activo else ""}">{escape(_ETIQUETAS_NAV[clave])}</a>'
        for clave, ruta in _RUTAS.items()
    )
    return (
        '<aside class="sidebar">'
        '<div class="marca">Libreria Hidalgo<br>Book It Escuelas</div>'
        f"<nav>{enlaces}</nav>"
        "</aside>"
    )


def _toggle_dry_run_html():
    return (
        '<div class="toggle-card">'
        '<label class="switch-grande">'
        '<input type="checkbox" id="toggle-dry-run" checked>'
        '<span class="slider"></span>'
        "</label>"
        "<div>"
        '<div id="modo-texto">Modo prueba activado</div>'
        '<div class="ayuda">Con el interruptor encendido se llena el formulario real pero NO se guarda. '
        "Apagalo solo cuando quieras guardar de verdad.</div>"
        "</div>"
        "</div>"
    )


def _valor_texto(campo, valores):
    return escape(str(valores.get(campo["name"], "") or ""))


def _es_requerido(campo, modo):
    # `contra` no trae `required` propio en la metadata porque su obligatoriedad
    # depende del modo: el sistema real la exige al Registrar (no hay "actual"
    # que conservar) pero la deja opcional al Modificar (vacio = conservarla).
    if campo["name"] == "contra":
        return modo == "insertar"
    return campo["required"]


def _render_campo(campo, valores, opciones, modo, bloqueado=False):
    name = campo["name"]
    widget = campo["widget"]
    # Un campo bloqueado (el sistema real lo trae disabled, ej. "sucursal" al
    # editar: no se puede reasignar tras el alta) nunca es "requerido" para
    # efectos de validacion, porque el usuario no puede tocarlo.
    requerido = _es_requerido(campo, modo) and not bloqueado
    req_html = '<span class="req">*</span>' if requerido else ""
    req_attr = "required" if requerido else ""
    dis_attr = "disabled" if bloqueado else ""

    if widget == "checkbox":
        checked = "checked" if valores.get(name) else ""
        control = (
            f'<label class="switch">'
            f'<input type="checkbox" data-campo="{escape(name)}" data-tipo="checkbox" {checked} {dis_attr}>'
            f'<span class="slider"></span></label>'
        )
        clase_fila = "campo-fila checkbox"
    elif widget == "select":
        actual = str(valores.get(name, ""))
        opts_html = "".join(
            f'<option value="{escape(str(v))}" {"selected" if str(v) == actual else ""}>{escape(t)}</option>'
            for v, t in opciones.get(name, [])
        )
        control = (
            f'<select data-campo="{escape(name)}" data-tipo="select" {req_attr} {dis_attr}>'
            f'<option value="">-- seleccionar --</option>{opts_html}</select>'
        )
        clase_fila = "campo-fila"
    elif widget == "textarea":
        control = (
            f'<textarea data-campo="{escape(name)}" data-tipo="textarea" {req_attr} {dis_attr}>'
            f'{_valor_texto(campo, valores)}</textarea>'
        )
        clase_fila = "campo-fila"
    else:
        maxlen = f'maxlength="{campo["maxlength"]}"' if campo.get("maxlength") else ""
        tipo_input = widget  # text | password | number | time
        control = (
            f'<input type="{tipo_input}" data-campo="{escape(name)}" data-tipo="{tipo_input}" '
            f'value="{_valor_texto(campo, valores)}" {maxlen} {req_attr} {dis_attr} autocomplete="off">'
        )
        clase_fila = "campo-fila"

    nota = ""
    if bloqueado:
        nota = '<div style="font-size:12px;color:var(--texto-suave);margin-top:4px;">No editable: el sistema no permite cambiarlo despues del alta.</div>'
    elif campo.get("only_edit") and modo == "insertar":
        nota = '<div style="font-size:12px;color:var(--aviso);margin-top:4px;">Se aplica tras crear la escuela (paso 2 automatico).</div>'
    elif widget == "password":
        if modo == "insertar":
            nota = '<div style="font-size:12px;color:var(--texto-suave);margin-top:4px;">Requerida: es la contrasena de acceso de la escuela.</div>'
        else:
            nota = '<div style="font-size:12px;color:var(--texto-suave);margin-top:4px;">Dejar en blanco para conservar la actual.</div>'

    return (
        f'<div class="{clase_fila}">'
        f'<label class="etiqueta">{escape(campo["label"])}{req_html}</label>'
        f'<div>{control}{nota}</div>'
        f'</div>'
    )


def render_campos_html(modo, valores, opciones, bloqueados=None, incluir_solo_edit=False):
    """Renderiza los <fieldset> agrupados con los campos aplicables al modo
    ("insertar" o "editar"), prellenados con `valores`/`opciones`. `bloqueados`
    es la lista de `name` que el sistema real trae disabled en este modo (ej.
    "sucursal" al editar): se muestran en gris y no editables. En modo
    "insertar", `incluir_solo_edit=True` muestra tambien los campos que el
    sistema real solo expone al Editar (celular, repa, etc.), con la nota
    'Se aplica tras crear la escuela (paso 2 automatico)'; el back los guarda
    en una segunda pasada tras el alta."""
    aplicables = {c["name"] for c in campos_para(modo, incluir_solo_edit=incluir_solo_edit)}
    bloqueados = set(bloqueados or ())
    bloques = []
    for titulo, campos in GRUPOS:
        campos_grupo = [c for c in campos if c["name"] in aplicables]
        if not campos_grupo:
            continue
        filas = "".join(
            _render_campo(c, valores, opciones, modo, bloqueado=c["name"] in bloqueados)
            for c in campos_grupo
        )
        bloques.append(f'<fieldset class="grupo"><legend>{escape(titulo)}</legend>{filas}</fieldset>')
    return "".join(bloques)


# JS "general" de la pagina: estado global, lectura del form, banner, envio y
# el interruptor de modo prueba. El modal de diferencias (DIFF_JS, importado
# arriba) se concatena antes de este bloque.
_JS_BASE = """
const CAMPO_LABELS = __LABELS__;
let original = __ORIGINAL__;
let modoActual = "__MODO__";

function leerCampos() {
    const datos = {};
    document.querySelectorAll('[data-campo]').forEach(el => {
        const nombre = el.dataset.campo;
        if (el.dataset.tipo === 'checkbox') {
            datos[nombre] = el.checked;
        } else {
            datos[nombre] = el.value;
        }
    });
    return datos;
}

function mostrarBanner(tipo, texto) {
    const banner = document.getElementById('banner');
    banner.className = tipo;
    banner.textContent = texto;
}

function actualizarModoTexto() {
    const toggle = document.getElementById('toggle-dry-run');
    const texto = document.getElementById('modo-texto');
    const btnConfirmar = document.getElementById('btn-confirmar');
    if (!toggle || !texto) return;
    if (toggle.checked) {
        texto.textContent = 'Modo prueba activado (no se guardara nada real)';
        if (btnConfirmar) btnConfirmar.classList.remove('peligro');
    } else {
        texto.textContent = 'GUARDADO REAL activado - esto se aplicara de verdad';
        if (btnConfirmar) btnConfirmar.classList.add('peligro');
    }
}

async function confirmarEnvio() {
    const idEscuela = modoActual === 'editar'
        ? document.getElementById('selector-colegio').value
        : '0';
    const valores = leerCampos();
    const toggle = document.getElementById('toggle-dry-run');
    const dryRun = toggle ? toggle.checked : true;
    document.getElementById('btn-confirmar').disabled = true;
    try {
        const resp = await fetch('/enviar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ idEscuela, valores, dryRun }),
        });
        const data = await resp.json();
        cerrarModal();
        if (!data.ok) {
            mostrarBanner('err', 'Error: ' + (data.error || 'no se pudo enviar.'));
        } else if (data.dry_run) {
            mostrarBanner('dry', 'Modo prueba: se lleno el formulario real pero NO se guardo. Revisa la ventana del navegador automatizado.');
            original = valores;
        } else if (data.nuevo_id) {
            mostrarBanner('ok', 'Escuela creada (id ' + data.nuevo_id + '). Abriendo opciones adicionales... ' + (data.mensaje || ''));
            original = valores;
            const nombreNueva = data.nuevo_texto || ('Escuela ' + data.nuevo_id);
            setTimeout(() => {
                location.href = '/editar?nuevo=' + encodeURIComponent(data.nuevo_id)
                    + '&nombre=' + encodeURIComponent(nombreNueva);
            }, 900);
        } else {
            mostrarBanner('ok', 'Guardado correctamente. ' + (data.mensaje || ''));
            original = valores;
        }
    } catch (e) {
        mostrarBanner('err', 'Error de red: ' + e);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const btnRevisar = document.getElementById('btn-revisar');
    if (btnRevisar) btnRevisar.addEventListener('click', abrirModal);
    const btnConfirmar = document.getElementById('btn-confirmar');
    if (btnConfirmar) btnConfirmar.addEventListener('click', confirmarEnvio);
    const btnCancelar = document.getElementById('btn-cancelar-modal');
    if (btnCancelar) btnCancelar.addEventListener('click', cerrarModal);

    const toggleDryRun = document.getElementById('toggle-dry-run');
    if (toggleDryRun) {
        toggleDryRun.addEventListener('change', actualizarModoTexto);
        actualizarModoTexto();
    }

    const selector = document.getElementById('selector-colegio');
    if (selector) {
        selector.addEventListener('change', async () => {
            const idEscuela = selector.value;
            const contenedor = document.getElementById('campos');
            const acciones = document.getElementById('barra-acciones');
            if (!idEscuela) {
                contenedor.innerHTML = '<div class="aviso-vacio">Elige un colegio para cargar sus datos.</div>';
                acciones.style.display = 'none';
                return;
            }
            contenedor.innerHTML = '<div class="aviso-vacio">Cargando datos actuales...</div>';
            const resp = await fetch('/cargar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ idEscuela }),
            });
            const data = await resp.json();
            if (!data.ok) {
                contenedor.innerHTML = '<div class="aviso-vacio">Error al cargar: ' + (data.error || '') + '</div>';
                return;
            }
            contenedor.innerHTML = data.html;
            original = data.valores;
            idEscuelaActual = idEscuela;
            if (typeof sincronizarReglas === 'function') sincronizarReglas();
            acciones.style.display = 'flex';
        });

        // Tras alta real, confirmarEnvio redirige a /editar?nuevo=<id>.
        // Auto-cargar el form de edicion de esa escuela sin que el usuario
        // tenga que elegirla a mano (ahorra el paso de ir a Editar).
        // Si la escuela nueva no esta en el selector (p.ej. si el
        // re-render del servidor no llego a tiempo), se agrega manualmente
        // y despues se dispara el change para que /cargar la traiga.
        const paramsCargar = new URLSearchParams(location.search);
        const nuevoId = paramsCargar.get('nuevo');
        if (nuevoId) {
            if (!selector.querySelector('option[value="' + nuevoId + '"]')) {
                const opt = document.createElement('option');
                opt.value = nuevoId;
                opt.textContent = paramsCargar.get('nombre') || ('Escuela ' + nuevoId);
                selector.appendChild(opt);
            }
            selector.value = nuevoId;
            selector.dispatchEvent(new Event('change'));
        }
    }

    // ---------- Pantalla de Historial ----------
    // Si estamos en /historial, cargar la lista de snapshots y recientes,
    // y permitir "jal back" (restaurar valores de una accion anterior).
    if (modoActual === 'historial') {
        cargarHistorial();
    }
});

async function cargarHistorial() {
    const contenedor = document.getElementById('hist-lista');
    const contRecientes = document.getElementById('hist-recientes');
    if (!contenedor) return;
    try {
        const resp = await fetch('/historial/listar', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({}),
        });
        const data = await resp.json();
        if (!data.ok) {
            contenedor.innerHTML = '<div class="aviso-vacio">Error: ' + (data.error || '') + '</div>';
            return;
        }
        // Recientes
        let htmlRec = '';
        if (data.recientes && data.recientes.length) {
            htmlRec = '<div style="font-size:13px;font-weight:600;margin-bottom:6px;">Recientes (ultimas 20 escuelas tocadas):</div>';
            htmlRec += data.recientes.slice().reverse().map(r => {
                const safe = (r.nombre || '').replace(/'/g, "\\\\'");
                return '<button type="button" class="boton secundario" style="margin:3px;font-size:12px;" '
                    + 'onclick="abrirEditarDesdeHistorial(' + JSON.stringify(r.id) + ', ' + JSON.stringify(safe) + ')">'
                    + escapeHtml(r.nombre) + ' <span style="color:var(--texto-suave);">(' + r.ts + ')</span></button>';
            }).join('');
        }
        contRecientes.innerHTML = htmlRec;
        // Snapshots (log de acciones)
        const snaps = (data.snapshots || []).slice().reverse();
        if (!snaps.length) {
            contenedor.innerHTML = '<div class="aviso-vacio">No hay acciones registradas todavia.</div>';
            return;
        }
        contenedor.innerHTML = snaps.map((s, i) => {
            const vals = JSON.stringify(s.valores || {});
            return '<div class="diff-fila" style="grid-template-columns:1fr auto;align-items:center;">'
                + '<div><div class="etiqueta">' + escapeHtml(s.accion) + ' - ' + escapeHtml(s.nombre || s.id) + '</div>'
                + '<div style="color:var(--texto-suave);font-size:12px;">' + s.ts + ' | id=' + escapeHtml(s.id) + ' | ' + escapeHtml(s.extra || '') + '</div></div>'
                + '<button type="button" class="boton secundario" style="font-size:12px;" '
                + 'onclick=\\'restaurarSnapshot(' + i + ')\\'>Restaurar</button>'
                + '</div>';
        }).join('');
        // Guardar los snapshots en variable global para que Restaurar funcione
        window._histSnaps = snaps;
    } catch (e) {
        contenedor.innerHTML = '<div class="aviso-vacio">Error de red: ' + e + '</div>';
    }
}

function escapeHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// "Jal back": abrir Editar para esa escuela (restaura el acceso rapido).
function abrirEditarDesdeHistorial(id, nombre) {
    location.href = '/editar?nuevo=' + encodeURIComponent(id) + '&nombre=' + encodeURIComponent(nombre || ('Escuela ' + id));
}

// Restaurar valores de un snapshot: abrir Insertar prellenado con esos valores.
// Como /insertar es estatico (no recibe query), guardamos un borrador temporal
// y redirigimos; al cargar Insertar, el JS busca borrador y lo aplica.
async function restaurarSnapshot(idx) {
    const snaps = window._histSnaps || [];
    const snap = snaps[idx];
    if (!snap) return;
    if (!confirm('Restaurar "' + snap.accion + ' - ' + (snap.nombre || snap.id) + '"?\\nAbrira Insertar con esos valores para que los reenvies.')) return;
    try {
        await fetch('/historial/borrador/guardar', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ clave: 'insertar', valores: snap.valores }),
        });
        location.href = '/insertar?restaurar=1';
    } catch (e) {
        alert('Error al restaurar: ' + e);
    }
}

// ---------- Autosave de borrador (persiste al recargar F5) ----------
let _autoSaveTimer = null;
function _claveBorradorActual() {
    if (modoActual === 'editar') {
        const sel = document.getElementById('selector-colegio');
        const id = sel ? sel.value : '';
        return id ? ('editar:' + id) : null;
    }
    return modoActual === 'insertar' ? 'insertar' : null;
}
function _iniciarAutosave() {
    const params = new URLSearchParams(location.search);
    const clave = _claveBorradorActual();
    const restored = params.get('restaurar') === '1';
    if (restored && clave) {
        // Restore from ?restaurar=1 (explicit historial restore)
        fetch('/historial/borrador/cargar', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ clave }),
        }).then(r => r.json()).then(data => {
            if (data.ok && data.borrador && data.borrador.valores) {
                aplicarValoresAlForm(data.borrador.valores);
                if (typeof sincronizarReglas === 'function') sincronizarReglas();
                mostrarBanner('dry', 'Datos restaurados desde el historial. Revisa y vuelve a enviar.');
            }
        }).catch(() => {});
    } else if (clave) {
        // Silent auto-restore from last borrador (survives F5 / server restart)
        fetch('/historial/borrador/cargar', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ clave }),
        }).then(r => r.json()).then(data => {
            if (data.ok && data.borrador && data.borrador.valores) {
                const current = leerCampos();
                const hasValues = Object.values(current).some(v => v !== '' && v !== false && v !== null && v !== undefined);
                if (!hasValues) {
                    aplicarValoresAlForm(data.borrador.valores);
                    if (typeof sincronizarReglas === 'function') sincronizarReglas();
                    mostrarBanner('dry', 'Borrador automatico restaurado. Puedes seguir editando.');
                }
            }
        }).catch(() => {});
    }
    // Autosave con debounce: tras cada cambio, 800ms sin actividad -> guardar.
    document.addEventListener('change', _dispararAutosave);
    document.addEventListener('input', _dispararAutosave);
    // Beforeunload: save inmediato para no perder el ultimo estado
    window.addEventListener('beforeunload', _autoSaveBeforeUnload);
    window.addEventListener('pagehide', _autoSaveBeforeUnload);
}
function _dispararAutosave() {
    clearTimeout(_autoSaveTimer);
    _autoSaveTimer = setTimeout(() => {
        const clave = _claveBorradorActual();
        if (!clave) return;
        const valores = leerCampos();
        fetch('/historial/borrador/guardar', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ clave, valores }),
        }).catch(() => {});
        // localStorage fallback: respaldo local en el navegador
        _guardarLocalStorage(clave, valores);
    }, 800);
}
function aplicarValoresAlForm(valores) {
    document.querySelectorAll('[data-campo]').forEach(el => {
        const nombre = el.dataset.campo;
        if (!(nombre in valores)) return;
        const v = valores[nombre];
        if (el.dataset.tipo === 'checkbox') {
            el.checked = !!v;
            el.dispatchEvent(new Event('change', { bubbles: true }));
        } else if (el.tagName === 'SELECT') {
            if (Array.from(el.options).some(o => o.value === String(v))) {
                el.value = String(v);
            }
            el.dispatchEvent(new Event('change', { bubbles: true }));
        } else {
            el.value = (v === null || v === undefined) ? '' : String(v);
            el.dispatchEvent(new Event('input', { bubbles: true }));
        }
    });
}
// ---------- Guardar en historial ahora (snapshot explicito) ----------
function guardarEnHistorialAhora() {
    const valores = leerCampos();
    const idEscuela = modoActual === 'editar'
        ? (document.getElementById('selector-colegio')?.value || '0')
        : '0';
    let nombre = '';
    if (modoActual === 'editar') {
        const sel = document.getElementById('selector-colegio');
        if (sel && sel.selectedOptions.length) nombre = sel.selectedOptions[0].textContent;
    } else {
        nombre = valores.nombre || '';
    }
    fetch('/historial/guardar-ahora', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ idEscuela, valores, nombre }),
    }).then(r => r.json()).then(data => {
        if (data.ok) {
            mostrarBanner('dry', 'Estado actual guardado en historial.');
        } else {
            mostrarBanner('err', 'Error: ' + (data.error || ''));
        }
    }).catch(e => {
        mostrarBanner('err', 'Error de red: ' + e);
    });
}
// ---------- Descargar respaldo JSON ----------
function descargarRespaldo() {
    const valores = leerCampos();
    const idEscuela = modoActual === 'editar'
        ? (document.getElementById('selector-colegio')?.value || '0')
        : '0';
    const respaldo = {
        version: 1,
        fecha: new Date().toISOString(),
        modo: modoActual,
        idEscuela,
        valores,
    };
    const blob = new Blob([JSON.stringify(respaldo, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const ts = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
    a.download = 'respaldo-escuela-' + ts + '.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    mostrarBanner('dry', 'Respaldo descargado como JSON.');
}
// ---------- Cargar respaldo JSON desde archivo ----------
function cargarRespaldo(inputEl) {
    const file = inputEl.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const data = JSON.parse(e.target.result);
            if (!data.valores) {
                mostrarBanner('err', 'El archivo no tiene valores validos.');
                return;
            }
            aplicarValoresAlForm(data.valores);
            if (typeof sincronizarReglas === 'function') sincronizarReglas();
            mostrarBanner('dry', 'Respaldo cargado. Revisa los valores.');
        } catch (err) {
            mostrarBanner('err', 'Error al leer archivo: ' + err);
        }
    };
    reader.readAsText(file);
    inputEl.value = '';
}
// ---------- localStorage fallback ----------
const LS_PREFIX = 'escuela_';
function _guardarLocalStorage(clave, valores) {
    try {
        localStorage.setItem(LS_PREFIX + clave, JSON.stringify(valores));
    } catch (e) {}
}
function _cargarLocalStorageFallback() {
    const clave = _claveBorradorActual();
    if (!clave) return;
    try {
        const saved = localStorage.getItem(LS_PREFIX + clave);
        if (!saved) return;
        const valores = JSON.parse(saved);
        const current = leerCampos();
        const hasValues = Object.values(current).some(v => v !== '' && v !== false && v !== null && v !== undefined);
        if (!hasValues && Object.keys(valores).length > 0) {
            aplicarValoresAlForm(valores);
            if (typeof sincronizarReglas === 'function') sincronizarReglas();
            mostrarBanner('dry', 'Respaldo local restaurado (localStorage).');
        }
    } catch (e) {}
}
// ---------- Beforeunload: ultimo guardado antes de cerrar ----------
function _autoSaveBeforeUnload() {
    const clave = _claveBorradorActual();
    if (!clave) return;
    const valores = leerCampos();
    try {
        localStorage.setItem(LS_PREFIX + clave, JSON.stringify(valores));
    } catch (e) {}
    try {
        const body = JSON.stringify({ clave, valores });
        navigator.sendBeacon('/historial/borrador/guardar', new Blob([body], { type: 'application/json' }));
    } catch (e) {}
}
// Disparar autosave al cargar (no en menu/historial).
if (modoActual === 'insertar' || modoActual === 'editar') {
    _iniciarAutosave();
    // localStorage fallback (restore if server borrador didn't)
    setTimeout(_cargarLocalStorageFallback, 1000);
}
"""


def _layout(activo, titulo, subtitulo, cuerpo_html, cola_html, modo_js, original, catalogo=None, cfg=None):
    """Envuelve `cuerpo_html` con la barra lateral + header compartidos, y
    arma el documento HTML completo con CSS+JS inline. `cola_html` es markup
    adicional que va antes de </body> (ej. el modal). `modo_js`/`original`
    alimentan el script (modoActual/original), usados por el modal de
    diferencias y el envio; en la pantalla de Menu no se usan pero se
    inicializan igual para que el script compartido no falle. `catalogo`/`cfg`
    alimentan REGLAS_JS (escuela.ui.reglas): catalogo de escuelas existentes
    (para el aviso de duplicados) y config de reglas (mapeo por Estado, etc.)."""
    labels_json = json.dumps(etiquetas(), ensure_ascii=False)
    original_json = json.dumps(original, ensure_ascii=False)
    catalogo_json = json.dumps(catalogo or [], ensure_ascii=False)
    cfg_json = json.dumps(cfg or {}, ensure_ascii=False)
    js = (
        (DIFF_JS + _JS_BASE + REGLAS_JS)
        .replace("__LABELS__", labels_json)
        .replace("__ORIGINAL__", original_json)
        .replace("__MODO__", modo_js)
        .replace("__CATALOGO__", catalogo_json)
        .replace("__REGLAS_CFG__", cfg_json)
    )

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(titulo)} - Libreria Hidalgo</title>
<style>{CSS}</style>
</head>
<body>
<div class="layout">
    {_sidebar_html(activo)}
    <div class="contenido">
        <header class="top">
            <h1>{escape(titulo)}</h1>
            <p>{escape(subtitulo)}</p>
        </header>
        <main>
            {cuerpo_html}
        </main>
    </div>
</div>
{cola_html}
<script>{js}</script>
</body>
</html>"""


def render_menu():
    """Pantalla de entrada: 2 tarjetas grandes para ir a Insertar/Editar."""
    cuerpo = f"""
    <div class="menu-grid">
        <a class="menu-card" href="{_RUTAS['insertar']}">
            <div class="icono">+</div>
            <h3>Insertar nueva escuela</h3>
            <p>Da de alta un colegio nuevo en Book It, con todos los campos y reglas del sistema.</p>
        </a>
        <a class="menu-card" href="{_RUTAS['editar']}">
            <div class="icono">&#9998;</div>
            <h3>Editar datos de escuela</h3>
            <p>Elige un colegio existente, revisa sus datos actuales y edita solo lo que cambie.</p>
        </a>
    </div>
    """
    return _layout(
        "menu",
        "Book It Escuelas",
        "Elige que quieres hacer.",
        cuerpo,
        cola_html="",
        modo_js="menu",
        original={},
    )


def _modal_html(boton_confirmar_texto):
    return f"""
<div id="modal-fondo" class="modal-fondo">
    <div class="modal">
        <header>
            <h2>Confirmar cambios</h2>
            <p>Esto es lo que se enviara al sistema real.</p>
        </header>
        <div class="cuerpo" id="modal-cuerpo"></div>
        <footer>
            <button type="button" id="btn-cancelar-modal" class="boton secundario">Cancelar</button>
            <button type="button" id="btn-confirmar" class="boton primario">{escape(boton_confirmar_texto)}</button>
        </footer>
    </div>
</div>
"""


def render_insertar(datos_iniciales, catalogo=None, cfg=None):
    """Pantalla de alta: formulario completo con reglas, vacio salvo defaults
    del sistema. `datos_iniciales` viene de `scrape_form(page, "0")` (con los
    defaults de Insertar ya aplicados, ver `escuela.ui.reglas.
    aplicar_defaults_insertar`). `catalogo`/`cfg` alimentan las reglas de
    negocio del JS (duplicados, autollenado por Estado, etc.)."""
    campos_html = render_campos_html(
        "insertar",
        datos_iniciales["valores"],
        datos_iniciales["opciones"],
        datos_iniciales.get("bloqueados"),
        incluir_solo_edit=True,
    )
    cuerpo = f"""
    {_toggle_dry_run_html()}
    <div id="banner"></div>
    <form id="form-escuela" onsubmit="return false;">
        <div id="campos">{campos_html}</div>
        <div id="barra-acciones" class="barra-acciones" style="display:flex;">
            <button type="button" id="btn-revisar" class="boton secundario">Revisar cambios</button>
            <button type="button" class="boton secundario" onclick="guardarEnHistorialAhora()">Guardar en historial</button>
            <button type="button" class="boton secundario" onclick="descargarRespaldo()">Descargar respaldo</button>
            <label class="boton secundario" style="cursor:pointer;">Cargar respaldo
            <input type="file" accept=".json" style="display:none" onchange="cargarRespaldo(this)">
            </label>
        </div>
    </form>
    """
    return _layout(
        "insertar",
        "Registrar nueva escuela",
        "Los campos marcados con * son obligatorios.",
        cuerpo,
        cola_html=_modal_html("Registrar escuela"),
        modo_js="insertar",
        original=datos_iniciales["valores"],
        catalogo=catalogo,
        cfg=cfg,
    )


def render_editar(colegios, catalogo=None, cfg=None):
    """Pantalla de edicion: selector de colegio + formulario que se llena via
    /cargar al elegir uno. `colegios` es [(value, texto), ...]. `catalogo`/
    `cfg` alimentan las reglas de negocio del JS (duplicados, autollenado por
    Estado, etc.); el catalogo se compara excluyendo la propia escuela por id."""
    opciones_colegio = "".join(
        f'<option value="{escape(v)}">{escape(t)}</option>' for v, t in (colegios or [])
    )
    cuerpo = f"""
    <div class="selector-card">
        <label for="selector-colegio">Colegio</label>
        <select id="selector-colegio"><option value="">-- seleccionar --</option>{opciones_colegio}</select>
    </div>
    {_toggle_dry_run_html()}
    <div id="banner"></div>
    <form id="form-escuela" onsubmit="return false;">
        <div id="campos"><div class="aviso-vacio">Elige un colegio para cargar sus datos.</div></div>
        <div id="barra-acciones" class="barra-acciones" style="display:none;">
            <button type="button" id="btn-revisar" class="boton secundario">Revisar cambios</button>
            <button type="button" class="boton secundario" onclick="guardarEnHistorialAhora()">Guardar en historial</button>
            <button type="button" class="boton secundario" onclick="descargarRespaldo()">Descargar respaldo</button>
            <label class="boton secundario" style="cursor:pointer;">Cargar respaldo
            <input type="file" accept=".json" style="display:none" onchange="cargarRespaldo(this)">
            </label>
        </div>
    </form>
    """
    return _layout(
        "editar",
        "Editar datos de escuela",
        "Elige un colegio para cargar su informacion actual.",
        cuerpo,
        cola_html=_modal_html("Guardar cambios"),
        modo_js="editar",
        original={},
        catalogo=catalogo,
        cfg=cfg,
    )


def render_historial():
    """Pantalla de historial: log de acciones (TXT) + lista de snapshots
    guardados para 'jal back' (restaurar a una alta/edicion anterior) +
    recientes. Todo se carga via /historial/listar (GET del JS)."""
    cuerpo = """
    <div id="banner"></div>
    <div class="selector-card">
        <h3 style="margin:0 0 10px;font-size:15px;">Historial de acciones</h3>
        <p style="margin:0 0 12px;color:var(--texto-suave);font-size:13px;">
            Cada alta y edicion (real o practica) se guarda en <code>historial/acciones.log</code>.
            Puedes restaurar los valores de cualquier accion anterior para volver a enviarlos.
        </p>
        <div id="hist-recientes" style="margin-bottom:18px;"></div>
        <div id="hist-lista"><div class="aviso-vacio">Cargando historial...</div></div>
    </div>
    """
    return _layout(
        "historial",
        "Historial",
        "Registro de altas y ediciones (persistente en TXT/JSON).",
        cuerpo,
        cola_html="",
        modo_js="historial",
        original={},
    )
