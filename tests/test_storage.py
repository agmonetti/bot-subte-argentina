import json

from src.config import Config
from src.services.storage import cargar_snapshot, guardar_snapshot


def test_guardar_y_cargar_snapshot_round_trip(tmp_config):
    estados = {
        "A": {"original": "Normal", "canonico": "normal"},
    }

    guardar_snapshot(estados, "2026-08-13T10:00:00-03:00")
    data = cargar_snapshot()

    assert data == {
        "ultima_actualizacion": "2026-08-13T10:00:00-03:00",
        "estados": estados,
    }


def test_cargar_snapshot_migra_formato_anterior(tmp_config):
    Config.ARCHIVO_ESTADO.write_text(
        json.dumps(
            {
                "ultima_actualizacion": "2026-08-13T10:00:00-03:00",
                "estados_actuales": {"Linea A": "Normal"},
                "historial": {"A_problema": {"estado": "Demora"}},
            }
        ),
        encoding="utf-8",
    )

    assert cargar_snapshot() == {
        "ultima_actualizacion": "2026-08-13T10:00:00-03:00",
        "estados": {
            "A": {"original": "Normal", "canonico": "normal"},
        },
    }


def test_cargar_json_corrupto_devuelve_vacio(tmp_config, capsys):
    Config.ARCHIVO_ESTADO.write_text("{no valido", encoding="utf-8")

    assert cargar_snapshot() == {}
    assert "Error de I/O" in capsys.readouterr().out
