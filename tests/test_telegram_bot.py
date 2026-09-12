import pytest
import requests
from datetime import date

from src.config import Config
from src.services.storage import guardar_snapshot
from src.services.telegram_bot import escuchar_comandos, obtener_respuesta_estado


def test_estado_consulta_emova_en_el_momento(tmp_config, monkeypatch):
    guardar_snapshot(
        {
            "A": {"original": "Normal", "canonico": "normal"},
            "B": {"original": "Cerrada por obras", "canonico": "cerrada por obras"},
        },
        "2026-08-13T13:00:00+00:00",
    )

    class FakeSource:
        def obtener_estado(self):
            return {
                "A": {"original": "Demora", "canonico": "demora"},
                "B": {"original": "Normal", "canonico": "normal"},
            }

    monkeypatch.setattr("src.services.telegram_bot.EmovaSignalRSource", FakeSource)

    texto = obtener_respuesta_estado()

    assert "<b>A:</b> Demora" in texto
    assert "<b>B:</b> Normal" in texto
    assert "<b>A:</b> Normal" not in texto
    assert "Última actualización:" in texto


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


def _actualizacion_comando(texto, update_id=10, timestamp=None, chat_id=None):
    mensaje = {"text": texto, "chat": {"id": chat_id or int(Config.TELEGRAM_CHAT_ID)}}
    if timestamp is not None:
        mensaje["date"] = timestamp
    return {"update_id": update_id, "message": mensaje}


def test_horarios_no_responde_a_chat_no_autorizado(monkeypatch):
    enviados = []
    llamadas = {"n": 0}

    def fake_updates(offset):
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            return {
                "ok": True,
                "result": [_actualizacion_comando("/horarios", chat_id=999)],
            }
        raise KeyboardInterrupt()

    monkeypatch.setattr("src.services.telegram_bot.obtener_updates", fake_updates)
    monkeypatch.setattr(
        "src.services.telegram_bot.obtener_respuesta_horarios",
        lambda fecha: (_ for _ in ()).throw(AssertionError("servicio no autorizado")),
    )
    monkeypatch.setattr(
        "src.services.telegram_bot.enviar_mensaje_telegram",
        lambda mensaje, chat_id=None: enviados.append((mensaje, chat_id)),
    )

    with pytest.raises(KeyboardInterrupt):
        escuchar_comandos()

    assert enviados == []


def test_horarios_usa_fecha_original_en_buenos_aires(monkeypatch):
    fechas = []
    enviados = []
    llamadas = {"n": 0}
    timestamp = 1789174800  # 2026-09-12 01:00 UTC = 2026-09-11 22:00 local

    def fake_updates(offset):
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            return {"ok": True, "result": [_actualizacion_comando("/horarios detalle", timestamp=timestamp)]}
        raise KeyboardInterrupt()

    monkeypatch.setattr("src.services.telegram_bot.obtener_updates", fake_updates)
    monkeypatch.setattr(
        "src.services.telegram_bot.obtener_respuesta_horarios",
        lambda fecha: fechas.append(fecha) or "tabla",
    )
    monkeypatch.setattr(
        "src.services.telegram_bot.enviar_mensaje_telegram",
        lambda mensaje, chat_id=None: enviados.append((mensaje, chat_id)),
    )
    monkeypatch.setattr(
        "src.services.telegram_bot.time",
        type("T", (), {"sleep": staticmethod(lambda seconds: None)})(),
    )

    with pytest.raises(KeyboardInterrupt):
        escuchar_comandos()

    assert fechas == [date(2026, 9, 11)]
    assert enviados == [("tabla", int(Config.TELEGRAM_CHAT_ID))]


def test_horarios_sin_timestamp_usa_fecha_local_actual(monkeypatch):
    from datetime import datetime

    fechas = []
    llamadas = {"n": 0}

    class FechaFija:
        @classmethod
        def now(cls, tz):
            return datetime(2026, 9, 14, 12, tzinfo=tz)

        @classmethod
        def fromtimestamp(cls, valor, tz):
            return datetime.fromtimestamp(valor, tz)

    def fake_updates(offset):
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            return {"ok": True, "result": [_actualizacion_comando("/horarios")]}
        raise KeyboardInterrupt()

    monkeypatch.setattr("src.services.telegram_bot.datetime", FechaFija)
    monkeypatch.setattr("src.services.telegram_bot.obtener_updates", fake_updates)
    monkeypatch.setattr(
        "src.services.telegram_bot.obtener_respuesta_horarios",
        lambda fecha: fechas.append(fecha) or "tabla",
    )
    monkeypatch.setattr(
        "src.services.telegram_bot.enviar_mensaje_telegram",
        lambda mensaje, chat_id=None: None,
    )
    monkeypatch.setattr(
        "src.services.telegram_bot.time",
        type("T", (), {"sleep": staticmethod(lambda seconds: None)})(),
    )

    with pytest.raises(KeyboardInterrupt):
        escuchar_comandos()

    assert fechas == [date(2026, 9, 14)]


def test_horariosfoo_se_ignora_y_estado_sigue_funcionando(monkeypatch):
    enviados = []
    llamadas = {"n": 0}

    def fake_updates(offset):
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            return {
                "ok": True,
                "result": [
                    _actualizacion_comando("/horariosfoo"),
                    _actualizacion_comando("/estado"),
                ],
            }
        raise KeyboardInterrupt()

    monkeypatch.setattr("src.services.telegram_bot.obtener_updates", fake_updates)
    monkeypatch.setattr(
        "src.services.telegram_bot.obtener_respuesta_horarios",
        lambda fecha: (_ for _ in ()).throw(AssertionError("comando inválido")),
    )
    monkeypatch.setattr(
        "src.services.telegram_bot.obtener_respuesta_estado",
        lambda: "Estado actual",
    )
    monkeypatch.setattr(
        "src.services.telegram_bot.enviar_mensaje_telegram",
        lambda mensaje, chat_id=None: enviados.append((mensaje, chat_id)),
    )
    monkeypatch.setattr(
        "src.services.telegram_bot.time",
        type("T", (), {"sleep": staticmethod(lambda seconds: None)})(),
    )

    with pytest.raises(KeyboardInterrupt):
        escuchar_comandos()

    assert enviados == [("Estado actual", int(Config.TELEGRAM_CHAT_ID))]


def test_horarios_de_madrugada_conserva_fecha_calendario_del_mensaje(monkeypatch):
    fechas = []
    llamadas = {"n": 0}
    timestamp = 1789185600  # 2026-09-12 04:00 UTC = 2026-09-12 01:00 local

    def fake_updates(offset):
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            return {"ok": True, "result": [_actualizacion_comando("/horarios", timestamp=timestamp)]}
        raise KeyboardInterrupt()

    monkeypatch.setattr("src.services.telegram_bot.obtener_updates", fake_updates)
    monkeypatch.setattr(
        "src.services.telegram_bot.obtener_respuesta_horarios",
        lambda fecha: fechas.append(fecha) or "tabla",
    )
    monkeypatch.setattr(
        "src.services.telegram_bot.enviar_mensaje_telegram",
        lambda mensaje, chat_id=None: None,
    )
    monkeypatch.setattr(
        "src.services.telegram_bot.time",
        type("T", (), {"sleep": staticmethod(lambda seconds: None)})(),
    )

    with pytest.raises(KeyboardInterrupt):
        escuchar_comandos()

    assert fechas == [date(2026, 9, 12)]
