"""Mini servidor local (solo 127.0.0.1) que sirve el HTML bonito y puentea
las peticiones del navegador hacia Playwright.

Solo stdlib (`http.server`/`socketserver`/`queue`/`threading`): Playwright
vive en el hilo principal (su API sincrona no es thread-safe), asi que este
servidor corre en un hilo aparte y mete cada peticion en una cola; el hilo
principal la despacha llamando a `procesar_pendientes()` en bucle.

Flujo general:
1. El proceso principal (`escuela/app.py`) ya hizo login y tiene la `page`
   de Playwright.
2. Crea un `ServidorEscuela` pasandole las paginas (Menu/Insertar/Editar de
   `escuela.ui.render`) y callbacks (`on_cargar`, `on_enviar`) que
   internamente llaman a `escuela.consultar.scrape_form` /
   `escuela.guardar.guardar_form`.
3. Abre el navegador del usuario en `http://127.0.0.1:<puerto>/`. Desde ahi
   se navega con la barra lateral entre Menu / Insertar / Editar (paginas
   reales, sin JS de ruteo: cada una es una respuesta GET distinta del mismo
   servidor).
4. El hilo principal llama `procesar_pendientes()` en bucle: cuando el
   navegador hace un fetch a `/cargar` o `/enviar`, el callback correspondiente
   se ejecuta en el hilo principal (con Playwright) y el resultado regresa
   como JSON a la pagina.
"""

import http.server
import json
import queue
import socketserver
import threading
from urllib.parse import urlparse


class ServidorEscuela:
    """Servidor HTTP local (solo 127.0.0.1) que sirve una o mas paginas
    estaticas (el HTML bonito de Menu/Insertar/Editar) y puentea /cargar y
    /enviar hacia callbacks que deben ejecutarse en el hilo principal, donde
    vive la `page` de Playwright."""

    def __init__(self, paginas, on_cargar=None, on_enviar=None):
        """`paginas` es un dict {ruta: html}, ej. {"/": ..., "/insertar": ...,
        "/editar": ...}. Tambien acepta un solo string por compatibilidad
        (equivale a {"/": html})."""
        self._paginas = paginas if isinstance(paginas, dict) else {"/": paginas}
        self._on_cargar = on_cargar
        self._on_enviar = on_enviar
        self._trabajos = queue.Queue()
        self._httpd = None

    def _handler_factory(self):
        servidor = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                pass  # silenciar el log de acceso en la terminal

            def _responder_json(self, data):
                cuerpo = json.dumps(data).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)

            def do_GET(self):
                ruta = urlparse(self.path).path
                html = servidor._paginas.get(ruta)
                if html is not None:
                    cuerpo = html.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(cuerpo)))
                    self.end_headers()
                    self.wfile.write(cuerpo)
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self):
                ruta = urlparse(self.path).path
                largo = int(self.headers.get("Content-Length", 0) or 0)
                crudo = self.rfile.read(largo) if largo else b"{}"
                try:
                    payload = json.loads(crudo or b"{}")
                except json.JSONDecodeError:
                    payload = {}

                if ruta == "/cargar" and servidor._on_cargar:
                    self._responder_json(servidor._encolar(servidor._on_cargar, payload, timeout=90))
                elif ruta == "/enviar" and servidor._on_enviar:
                    self._responder_json(servidor._encolar(servidor._on_enviar, payload, timeout=240))
                else:
                    self.send_response(404)
                    self.end_headers()

        return Handler

    def _encolar(self, fn, payload, timeout=60):
        evento = threading.Event()
        caja = {}

        def tarea():
            try:
                caja["resultado"] = fn(payload)
            except Exception as exc:  # noqa: BLE001 - reportar cualquier error al navegador
                caja["error"] = str(exc)
            finally:
                evento.set()

        self._trabajos.put(tarea)
        completado = evento.wait(timeout=timeout)
        if not completado:
            return {"ok": False, "error": "tiempo de espera agotado"}
        if "error" in caja:
            return {"ok": False, "error": caja["error"]}
        return caja.get("resultado", {"ok": False, "error": "sin resultado"})

    def iniciar(self, puerto=0):
        self._httpd = socketserver.ThreadingTCPServer(("127.0.0.1", puerto), self._handler_factory())
        self._httpd.daemon_threads = True
        hilo = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        hilo.start()
        return self._httpd.server_address[1]

    def procesar_pendientes(self, timeout=0.2):
        """Llamar en bucle desde el hilo principal (el de Playwright) para
        ejecutar los trabajos que el servidor va encolando."""
        try:
            tarea = self._trabajos.get(timeout=timeout)
        except queue.Empty:
            return False
        tarea()
        return True

    def detener(self):
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
