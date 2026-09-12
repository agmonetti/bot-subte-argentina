import pytest
import requests

from src.config import Config
from src.services.storage import guardar_snapshot
from src.services.telegram_bot import escuchar_comandos, obtener_respuesta_estado


def test_estado_usa_snapshot_persistido(tmp_config):
    guardar_snapshot(
        {
            "A": {"original": "Normal", "canonico": "normal"},
            "B": {"original": "Cerrada por obras", "canonico": "cerrada por obras"},
        },
        "2026-08-13T10:00:00-03:00",
    )

    texto = obtener_respuesta_estado()

    assert "<b>A:</b> Normal" in texto
    assert "<b>B:</b> Cerrada por obras" in texto
    assert "Última actualización: 2026-08-13T10:00:00-03:00" in texto


def test_listener_ignora_chat_no_autorizado(monkeypatch):
    enviados = []
    llamadas = {"n": 0}

    def fake_updates(offset):
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            return {
                "ok": True,
                "result": [
                    {
                        "update_id": 5,
                        "message": {"text": "/estado", "chat": {"id": 999}},
                    }
                ],
            }
        raise KeyboardInterrupt()

    monkeypatch.setattr("src.services.telegram_bot.obtener_updates", fake_updates)
    monkeypatch.setattr(
        "src.services.telegram_bot.enviar_mensaje_telegram",
        lambda mensaje, chat_id=None: enviados.append((mensaje, chat_id)),
    )

    with pytest.raises(KeyboardInterrupt):
        escuchar_comandos()

    assert enviados == []


def test_listener_responde_estado_al_chat_autorizado(monkeypatch):
    enviados = []
    llamadas = {"n": 0}

    def fake_updates(offset):
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            return {
                "ok": True,
                "result": [
                    {
                        "update_id": 6,
                        "message": {
                            "text": "/estado detalle",
                            "chat": {"id": int(Config.TELEGRAM_CHAT_ID)},
                        },
                    }
                ],
            }
        raise KeyboardInterrupt()

    monkeypatch.setattr("src.services.telegram_bot.obtener_updates", fake_updates)
    monkeypatch.setattr(
        "src.services.telegram_bot.obtener_respuesta_estado",
        lambda: "Estado actual",
    )
    monkeypatch.setattr(
        "src.services.telegram_bot.enviar_mensaje_telegram",
        lambda mensaje, chat_id=None: enviados.append((mensaje, chat_id)),
    )

    with pytest.raises(KeyboardInterrupt):
        escuchar_comandos()

    assert enviados == [("Estado actual", int(Config.TELEGRAM_CHAT_ID))]


def test_error_de_red_no_rompe_el_loop(monkeypatch):
    llamadas = {"n": 0}

    def fake_updates(offset):
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            raise requests.exceptions.ConnectionError("boom")
        raise KeyboardInterrupt()

    monkeypatch.setattr("src.services.telegram_bot.obtener_updates", fake_updates)
    monkeypatch.setattr(
        "src.services.telegram_bot.time",
        type("T", (), {"sleep": staticmethod(lambda seconds: None)})(),
    )

    with pytest.raises(KeyboardInterrupt):
        escuchar_comandos()
