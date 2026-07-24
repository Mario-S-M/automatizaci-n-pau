"""Reglas de negocio del formulario "Book It Escuelas" que hoy se aplican a
mano (autollenado por Estado, defaults al Insertar, cascadas de Fedex/
packing, obligatoriedad condicional y aviso de duplicados).

Este modulo es la unica fuente de esas reglas: la config (`config_js`) viaja
como JSON al navegador y la corre `REGLAS_JS` contra el DOM del formulario
propio (no el de Bookitech). Los defaults de Insertar (`aplicar_defaults_insertar`)
se aplican en Python antes de renderizar, para que el formulario ya nazca
prellenado.

No toca Playwright ni HTML directamente: solo strings de JS y datos.
"""

# ---------------------------------------------------------------------------
# Constantes compartidas entre el default server-side (Insertar) y el JS.
# ---------------------------------------------------------------------------

FEDEX_COSTO_DEFAULT = 165
FEDEX_COSTO_PRORRATEO = 1
FEDEX_OBS_DEFAULT = (
    "Recibe por fedex en 3 a 5 días, al finalizar tu compra puedes seguir tu "
    "envío en camino en la sección de PEDIDOS."
)
HORA_DESDE_DEFAULT = "09:00"
HORA_HASTA_DEFAULT = "17:00"

# Mapeo Estado -> sucursal/BBVA/cuenta de pago/usuario de atencion. El match
# es por texto de la opcion (normalizado, sin acentos, "contiene"), porque
# las opciones reales de los <select> se leen en vivo del sistema y no hay
# valores fijos que hardcodear (ver campos.py).
ESTADOS_REGLAS = [
    {
        "match": ["queretaro"],
        "sucursal": ["queretaro"],
        "bbva_prefijo": "BQ",
        "cuenta": ["hidalgo"],
        "atencion": ["carla"],
    },
    {
        "match": ["michoacan"],
        "sucursal": ["morelia"],
        "bbva_prefijo": "BM",
        "cuenta": ["hidalgo"],
        "atencion": ["lesly", "vanessa"],
    },
    {
        "match": ["mexico", "cdmx", "distrito federal"],
        "sucursal": ["edutech"],
        "bbva_prefijo": "BX",
        "cuenta": ["bookitech"],
        "atencion": ["diego", "cruz"],
    },
]


def config_js():
    """Config que viaja como JSON al navegador (REGLAS_CFG en REGLAS_JS)."""
    return {
        "estados": ESTADOS_REGLAS,
        "fedexCostoDefault": FEDEX_COSTO_DEFAULT,
        "fedexCostoProrrateo": FEDEX_COSTO_PRORRATEO,
    }


def aplicar_defaults_insertar(valores):
    """Devuelve una copia de `valores` (el snapshot de scrape_form del form de
    alta en blanco) con los defaults de Insertar ya aplicados, para que el
    formulario nazca prellenado en vez de vacio.

    `costoFedex` solo se fuerza a 165 si el form de alta ya trae envioFedex=Sí
    (que es cuando aplica el default). Si trae No/vacio, el JS deja el costo en
    0 al cargar (regla: Fedex=No -> costo 0), asi que aqui no lo pisamos."""
    datos = dict(valores)
    datos["tarjeta"] = True
    datos["transferencia"] = True
    datos["packing"] = True
    datos["desde_atencion"] = HORA_DESDE_DEFAULT
    datos["hasta_atencion"] = HORA_HASTA_DEFAULT
    datos["fedex_obs"] = FEDEX_OBS_DEFAULT
    # Solo forzar costo 165 si envioFedex esta en Sí; si no, el JS lo deja en 0.
    fedex_val = str(datos.get("envioFedex", "")).strip().lower()
    fedex_activo_py = fedex_val in ("si", "sí", "1", "true", "yes")
    if fedex_activo_py:
        datos["costoFedex"] = FEDEX_COSTO_DEFAULT
    return datos


# ---------------------------------------------------------------------------
# JS: reglas dinamicas contra el DOM del formulario propio (no Bookitech).
# Se concatena despues de DIFF_JS + _JS_BASE en escuela.ui.render._layout.
# Placeholders __REGLAS_CFG__ / __CATALOGO__ se reemplazan alli con JSON.
# ---------------------------------------------------------------------------

REGLAS_JS = r"""
const REGLAS_CFG = __REGLAS_CFG__;
const CATALOGO = __CATALOGO__;
let idEscuelaActual = "0";
const _CAMPOS_DUPLICADO = ["nombre", "bbva", "codigoweb", "usuario"];
let _dupTimer = null;

// ----------- Disclaimer de "cambiaste un dato que las reglas autoconfiguraron" -----------
// `autoValores` guarda {name: valor} CADA VEZ que una regla setea un campo por
// la logica automatica (Estado->sucursal/cuenta/atencion/bbva; Fedex/prorrateo
// ->costoFedex; packpar->packing). Si el usuario luego edita ese campo a un
// valor distinto al auto, aparece un disclaimer rojo persistente bajo el campo.
// No bloquea el envio (solo es aviso); se oculta si el valor vuelve a coincidir.
const autoValores = {};
const _DISCLAIMER_TXT = "Considera que estás cambiando este dato por valores diferentes a los configurados en automático. ¿Estás seguro?";

function _disclaimerEl(el) {
    if (!el) return null;
    const cont = el.closest("div");
    if (!cont) return null;
    let d = cont.querySelector && cont.querySelector(".disclaimer-auto");
    if (!d && cont.parentElement) {
        // el .campo-fila tiene [label, div>control+nota]; meter disclaimer en
        // el div que contiene el control, despues de la nota.
        const fila = cont.closest && cont.closest(".campo-fila");
        const wrapper = fila && (fila.children[1] || null);
        if (wrapper) {
            d = document.createElement("div");
            d.className = "disclaimer-auto";
            d.style.cssText = "font-size:12px;color:var(--peligro);margin-top:6px;line-height:1.35;";
            d.textContent = _DISCLAIMER_TXT;
            wrapper.appendChild(d);
        }
    }
    return d;
}

// Registra que la regla seteo `name` a `valor`. Muestra/oculta el disclaimer
// segun el valor actual del campo vs el auto-seteado.
function registrarAuto(name, valor) {
    autoValores[name] = valor;
    _sincronizarDisclaimer(name);
}

function _sincronizarDisclaimer(name) {
    const el = campoEl(name);
    const d = _disclaimerEl(el);
    const auto = autoValores[name];
    if (d && auto !== undefined) {
        const actual = el && el.dataset && el.dataset.tipo === "checkbox" ? el.checked : (el && el.value);
        if (String(actual) !== String(auto)) {
            d.style.display = "block";
        } else {
            d.style.display = "none";
        }
    } else if (d) {
        d.style.display = "none";
    }
}

function norm(s) {
    // Quita diacriticos (acentos) tras normalize("NFD") comparando codepoint
    // por codepoint en vez de un regex con escapes \u, para evitar líos de
    // codificación al incrustar este JS como string de Python.
    const base = (s || "").toString().normalize("NFD");
    let limpio = "";
    for (const ch of base) {
        const cp = ch.codePointAt(0);
        if (cp >= 0x0300 && cp <= 0x036f) continue;
        limpio += ch;
    }
    return limpio.toLowerCase().trim();
}

function campoEl(nombre) {
    return document.querySelector('[data-campo="' + nombre + '"]');
}

function valorCampo(nombre) {
    const el = campoEl(nombre);
    if (!el) return undefined;
    return el.dataset.tipo === "checkbox" ? el.checked : el.value;
}

function textoOpcionSeleccionada(el) {
    if (!el || !el.options) return "";
    const opcion = Array.from(el.options).find(o => o.value === el.value);
    return norm(opcion ? opcion.text : "");
}

function marcarRequeridoVisual(el, requerido) {
    if (!el) return;
    const fila = el.closest(".campo-fila");
    if (!fila) return;
    const etiqueta = fila.querySelector(".etiqueta");
    if (!etiqueta) return;
    let span = etiqueta.querySelector(".req");
    if (requerido && !span) {
        span = document.createElement("span");
        span.className = "req";
        span.textContent = "*";
        etiqueta.appendChild(span);
    } else if (!requerido && span) {
        span.remove();
    }
}

// Busca en un <select> la primera opcion cuyo texto (normalizado) contenga
// TODOS los substrings dados (AND, no OR), y la selecciona. Asi ["lesly",
// "vanessa"] solo matchea "Lesly Vanessa" y no otra "Vanessa" cualquiera.
// No hace nada si el campo esta bloqueado (disabled) o no hay match.
function seleccionarPorTexto(nombreCampo, substrs) {
    const el = campoEl(nombreCampo);
    if (!el || el.tagName !== "SELECT" || el.disabled || !substrs || !substrs.length) return;
    const objetivo = substrs.map(norm);
    const opcion = Array.from(el.options).find(o => {
        const t = norm(o.text);
        return objetivo.every(s => t.includes(s));
    });
    if (opcion) el.value = opcion.value;
}

// Cambia el prefijo (BX/BQ/BM) de la clave BBVA conservando lo que el
// usuario ya haya escrito despues de un prefijo previo.
function aplicarPrefijoBBVA(prefijo) {
    const el = campoEl("bbva");
    if (!el || el.disabled || !prefijo) return;
    const max = parseInt(el.getAttribute("maxlength") || "5", 10);
    const actual = el.value || "";
    const prefijosConocidos = (REGLAS_CFG.estados || []).map(r => r.bbva_prefijo).filter(Boolean);
    const yaTienePrefijo = prefijosConocidos.some(p => actual.slice(0, p.length).toUpperCase() === p.toUpperCase());
    const resto = yaTienePrefijo ? actual.slice(prefijo.length) : actual;
    el.value = (prefijo + resto).slice(0, max);
}

function aplicarReglasEstado() {
    const estadoEl = campoEl("estado");
    if (!estadoEl) return;
    const texto = textoOpcionSeleccionada(estadoEl);
    if (!texto) return;
    const regla = (REGLAS_CFG.estados || []).find(r => (r.match || []).some(m => texto.includes(norm(m))));
    if (!regla) {
        // Estado sin mapeo: limpiar autos del Estado anterior para que no
        // salgan disclaimers sobre valores ya no autoconfigurados.
        ["sucursal", "cuenta_open", "usuario_atencion", "bbva"].forEach(n => {
            delete autoValores[n];
            _sincronizarDisclaimer(n);
        });
        return;
    }
    seleccionarPorTexto("sucursal", regla.sucursal);
    registrarAuto("sucursal", valorCampo("sucursal"));
    seleccionarPorTexto("cuenta_open", regla.cuenta);
    registrarAuto("cuenta_open", valorCampo("cuenta_open"));
    seleccionarPorTexto("usuario_atencion", regla.atencion);
    registrarAuto("usuario_atencion", valorCampo("usuario_atencion"));
    aplicarPrefijoBBVA(regla.bbva_prefijo);
    registrarAuto("bbva", valorCampo("bbva"));
}

function fedexActivo() {
    return textoOpcionSeleccionada(campoEl("envioFedex")).startsWith("si");
}

function _setCostoFedex(valor) {
    const costo = campoEl("costoFedex");
    if (costo && !costo.disabled) {
        costo.value = String(valor);
        costo.dispatchEvent(new Event("input", { bubbles: true }));
    }
}

function aplicarReglasFedex() {
    if (fedexActivo()) {
        const prorrateoEl = campoEl("prorrateo");
        _setCostoFedex((prorrateoEl && prorrateoEl.checked)
            ? REGLAS_CFG.fedexCostoProrrateo
            : REGLAS_CFG.fedexCostoDefault);
        registrarAuto("costoFedex", String((prorrateoEl && prorrateoEl.checked)
            ? REGLAS_CFG.fedexCostoProrrateo
            : REGLAS_CFG.fedexCostoDefault));
    } else {
        _setCostoFedex("0");
        registrarAuto("costoFedex", "0");
    }
    actualizarFedexObsRequerido();
}

function aplicarReglasProrrateo() {
    const prorrateoEl = campoEl("prorrateo");
    if (!prorrateoEl || prorrateoEl.disabled) return;
    const fedexEl = campoEl("envioFedex");
    if (prorrateoEl.checked) {
        // Activar prorrateo fuerza envioFedex=Sí (si no lo está) y costo=1.
        if (fedexEl && !fedexEl.disabled && !fedexActivo()) {
            const optSi = Array.from(fedexEl.options).find(o => norm(o.text).startsWith("si"));
            if (optSi) {
                fedexEl.value = optSi.value;
                fedexEl.dispatchEvent(new Event("change", { bubbles: true }));
                registrarAuto("envioFedex", valorCampo("envioFedex"));
            }
        }
        _setCostoFedex(REGLAS_CFG.fedexCostoProrrateo);
        registrarAuto("costoFedex", String(REGLAS_CFG.fedexCostoProrrateo));
        actualizarFedexObsRequerido();
    } else if (fedexActivo()) {
        _setCostoFedex(REGLAS_CFG.fedexCostoDefault);
        registrarAuto("costoFedex", String(REGLAS_CFG.fedexCostoDefault));
    }
}

// Cascada real packing: packing ON -> habilita packpar -> habilita
// tipo_packing (Metodo de Entrega). Packing parcial fuerza Packing (que
// sigue desmarcable por si solo) y bloquea Envio Fedex mientras este activo.
// Al desmarcar packing: desmarca y deshabilita packpar (y tipo_packing).
function aplicarReglasPacking() {
    const packparEl = campoEl("packpar");
    const packingEl = campoEl("packing");
    if (!packparEl) return;
    // Si alguien marca packpar, forzar packing ON.
    if (packparEl.checked && packingEl && !packingEl.disabled) {
        packingEl.checked = true;
        registrarAuto("packing", true);
    }
    // Si packing se desmarca, desmarcar y deshabilitar packpar.
    if (packingEl && !packingEl.checked && packparEl.checked) {
        packparEl.checked = false;
    }
    _sincronizarDisablePacking();
}

// Sincroniza los disabled de packpar, envioFedex y tipo_packing segun el
// estado de packing y packpar. Llamada desde aplicarReglasPacking,
// sincronizarReglas y el change handler de packing.
// - packpar: solo habilita cuando packing este ON.
// - envioFedex: disable mientras packpar este ON.
// - tipo_packing: solo habilita cuando packing Y packpar esten ON.
function _sincronizarDisablePacking() {
    const packparEl = campoEl("packpar");
    const packingEl = campoEl("packing");
    const fedexEl = campoEl("envioFedex");
    const tipoPackingEl = campoEl("tipo_packing");
    const packingOn = !!(packingEl && packingEl.checked);
    const packparOn = !!(packparEl && packparEl.checked);
    // packpar solo se puede tocar si packing esta ON (no respeta disabled
    // permanente: packpar nunca es permanentemente bloqueado).
    if (packparEl) packparEl.disabled = !packingOn;
    // envioFedex se bloquea mientras packpar este ON (no respeta disabled
    // permanente: envioFedex nunca es permanentemente bloqueado).
    if (fedexEl) fedexEl.disabled = packparOn;
    // tipo_packing solo habilita cuando packing Y packpar esten ON.
    if (tipoPackingEl) tipoPackingEl.disabled = !(packingOn && packparOn);
}

function actualizarObsRequerido(nombreCheckbox, nombreObs) {
    const chk = campoEl(nombreCheckbox);
    const obs = campoEl(nombreObs);
    if (!chk || !obs) return;
    const requerido = !!chk.checked;
    obs.required = requerido;
    marcarRequeridoVisual(obs, requerido);
}

function actualizarFedexObsRequerido() {
    const obs = campoEl("fedex_obs");
    if (!obs) return;
    const requerido = fedexActivo();
    obs.required = requerido;
    marcarRequeridoVisual(obs, requerido);
}

function aplicarReglasObs() {
    actualizarObsRequerido("entrega_escuela", "entrega_escuela_obs");
    actualizarObsRequerido("entrega_sucursal", "entrega_sucursal_obs");
    actualizarFedexObsRequerido();
}

function algunaEntregaActiva() {
    return fedexActivo() || !!valorCampo("entrega_escuela") || !!valorCampo("entrega_sucursal");
}

// Compara nombre/BBVA/codigo WEB/usuario contra el catalogo de todas las
// escuelas (leido una vez al iniciar la app). Excluye la propia escuela por
// id al Editar, para no marcarse duplicada consigo misma.
function buscarDuplicado() {
    const idActual = String(idEscuelaActual || "0");
    for (const campo of _CAMPOS_DUPLICADO) {
        const el = campoEl(campo);
        if (!el) continue;
        const valor = norm(el.value);
        if (!valor) continue;
        const choque = (CATALOGO || []).find(r => String(r.id) !== idActual && norm(r[campo]) === valor);
        if (choque) {
            return { campo, label: (CAMPO_LABELS && CAMPO_LABELS[campo]) || campo, escuela: choque.nombre };
        }
    }
    return null;
}

// ----------- Validacion en vivo de duplicados (mientras el usuario escribe) -----------
function limpiarBordeDuplicado() {
    _CAMPOS_DUPLICADO.forEach(c => {
        const el = campoEl(c);
        if (el) el.style.borderColor = "";
    });
}

// Se llama con debounce (250ms) tras cada input/change en los 4 campos de
// duplicado. Muestra el banner de error y borde rojo del campo si choca;
// limpia el error cuando el conflicto se resuelve (sin pisar avisos de
// otras validaciones).
function validarDuplicadoLive() {
    const dup = buscarDuplicado();
    const banner = document.getElementById("banner");
    if (dup) {
        mostrarBanner("err", 'El campo "' + dup.label + '" ya esta registrado en "' + dup.escuela + '". Cambialo para continuar.');
        limpiarBordeDuplicado();
        const el = campoEl(dup.campo);
        if (el) el.style.borderColor = "var(--peligro)";
    } else {
        if (banner && banner.classList.contains("err") && banner.textContent.indexOf("ya esta registrado") !== -1) {
            banner.className = "";
            banner.textContent = "";
        }
        limpiarBordeDuplicado();
    }
}

function _onInputDuplicado(e) {
    const el = e.target;
    if (!el || !el.dataset || !_CAMPOS_DUPLICADO.includes(el.dataset.campo)) return;
    clearTimeout(_dupTimer);
    _dupTimer = setTimeout(validarDuplicadoLive, 250);
}

// Gate de negocio llamado desde abrirModal() (diff.js), antes de la
// validacion nativa. Sincroniza requeridos condicionales y bloquea si falta
// una forma de entrega o hay un duplicado.
function validarNegocio() {
    aplicarReglasObs();
    if (!algunaEntregaActiva()) {
        mostrarBanner("err", "Falta marcar al menos una forma de entrega: Envio Fedex, Entrega en escuela o Entrega en sucursal.");
        return false;
    }
    const dup = buscarDuplicado();
    if (dup) {
        mostrarBanner("err", 'El campo "' + dup.label + '" ya esta registrado en "' + dup.escuela + '". Cambialo para continuar.');
        limpiarBordeDuplicado();
        const el = campoEl(dup.campo);
        if (el) {
            el.style.borderColor = "var(--peligro)";
            if (el.scrollIntoView) el.scrollIntoView({ behavior: "smooth", block: "center" });
        }
        return false;
    }
    return true;
}

// Reaplica solo requeridos/deshabilitados segun los valores ya cargados
// (no pisa valores salvo el costoFedex cuando cargan datos con Fedex=No al
// Editar, caso comun: la escuela tiene Fedex apagado -> costo debe ser 0).
// Se llama al cargar la pagina y de nuevo tras /cargar en Editar.
function sincronizarReglas() {
    aplicarReglasObs();
    // Regla: si envioFedex != Sí al cargar (cualquier modo), costoFedex debe
    // ser 0. No se toca el costo si Fedex=Sí (preserva el valor editable 165
    // o el valor custom que la escuela ya tenga guardado).
    const fedexEl = campoEl("envioFedex");
    const costo = campoEl("costoFedex");
    if (fedexEl && costo && !fedexEl.disabled && String(costo.value) !== "0" && !fedexActivo()) {
        _setCostoFedex("0");
    }
    // Aplicar bloqueo de envioFedex/tipo_packing segun packpar/packing.
    _sincronizarDisablePacking();
    // Validacion en vivo inicial
    validarDuplicadoLive();
}

function manejarCambioReglas(e) {
    const el = e.target;
    if (!el || !el.dataset || !el.dataset.campo) return;
    const campo = el.dataset.campo;
    if (campo === "estado") aplicarReglasEstado();
    else if (campo === "envioFedex") aplicarReglasFedex();
    else if (campo === "prorrateo") aplicarReglasProrrateo();
    else if (campo === "packing" || campo === "packpar") aplicarReglasPacking();
    else if (campo === "entrega_escuela" || campo === "entrega_sucursal") aplicarReglasObs();
}

document.addEventListener("change", function(e) {
    manejarCambioReglas(e);
    _onInputDuplicado(e);
    if (e.target && e.target.dataset && e.target.dataset.campo) {
        _sincronizarDisclaimer(e.target.dataset.campo);
    }
});
document.addEventListener("input", function(e) {
    _onInputDuplicado(e);
    if (e.target && e.target.dataset && e.target.dataset.campo) {
        _sincronizarDisclaimer(e.target.dataset.campo);
    }
});
document.addEventListener("DOMContentLoaded", sincronizarReglas);
"""
