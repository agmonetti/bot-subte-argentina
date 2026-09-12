import os
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    RECONCILIATION_INTERVAL_SECONDS = int(
        os.getenv("RECONCILIATION_INTERVAL_SECONDS", 600)
    )
    RECONNECT_MAX_SECONDS = int(os.getenv("RECONNECT_MAX_SECONDS", 60))
    MARGEN_FIN_SERVICIO_MINUTOS = int(
        os.getenv("MARGEN_FIN_SERVICIO_MINUTOS", 60)
    )

    COMANDO_ESTADO = os.getenv("COMANDO_ESTADO", "/estado")
    POLLING_TIMEOUT = int(os.getenv("POLLING_TIMEOUT", 25))
    POLLING_INTERVALO = int(os.getenv("POLLING_INTERVALO", 1))

    URL_ESTADO_SUBTE = (
        "https://aplicacioneswp.metrovias.com.ar/estadolineasEMOVA/desktopEmova.html"
    )
    URL_SIGNALR = (
        "https://aplicacioneswp.metrovias.com.ar/estadolineasEMOVA/signalr"
    )
    SIGNALR_HUB = "signalremova"
    EVENTO_ESTADO = "estadoLineas"
    ESTADO_NORMAL = "Normal"
    ESTADO_REDUNDANTE = "Servicio finalizado"
    LINEAS = ("A", "B", "C", "D", "E", "H", "Premetro")
    TIMEZONE_LOCAL = ZoneInfo("America/Argentina/Buenos_Aires")

    DATA_DIR = BASE_DIR / "src" / "data"
    ARCHIVO_ESTADO = DATA_DIR / "estados_persistentes.json"

    @classmethod
    def validate(cls):
        """Verifica requerimientos críticos y prepara el entorno."""
        if not cls.TELEGRAM_TOKEN or not cls.TELEGRAM_CHAT_ID:
            print("Error crítico: TELEGRAM_TOKEN o TELEGRAM_CHAT_ID no definidos en el .env")
            sys.exit(1)

        if cls.RECONCILIATION_INTERVAL_SECONDS <= 0:
            raise ValueError("RECONCILIATION_INTERVAL_SECONDS debe ser positivo")
        if cls.RECONNECT_MAX_SECONDS <= 0:
            raise ValueError("RECONNECT_MAX_SECONDS debe ser positivo")

        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)


Config.validate()
