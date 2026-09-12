import html
import sys
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.config import Config


def enviar_mensaje_telegram(mensaje, chat_id=None):
    """Ejecuta la petición HTTP contra la API de Telegram."""
    url = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id or Config.TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        print("Notificación enviada exitosamente a Telegram.")
        return response
    except requests.exceptions.RequestException as error:
        print(f"Error de red al notificar por Telegram: {error}")
    except Exception as error:
        print(f"Error inesperado en notificador de Telegram: {error}")
    return None


def enviar_alerta_cambios(cambios, fecha_actualizacion):
    """Notifica juntas las líneas modificadas en un snapshot."""
    if not cambios:
        return

    mensaje = "Estado del Subte de Buenos Aires\n\n"
    for linea, cambio in cambios.items():
        estado = html.escape(cambio["actual"])
        mensaje += f"<b>{html.escape(linea)}:</b> {estado}\n"
    mensaje += (
        "\nActualización: "
        f"{fecha_actualizacion.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    return enviar_mensaje_telegram(mensaje)
