from datetime import datetime

from src.config import Config
from src.services.telegram_notifier import enviar_alerta_cambios, enviar_mensaje_telegram


class FakeResponse:
    def raise_for_status(self):
        pass


def test_alerta_incluye_solo_lineas_modificadas(monkeypatch):
    capturado = {}

    def fake_post(url, data, timeout):
        capturado["data"] = data
        return FakeResponse()

    monkeypatch.setattr("src.services.telegram_notifier.requests.post", fake_post)
    enviar_alerta_cambios(
        {"B": {"anterior": "Normal", "actual": "Cerrada <por> obras"}},
        datetime(2026, 8, 13, 10, 0, 0),
    )

    assert "<b>B:</b> Cerrada &lt;por&gt; obras" in capturado["data"]["text"]
    assert capturado["data"]["chat_id"] == Config.TELEGRAM_CHAT_ID


def test_alerta_sin_cambios_no_envia(monkeypatch):
    llamadas = []
    monkeypatch.setattr(
        "src.services.telegram_notifier.enviar_mensaje_telegram",
        lambda mensaje, chat_id=None: llamadas.append(mensaje),
    )

    assert enviar_alerta_cambios({}, datetime.now()) is None
    assert llamadas == []


def test_enviar_mensaje_usa_chat_id_personalizado(monkeypatch):
    capturado = {}

    def fake_post(url, data, timeout):
        capturado["data"] = data
        return FakeResponse()

    monkeypatch.setattr("src.services.telegram_notifier.requests.post", fake_post)
    enviar_mensaje_telegram("Hola", chat_id=42)

    assert capturado["data"]["chat_id"] == 42
