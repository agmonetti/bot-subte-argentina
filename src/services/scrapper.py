import json
import sys
import time
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.config import Config
from src.services.analyzer import normalizar_estados, snapshot_completo


class EmovaSourceError(Exception):
    """Error recuperable al comunicarse con el estado de EMOVA."""


class EmovaSignalRSource:
    """Cliente mínimo del hub SignalR público usado por la página de EMOVA."""

    def __init__(self, session=None):
        self.session = session or requests.Session()

    def _negociar(self):
        params = {
            "clientProtocol": "2.0",
            "connectionData": json.dumps(
                [{"name": Config.SIGNALR_HUB}], separators=(",", ":")
            ),
            "_": str(int(time.time() * 1000)),
        }
        response = self.session.get(
            f"{Config.URL_SIGNALR}/negotiate", params=params, timeout=10
        )
        response.raise_for_status()
        data = response.json()
        token = data.get("ConnectionToken")
        if not token:
            raise EmovaSourceError("EMOVA no devolvió un token de conexión")
        return params, token

    @staticmethod
    def _parametros_transporte(params, token):
        return {
            **params,
            "transport": "serverSentEvents",
            "connectionToken": token,
        }

    @staticmethod
    def _mensajes_sse(response):
        acumulado = []
        for linea in response.iter_lines(decode_unicode=True):
            if linea is None:
                continue
            if linea == "":
                if acumulado:
                    yield "\n".join(acumulado)
                    acumulado = []
                continue
            if linea.startswith("data:"):
                acumulado.append(linea[5:].lstrip())
        if acumulado:
            yield "\n".join(acumulado)

    @staticmethod
    def _extraer_estados(payload):
        if not isinstance(payload, dict):
            return {}
        estados = {}
        for mensaje in payload.get("M", []):
            if not isinstance(mensaje, dict):
                continue
            if mensaje.get("H", "").casefold() != Config.SIGNALR_HUB.casefold():
                continue
            if mensaje.get("M", "").casefold() != Config.EVENTO_ESTADO.casefold():
                continue
            argumentos = mensaje.get("A", [])
            if argumentos and isinstance(argumentos[0], str):
                estados = _parsear_html_estados(argumentos[0])
        return estados

    def escuchar(self, procesar_estado, duracion=None, stop_event=None):
        """Escucha una conexión durante la reconciliación configurada."""
        parametros, token = self._negociar()
        transporte = self._parametros_transporte(parametros, token)
        response = None
        deadline = time.monotonic() + duracion if duracion else None
        try:
            # El stream debe abrirse antes de /start: SignalR usa el stream para
            # entregar el handshake y el estado inicial del hub.
            response = self.session.get(
                f"{Config.URL_SIGNALR}/connect",
                params=transporte,
                stream=True,
                timeout=(10, 75),
            )
            response.raise_for_status()
            response.encoding = "utf-8"
            start = self.session.get(
                f"{Config.URL_SIGNALR}/start", params=transporte, timeout=10
            )
            start.raise_for_status()

            for contenido in self._mensajes_sse(response):
                if stop_event and stop_event.is_set():
                    return
                if deadline and time.monotonic() >= deadline:
                    return
                if contenido in ("initialized", "{}"):
                    continue
                try:
                    payload = json.loads(contenido)
                except json.JSONDecodeError:
                    continue
                estados = normalizar_estados(self._extraer_estados(payload))
                if snapshot_completo(estados):
                    procesar_estado(estados, datetime.now(Config.TIMEZONE_LOCAL))
        except (requests.RequestException, ValueError, EmovaSourceError) as error:
            raise EmovaSourceError(str(error)) from error
        finally:
            if response is not None:
                response.close()


class _EstadosHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.en_columna = False
        self.en_estado = False
        self.alt = ""
        self.texto = []
        self.estados = {}

    def handle_starttag(self, tag, attrs):
        atributos = dict(attrs)
        clases = atributos.get("class", "").split()
        if tag == "div" and "col" in clases and not self.en_columna:
            self.en_columna = True
            self.alt = ""
            self.texto = []
        elif self.en_columna and tag == "img":
            self.alt = atributos.get("alt", "")
        elif self.en_columna and tag == "p":
            self.en_estado = True

    def handle_data(self, data):
        if self.en_columna and self.en_estado:
            self.texto.append(data)

    def handle_endtag(self, tag):
        if tag == "p" and self.en_columna:
            self.en_estado = False
        elif tag == "div" and self.en_columna and self.alt:
            self.estados[self.alt.strip()] = " ".join("".join(self.texto).split())
            self.en_columna = False


def _parsear_html_estados(html):
    """Extrae las etiquetas y textos del HTML entregado por SignalR."""
    parser = _EstadosHTMLParser()
    parser.feed(html)
    return parser.estados
