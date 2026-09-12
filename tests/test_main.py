from datetime import datetime

from src.config import Config
from src.main import procesar_estado
from src.services.analyzer import normalizar_estados


def estados(estado_a="Normal"):
    valores = {linea: "Normal" for linea in Config.LINEAS}
    valores["A"] = estado_a
    return normalizar_estados(valores)


def test_primer_snapshot_se_persiste_sin_notificar(tmp_config, monkeypatch):
    notificaciones = []
    monkeypatch.setattr(
        "src.main.enviar_alerta_cambios",
        lambda cambios, fecha: notificaciones.append(cambios),
    )

    procesar_estado(estados("Demora"), datetime(2026, 8, 13, 10, 0, 0))

    assert notificaciones == []


def test_retorno_a_normal_notifica_el_cambio(tmp_config, monkeypatch):
    notificaciones = []
    monkeypatch.setattr(
        "src.main.enviar_alerta_cambios",
        lambda cambios, fecha: notificaciones.append(cambios),
    )

    procesar_estado(estados("Demora"), datetime(2026, 8, 13, 10, 0, 0))
    procesar_estado(estados("Normal"), datetime(2026, 8, 13, 10, 10, 0))

    assert notificaciones == [
        {"A": {"anterior": "Demora", "actual": "Normal"}}
    ]


def test_payload_incompleto_no_reemplaza_snapshot(tmp_config, monkeypatch):
    notificaciones = []
    monkeypatch.setattr(
        "src.main.enviar_alerta_cambios",
        lambda cambios, fecha: notificaciones.append(cambios),
    )

    procesar_estado(normalizar_estados({"A": "Demora"}), datetime.now())

    assert notificaciones == []
    assert not Config.ARCHIVO_ESTADO.exists()
