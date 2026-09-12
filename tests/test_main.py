from datetime import datetime

from src.config import Config
from src.main import procesar_estado
from src.services.analyzer import normalizar_estados
from src.services.storage import cargar_snapshot


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


def test_mismo_snapshot_no_repite_alerta_ni_fecha(tmp_config, monkeypatch):
    notificaciones = []
    monkeypatch.setattr(
        "src.main.enviar_alerta_cambios",
        lambda cambios, fecha: notificaciones.append(cambios),
    )

    procesar_estado(estados(), datetime(2026, 9, 12, 8, 40, 0))
    procesar_estado(
        estados("Servicio limitado entre Retiro y Belgrano"),
        datetime(2026, 9, 12, 8, 50, 0),
    )
    primera_fecha = cargar_snapshot()["ultima_actualizacion"]
    procesar_estado(
        estados("  servicio   limitado entre Retiro y Belgrano "),
        datetime(2026, 9, 12, 9, 0, 0),
    )

    assert notificaciones == [
        {"A": {"anterior": "Normal", "actual": "Servicio limitado entre Retiro y Belgrano"}}
    ]
    assert cargar_snapshot()["ultima_actualizacion"] == primera_fecha


def test_payload_incompleto_no_reemplaza_snapshot(tmp_config, monkeypatch):
    notificaciones = []
    monkeypatch.setattr(
        "src.main.enviar_alerta_cambios",
        lambda cambios, fecha: notificaciones.append(cambios),
    )

    procesar_estado(normalizar_estados({"A": "Demora"}), datetime.now())

    assert notificaciones == []
    assert not Config.ARCHIVO_ESTADO.exists()
