import json

from src.services.scrapper import (
    EmovaSignalRSource,
    _parsear_html_estados,
)


def _html_estados():
    columnas = []
    for linea in ("A", "B", "C", "D", "E", "H", "Premetro"):
        columnas.append(
            f'<div class="col"><img alt="Linea {linea}"><p>Normal</p></div>'
        )
    return "".join(columnas)


def test_parser_html_extrae_las_siete_lineas():
    estados = _parsear_html_estados(_html_estados())

    assert list(estados) == [
        "Linea A",
        "Linea B",
        "Linea C",
        "Linea D",
        "Linea E",
        "Linea H",
        "Linea Premetro",
    ]
    assert all(estado == "Normal" for estado in estados.values())


def test_extraer_estados_ignora_mensajes_de_otro_hub():
    payload = {
        "M": [
            {"H": "OtroHub", "M": "estadoLineas", "A": [_html_estados()]},
            {
                "H": "SignalREmova",
                "M": "estadoLineas",
                "A": [_html_estados()],
            },
        ]
    }

    estados = EmovaSignalRSource._extraer_estados(payload)

    assert len(estados) == 7
    assert estados["Linea B"] == "Normal"


def test_sse_parser_reconstruye_data_multilinea():
    class Response:
        def iter_lines(self, decode_unicode):
            yield "data: initialized"
            yield ""
            yield 'data: {"C":"1",'
            yield 'data: "M":[]}'
            yield ""

    contenidos = list(EmovaSignalRSource._mensajes_sse(Response()))

    assert contenidos == ["initialized", '{"C":"1",\n"M":[]}' ]
    assert json.loads(contenidos[1])["C"] == "1"
