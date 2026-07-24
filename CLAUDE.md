# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es esto

Scripts de automatización con Playwright (Python, API síncrona) para el sistema interno
de Librerías Hidalgo en `https://lh.bookitech.mx/sistema` (Bookitech). Cada módulo bajo
`navegacion/` automatiza un flujo completo dentro de ese sistema, reutilizando el login
común de `autenticacion/login.py`. El paquete `escuela/` (ver más abajo) automatiza
Insertar/Editar en "Book It Escuelas" con un HTML local propio en vez de operar la UI
fea del sistema directamente.

## Setup

```bash
cp config.example.py config.py   # completar EMAIL y PASSWORD reales
python3 -m playwright install chromium   # si el navegador no está descargado
```

`config.py` contiene credenciales reales y está en `.gitignore` — nunca debe
versionarse ni subirse a git. `config.example.py` es la plantilla pública sin datos.

No hay `requirements.txt` ni gestor de dependencias declarado; la única dependencia
externa es `playwright` (instalada globalmente en el entorno de Python 3.9 del sistema).
No hay suite de tests ni configuración de lint/formatter en el repo.

## Ejecutar y probar scripts

Cada módulo de `navegacion/` (y `autenticacion/login.py`) es ejecutable de forma
independiente y abre un navegador visible (`headless=False`) que queda abierto
esperando Enter en la terminal al terminar:

```bash
python3 autenticacion/login.py              # prueba solo el login
python3 navegacion/bookit_escuelas.py       # flujo completo: login + Book It Escuelas
```

Para probarlos de forma no interactiva (sin quedarse esperando el Enter final),
alimentar un Enter por stdin:

```bash
echo "" | python3 navegacion/bookit_escuelas.py
```

Estos scripts hacen login real contra el sistema en producción — no hay entorno de
staging ni mocks. Confirmar con el usuario antes de correrlos si no es obvio que se
quiere probar contra el sistema real.

### Insertar / Editar escuela (`escuela/`)

```bash
python3 escuela/app.py
```

Un solo comando: hace login real, abre el navegador Playwright y además abre un HTML
local bonito (`http://127.0.0.1:<puerto>/`) en el navegador por defecto del usuario.
Desde ahí, una barra lateral permite ir y volver entre **Menú / Insertar / Editar**
sin volver a la terminal ni relanzar nada (mismo login, misma sesión).

El modo prueba ya no es un flag de `--dry-run`: es un **interruptor visible en cada
pantalla**, encendido por defecto (seguro — llena el formulario real pero no hace
click en Registrar/Actualizar). Apagarlo solo cuando se quiere guardar de verdad;
recomendable probar primero contra "Colegio DEMO". El proceso principal queda
esperando Enter en la terminal para cerrar el navegador y el servidor local.

## Arquitectura

- **`config.py`**: única fuente de `EMAIL`, `PASSWORD`, `BASE_URL`. Todo módulo lo
  importa; nunca hardcodear credenciales ni URLs en otro archivo.
- **`autenticacion/login.py`**: expone `iniciar_sesion(page)`, la única función de
  login del proyecto. Hace login sobre una `page` de Playwright ya creada por el
  llamador y lanza `RuntimeError` si el sistema rechaza las credenciales (se detecta
  porque la URL post-submit sigue conteniendo `login.php`). Todo flujo nuevo bajo
  `navegacion/` debe importar y reutilizar esta función en vez de reimplementar login.
- **`navegacion/*.py`**: un módulo por flujo/sección del sistema Bookitech. Patrón que
  siguen (ver `bookit_escuelas.py`): abrir navegador → `iniciar_sesion(page)` →
  navegar a la URL de la sección → esperar un selector específico que confirme que la
  página cargó → dejar el navegador abierto para inspección manual (`input()`).
- **Import cruzado entre paquetes**: como los scripts se ejecutan directamente
  (`python3 navegacion/bookit_escuelas.py`), cada módulo **que se ejecuta como script
  standalone** (tiene su propio `if __name__ == "__main__":`) inserta la raíz del
  proyecto en `sys.path` manualmente al inicio del archivo antes de `import config` o
  de importar entre paquetes hermanos (`autenticacion` ↔ `navegacion` ↔ `escuela`).
  Los módulos que son solo librería (nunca se corren directamente, ej. los de
  `escuela/consultar/`, `escuela/guardar/`, `escuela/ui/`) no necesitan repetir esto:
  basta con que el entry point que los importa ya haya fijado `sys.path`. Ojo con la
  profundidad al copiar el patrón: es `parent.parent` para un módulo a un nivel de la
  raíz (`navegacion/foo.py`, `escuela/campos.py`, `escuela/app.py`) pero
  `parent.parent.parent` para uno a dos niveles (`escuela/consultar/consultar.py`).

### `escuela/`: Insertar/Editar escuela con HTML propio

Automatiza el formulario real de "Book It Escuelas" (`config.BASE_URL +
"/Secciones/Book_It/bookit"`, el mismo `<form>` para alta y edición: un botón
`boton=registrarEscuela`/`modificarEscuela` decide cuál, y ambos guardan con
`boton=guardarEscuela`). En vez de operar esa UI directamente, se scrapea/llena por
Playwright pero se le muestra al usuario un HTML local propio (bonito, ordenado, con
reglas visibles y modal de diferencias Antes→Después antes de enviar).

- **`escuela/campos.py`**: fuente única de metadata de campos (label, widget, orden,
  agrupación, `required`, `maxlength`, `only_edit`). Los *valores* y *opciones* de los
  `<select>` nunca se hardcodean aquí: se leen en vivo (son catálogos que cambian).
- **`escuela/navegador.py`**: navegación compartida hacia el formulario real
  (`abrir_landing`, `abrir_form`), usada tanto por `consultar` como por `guardar`.
- **`escuela/consultar/consultar.py`**: `scrape_form(page, id_escuela)` — solo lectura.
- **`escuela/guardar/guardar.py`**: `guardar_form(page, id_escuela, valores, dry_run)`
  — escritura real, compartida por insertar y editar.
- **`escuela/diff/diff.py`**: JS del modal "Antes → Después" (revisar cambios antes de
  enviar), aislado del resto del render.
- **`escuela/ui/render.py`** + **`escuela/ui/servidor.py`**: HTML autocontenido
  (CSS+JS inline, sin CDNs, barra lateral compartida) y el mini servidor local
  (stdlib) que sirve varias páginas estáticas (`/`, `/insertar`, `/editar`) y puentea
  `/cargar` y `/enviar` hacia Playwright, que sigue viviendo en el hilo principal.
- **`escuela/app.py`**: único entry point ejecutable (login real, navegador visible,
  levanta el servidor con las 3 páginas, abre el navegador del usuario en `/`, espera
  Enter para cerrar). No tiene flags: el modo prueba es un interruptor en el HTML que
  viaja como `dryRun` en el POST a `/enviar` (default `True` en el servidor si por
  algún motivo no llega, para nunca asumir guardado real por accidente).

Reglas del sistema real descubiertas al implementar esto (importantes si se toca este
código o se agregan campos nuevos):

- **Campos bloqueados dinámicamente**: varios `<select>`/`<input>` vienen `disabled` en
  el DOM real según el modo o el estado de otros campos — algunos de forma permanente
  tras el alta (`sucursal`, `c_cod_origen`, `c_cod_almacen`, `cuenta_open`: no se pueden
  reasignar al editar), otros por cascada JS (`packing` habilita `packpar`, que a su vez
  habilita `tipo_packing`). `guardar_form`/`_set_campo` detecta esto **en vivo** con
  `loc.is_disabled()` antes de tocar cualquier campo (nunca se hardcodea una lista fija
  de bloqueados) y lo omite en vez de colgarse esperando a que se habilite.
  `campos_planos()` respeta el orden real del formulario a propósito, para que la
  cascada se dispare en el orden correcto al llenar.
- **Checkboxes "custom-checkbox" de Bootstrap**: el `<input type=checkbox>` real queda
  cubierto visualmente por su wrapper, y el sitio tiene JS que revierte un click
  simulado (incluso con `force=True` de Playwright). Se fija `.checked` por JS
  (`loc.evaluate(...)`) y se disparan `input`/`change` reales, para que los handlers
  jQuery del sistema reaccionen igual que con un click real.
- **`contra` (contraseña) es requerida solo al Insertar**, no al Editar (donde vacío =
  conservar la actual). El HTML marca esto dinámicamente según el modo.

### Selectores: evitar `text=` ambiguo

El HTML de Bookitech suele repetir el mismo texto en el menú lateral (a veces oculto/
colapsado) y en el título real de la página (`<h2 class="page-title">...</h2>`). Un
selector `text=...` genérico puede matchear el elemento oculto del menú primero y
Playwright se queda esperando a que se vuelva visible hasta hacer timeout. Preferir
selectores más específicos (ej. `h2.page-title`) para confirmar que la navegación
llegó a la página correcta, en vez de buscar el texto visible en cualquier parte del DOM.
