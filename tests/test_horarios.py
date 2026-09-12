import copy
import json
from datetime import date

import pytest

from src.services import horarios


ESPERADO = [
    (
        "A",
        None,
        [
            ("San Pedrito", ("05:30", "23:00"), ("06:00", "23:30"), ("08:00", "22:08")),
            ("Pza. de Mayo–Casa Rosada", ("05:30", "23:28"), ("06:00", "23:57"), ("08:00", "22:36")),
        ],
    ),
    (
        "B",
        None,
        [
            ("J. M. Rosas–V. Urquiza", ("05:30", "23:00"), ("06:00", "01:00"), ("08:00", "22:00")),
            ("Leandro N. Alem", ("05:30", "23:30"), ("06:00", "01:30"), ("08:00", "22:28")),
        ],
    ),
    (
        "C",
        None,
        [
            ("Constitución", ("05:30", "23:19"), ("06:00", "23:40"), ("08:00", "22:21")),
            ("Retiro", ("05:30", "23:33"), ("06:00", "23:54"), ("08:00", "22:34")),
        ],
    ),
    (
        "D",
        None,
        [
            ("Congreso de Tucumán", ("05:30", "23:02"), ("06:00", "23:26"), ("08:00", "22:01")),
            ("Catedral", ("05:30", "23:33"), ("06:00", "23:59"), ("08:00", "22:34")),
        ],
    ),
    (
        "E",
        None,
        [
            ("Pza. de los Virreyes–Perón", ("05:30", "22:56"), ("06:00", "23:26"), ("08:00", "21:56")),
            ("Retiro", ("05:30", "23:30"), ("06:00", "23:58"), ("08:00", "22:28")),
        ],
    ),
    (
        "H",
        None,
        [
            ("Hospitales", ("05:30", "23:51"), ("06:00", "00:20"), ("08:00", "22:51")),
            ("Fac. de Derecho–J. Lanteri", ("05:30", "23:30"), ("06:00", "23:59"), ("08:00", "22:29")),
        ],
    ),
    (
        "Premetro",
        "Centro Cívico",
        [
            ("Intendente Saguier", ("05:30", "21:00"), ("06:00", "21:07"), ("08:00", "21:00")),
            ("Centro Cívico", ("06:03", "21:33"), ("06:31", "21:38"), ("08:32", "21:32")),
        ],
    ),
    (
        "Premetro",
        "General Savio",
        [
            ("Intendente Saguier", ("05:39", "20:48"), ("06:11", "20:55"), ("08:13", "20:47")),
            ("General Savio", ("06:13", "21:21"), ("06:43", "21:27"), ("08:45", "21:19")),
        ],
    ),
]


def _matriz(catalogo):
    resultado = []
    for grupo in catalogo["lineas"]:
        cabeceras = []
        for cabecera in grupo["cabeceras"]:
            cabeceras.append(
                (
                    cabecera["nombre"],
                    tuple(cabecera["habil"].values()),
                    tuple(cabecera["sabado"].values()),
                    tuple(cabecera["domingo_feriado"].values()),
                )
            )
        resultado.append((grupo["linea"], grupo["ramal"], cabeceras))
    return resultado


def test_catalogo_transcribe_las_16_cabeceras():
    assert _matriz(horarios.cargar_horarios()) == ESPERADO


def test_seleccion_laborable_y_formato():
    respuesta = horarios.obtener_respuesta_horarios(date(2026, 9, 14))

    assert "Horarios del subte — 14/09/2026 (lunes a viernes)" in respuesta
    assert "Pza. de Mayo–Casa Rosada: primero 05:30 · último 23:28" in respuesta
    assert "Línea B — horario extendido" not in respuesta


def test_viernes_incluye_nota_sin_alterar_tabla():
    respuesta = horarios.obtener_respuesta_horarios(date(2026, 9, 11))

    assert "Horarios del subte — 11/09/2026 (lunes a viernes)" in respuesta
    assert "J. M. Rosas–V. Urquiza: primero 05:30 · último 23:00" in respuesta
    assert "Línea B — horario extendido viernes y sábado: último tren desde J. M. de Rosas 01:00 y desde Leandro N. Alem 01:30 (día siguiente)." in respuesta


def test_sabado_marca_medianoche_y_distingue_ramas_premetro():
    respuesta = horarios.obtener_respuesta_horarios(date(2026, 9, 12))

    assert "Horarios del subte — 12/09/2026 (sábado)" in respuesta
    assert "Hospitales: primero 06:00 · último 00:20 (día siguiente)" in respuesta
    assert "<b>Premetro — Centro Cívico</b>" in respuesta
    assert "<b>Premetro — General Savio</b>" in respuesta
    assert "Centro Cívico: primero 06:31 · último 21:38" in respuesta
    assert "General Savio: primero 06:43 · último 21:27" in respuesta


def test_domingo_y_feriado_nacional_usan_columna_domingo():
    domingo = horarios.obtener_respuesta_horarios(date(2026, 9, 13))
    feriado = horarios.obtener_respuesta_horarios(date(2026, 5, 1))

    for respuesta, fecha in ((domingo, "13/09/2026"), (feriado, "01/05/2026")):
        assert f"Horarios del subte — {fecha} (domingo/feriado)" in respuesta
        assert "San Pedrito: primero 08:00 · último 22:08" in respuesta
        assert "Línea B — horario extendido" not in respuesta


def test_calendario_public_cubre_cambio_de_anio_y_feriado_trasladado():
    assert horarios.tipo_dia(date(2027, 1, 1)) == "domingo_feriado"
    assert horarios.tipo_dia(date(2026, 10, 12)) == "domingo_feriado"


def test_respuesta_contiene_todas_las_cabeceras_y_cabe_en_telegram():
    respuesta = horarios.obtener_respuesta_horarios(date(2026, 9, 12))

    assert len(respuesta) < 4096
    for _, _, cabeceras in ESPERADO:
        for nombre, *_ in cabeceras:
            assert nombre in respuesta


def test_datos_se_escapan_como_html(monkeypatch):
    catalogo = copy.deepcopy(horarios.cargar_horarios())
    catalogo["lineas"][0]["cabeceras"][0]["nombre"] = "<Cabecera> & especial"
    monkeypatch.setattr(horarios, "cargar_horarios", lambda: catalogo)

    respuesta = horarios.obtener_respuesta_horarios(date(2026, 9, 14))

    assert "&lt;Cabecera&gt; &amp; especial" in respuesta
    assert "<Cabecera> & especial" not in respuesta


@pytest.mark.parametrize("contenido", ["{", '{"lineas": []}'])
def test_catalogo_ausente_o_corrupto_no_devuelve_parcial(monkeypatch, tmp_path, contenido):
    archivo = tmp_path / "horarios.json"
    monkeypatch.setattr(horarios, "ARCHIVO_HORARIOS", archivo)
    if contenido != "{":
        archivo.write_text(contenido, encoding="utf-8")

    assert horarios.obtener_respuesta_horarios(date(2026, 9, 14)) == horarios._INDISPONIBLE


def test_hora_invalida_no_devuelve_tabla(monkeypatch, tmp_path):
    catalogo = horarios.cargar_horarios()
    catalogo["lineas"][0]["cabeceras"][0]["habil"]["primero"] = "25:00"
    archivo = tmp_path / "horarios.json"
    archivo.write_text(json.dumps(catalogo), encoding="utf-8")
    monkeypatch.setattr(horarios, "ARCHIVO_HORARIOS", archivo)

    assert horarios.obtener_respuesta_horarios(date(2026, 9, 14)) == horarios._INDISPONIBLE


def test_error_de_calendario_no_finge_dia_habil(monkeypatch):
    monkeypatch.setattr(horarios, "CALENDARIO_FERIADOS", None)

    assert horarios.obtener_respuesta_horarios(date(2026, 5, 1)) == horarios._INDISPONIBLE
