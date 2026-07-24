"""Fuente unica de metadata de los campos del formulario "Book It Escuelas".

Este modulo NO toca Playwright ni HTML: solo describe que campos existen, en
que orden, agrupados en que secciones, y que reglas tiene cada uno (label,
tipo de widget, si es requerido, maxlength). Tanto `escuela.consultar` y
`escuela.guardar` (interaccion real con Bookitech) como `escuela.ui` (render
del HTML bonito) consumen esta metadata para no duplicar la lista de campos.

Los VALORES y las OPCIONES de los <select> (estados, sucursales, usuarios de
atencion, etc.) no se hardcodean aqui: se leen en vivo del sistema porque son
catalogos que cambian con el tiempo.
"""

# Cada campo: name (atributo `name` real en el HTML de Bookitech), label
# (texto bonito para el HTML propio), widget (text/password/number/time/
# textarea/select/checkbox), required, maxlength (o None) y only_edit (True
# si el campo solo existe en el formulario de "Modificar Escuela", no en el
# de "Registrar Escuela").
GRUPOS = [
    (
        "Datos generales",
        [
            {"name": "nombre", "label": "Nombre", "widget": "text", "required": True},
            {"name": "bbva", "label": "BBVA", "widget": "text", "required": True, "maxlength": 5},
            {"name": "estado", "label": "Estado", "widget": "select", "required": False},
            {"name": "sucursal", "label": "Sucursal", "widget": "select", "required": False},
            {"name": "codigoweb", "label": "Codigo WEB", "widget": "text", "required": True, "maxlength": 6},
        ],
    ),
    (
        "Clientes y pago",
        [
            {"name": "c_cod_origen", "label": "Cliente Venta", "widget": "text", "required": True},
            {"name": "c_cod_almacen", "label": "Cliente Almacen", "widget": "text", "required": True},
            {"name": "cuenta_open", "label": "Cuenta Pago", "widget": "select", "required": False},
            {"name": "efectivo", "label": "Efectivo", "widget": "checkbox", "required": False},
            {"name": "tarjeta", "label": "Tarjeta", "widget": "checkbox", "required": False},
            {"name": "transferencia", "label": "Transferencia", "widget": "checkbox", "required": False},
        ],
    ),
    (
        "Envio y entrega",
        [
            {"name": "envioFedex", "label": "Envio Fedex", "widget": "select", "required": True},
            {"name": "costoFedex", "label": "Costo Fedex", "widget": "number", "required": True},
            {"name": "prorrateo", "label": "Prorrateo", "widget": "checkbox", "required": False},
            {"name": "packing", "label": "Packing", "widget": "checkbox", "required": False},
            {"name": "packpar", "label": "Packing Parcial", "widget": "checkbox", "required": False},
            {"name": "tipo_packing", "label": "Metodo de Entrega", "widget": "select", "required": False},
            {"name": "entrega_escuela", "label": "Entrega Escuela", "widget": "checkbox", "required": False},
            {"name": "entrega_escuela_obs", "label": "Obs Entrega Escuela", "widget": "textarea", "required": False},
            {"name": "entrega_sucursal", "label": "Entrega Sucursal", "widget": "checkbox", "required": False},
            {"name": "entrega_sucursal_obs", "label": "Obs Entrega Sucursal", "widget": "textarea", "required": False},
            {"name": "fedex_obs", "label": "Obs Entrega Fedex", "widget": "textarea", "required": False},
        ],
    ),
    (
        "Atencion",
        [
            {"name": "usuario_atencion", "label": "Usuario para Atencion", "widget": "select", "required": True},
            {"name": "desde_atencion", "label": "Atencion Desde", "widget": "time", "required": True},
            {"name": "hasta_atencion", "label": "Atencion Hasta", "widget": "time", "required": True},
            {"name": "observacion", "label": "Pizarrón inicio", "widget": "textarea", "required": False},
            {"name": "mensaje_correo", "label": "Mensaje del Correo", "widget": "textarea", "required": False},
        ],
    ),
    (
        "Acceso escuela",
        [
            {"name": "usuario", "label": "Usuario", "widget": "text", "required": True},
            {"name": "contra", "label": "Contrasena", "widget": "password", "required": False},
        ],
    ),
    (
        "Opciones adicionales (solo edicion)",
        [
            {"name": "celular", "label": "Habilitado", "widget": "checkbox", "required": False, "only_edit": True},
            {"name": "repa", "label": "Reporte Administrador", "widget": "checkbox", "required": False, "only_edit": True},
            {"name": "surtido_total", "label": "Surtido Total", "widget": "checkbox", "required": False, "only_edit": True},
            {"name": "m_obligatoria", "label": "Matricula Obligatoria", "widget": "checkbox", "required": False, "only_edit": True},
            {"name": "portadas", "label": "Mostrar Portadas", "widget": "checkbox", "required": False, "only_edit": True},
        ],
    ),
]


def campos_planos():
    """Devuelve todos los campos en un solo listado plano, en el mismo orden
    en el que aparecen agrupados, con `maxlength`/`only_edit` normalizados."""
    planos = []
    for _grupo, campos in GRUPOS:
        for campo in campos:
            planos.append(
                {
                    "name": campo["name"],
                    "label": campo["label"],
                    "widget": campo["widget"],
                    "required": campo.get("required", False),
                    "maxlength": campo.get("maxlength"),
                    "only_edit": campo.get("only_edit", False),
                }
            )
    return planos


def campos_para(modo, incluir_solo_edit=False):
    """Campos aplicables a un modo ("insertar" o "editar"). En "insertar" se
    excluyen los campos que solo existen al modificar una escuela existente,
    a menos que `incluir_solo_edit=True` (caso del HTML de Insertar que muestra
    esos campos con nota "se aplica tras alta" y el back los guarda en una
    segunda pasada tras crear la escuela)."""
    if modo == "editar" or incluir_solo_edit:
        return list(campos_planos())
    return [c for c in campos_planos() if not c["only_edit"]]


def nombres_solo_edit():
    """Lista de `name` que solo existen al Modificar (no al Registrar). Los
    usa `app.py` para separar los valores que se guardan en la segunda pasada
    (post-alta: editar la escuela recien creada y setear solo estos campos)."""
    return [c["name"] for c in campos_planos() if c["only_edit"]]


def etiquetas():
    """Mapa name -> label, usado por el HTML/JS para mostrar el modal de
    diferencias con nombres legibles en vez del atributo `name` crudo."""
    return {c["name"]: c["label"] for c in campos_planos()}
