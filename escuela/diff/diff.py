"""JS del modal "Antes -> Despues" (revisar cambios antes de enviar).

Aislado de `escuela.ui.render` a proposito: es la unica pieza que le importa
al usuario para confirmar visualmente que va a enviar exactamente lo que
cree que va a enviar, tanto al Insertar (resumen de alta) como al Editar
(diferencias reales contra lo que habia antes).

Se expone como una cadena de JS (`DIFF_JS`) que `escuela.ui.render` inserta
dentro de la pagina generada, junto al resto del script de la UI. No hay
logica de diff en Python: todo ocurre en el navegador contra el DOM del
formulario, comparando contra `original` (el snapshot cargado al abrir/
consultar la escuela).
"""

DIFF_JS = """
// Dado un elemento y un valor "crudo" (tal como se guarda en `original` o se
// lee de leerCampos()), devuelve el texto legible correspondiente. Para los
// <select> busca la opcion cuyo value coincide, para no depender de cual sea
// el valor seleccionado actualmente en el DOM.
function textoParaValor(el, valorCrudo) {
    if (el.dataset.tipo === 'checkbox') return valorCrudo ? 'Si' : 'No';
    if (el.dataset.tipo === 'select') {
        const opcion = Array.from(el.options).find(o => o.value === String(valorCrudo ?? ''));
        return opcion ? opcion.text : (valorCrudo ? String(valorCrudo) : '(vacio)');
    }
    if (el.dataset.tipo === 'password') return valorCrudo ? '(nueva contrasena)' : '(sin cambio)';
    return valorCrudo ? String(valorCrudo) : '(vacio)';
}

function calcularDiferencias() {
    const diffs = [];
    document.querySelectorAll('[data-campo]').forEach(el => {
        const nombre = el.dataset.campo;
        const actual = el.dataset.tipo === 'checkbox' ? el.checked : el.value;
        const antes = original[nombre];
        const antesNorm = antes === undefined || antes === null ? '' : antes;
        const actualNorm = actual === undefined || actual === null ? '' : actual;
        if (el.dataset.tipo === 'password') {
            if (el.value) diffs.push({ nombre, el, soloNuevo: true });
            return;
        }
        if (String(antesNorm) !== String(actualNorm)) {
            diffs.push({ nombre, el, antes, actual, soloNuevo: false });
        }
    });
    return diffs;
}

function abrirModal() {
    // Reglas de negocio (escuela.ui.reglas): sincroniza requeridos
    // condicionales y bloquea si falta una forma de entrega o hay un
    // duplicado, ANTES de la validacion nativa de abajo.
    if (typeof validarNegocio === 'function' && !validarNegocio()) return;

    // Los botones son type="button" (no disparan el submit del <form>), asi
    // que hay que pedir la validacion nativa explicitamente: si falta un
    // campo requerido, el navegador lo marca y no se abre el modal.
    const form = document.getElementById('form-escuela');
    if (!form.reportValidity()) return;

    const toggleDryRun = document.getElementById('toggle-dry-run');
    const esReal = toggleDryRun && !toggleDryRun.checked;
    const avisoModo = esReal
        ? '<div class="aviso-real">Modo prueba DESACTIVADO: esto se guardara de verdad en el sistema.</div>'
        : '';

    const diffs = calcularDiferencias();
    const cuerpo = document.getElementById('modal-cuerpo');
    const btnConfirmar = document.getElementById('btn-confirmar');
    if (diffs.length === 0) {
        cuerpo.innerHTML = avisoModo + '<div class="sin-cambios">No hay cambios para guardar.</div>';
        btnConfirmar.disabled = true;
    } else {
        btnConfirmar.disabled = false;
        cuerpo.innerHTML = avisoModo + diffs.map(d => {
            const label = CAMPO_LABELS[d.nombre] || d.nombre;
            if (d.soloNuevo) {
                return `<div class="diff-fila"><div class="etiqueta">${label}</div>
                    <div class="diff-despues">Se actualizara la contrasena</div><div></div></div>`;
            }
            const despues = textoParaValor(d.el, d.actual);
            const antesTxt = modoActual === 'insertar' ? '(nuevo)' : textoParaValor(d.el, d.antes);
            return `<div class="diff-fila"><div class="etiqueta">${label}</div>
                <div class="diff-antes">${antesTxt}</div><div class="diff-despues">${despues}</div></div>`;
        }).join('');
    }
    document.getElementById('modal-fondo').classList.add('visible');
}

function cerrarModal() {
    document.getElementById('modal-fondo').classList.remove('visible');
}
"""
