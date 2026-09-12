import math
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.config import Config
from src.services.telegram_notifier import enviar_mensaje_telegram
from src.services.scrapper import EmovaSignalRSource, EmovaSourceError
from src.services.horarios import obtener_respuesta_horarios


def _estados_originales(snapshot):
    estados = snapshot.get("estados", {}) if isinstance(snapshot, dict) else {}
    resultado = {}
    for linea in Config.LINEAS:
        datos = estados.get(linea)
        if isinstance(datos, dict) and datos.get("original"):
            resultado[linea] = datos["original"]
        elif isinstance(datos, str) and datos.strip():
            resultado[linea] = datos.strip()
    return resultado


def _formatear_ultima_actualizacion(valor):
    try:
        fecha = datetime.fromisoformat(valor) if isinstance(valor, str) else valor
        if not isinstance(fecha, datetime):
            return str(valor)
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=Config.TIMEZONE_LOCAL)
        return fecha.astimezone(Config.TIMEZONE_LOCAL).strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError, OverflowError):
        return str(valor)

def formatear_estado_actual(snapshot):
    """Formatea un snapshot de estado."""
    estados = _estados_originales(snapshot)
    mensaje = "Estado del Subte de Buenos Aires\n\n"
    for linea in Config.LINEAS:
        estado = estados.get(linea, "sin datos disponibles")
        mensaje += f"<b>{linea}:</b> {estado}\n"

    actualizado = snapshot.get("ultima_actualizacion") if isinstance(snapshot, dict) else None
    if actualizado:
        mensaje += f"\nÚltima actualización: {_formatear_ultima_actualizacion(actualizado)}"
    return mensaje


def obtener_respuesta_estado():
    """Consulta EMOVA y devuelve el estado observado en ese momento."""
    try:
        estados = EmovaSignalRSource().obtener_estado()
    except EmovaSourceError as error:
        print(f"Error al consultar el estado actual de EMOVA: {error}")
        return "No se pudo obtener el estado del subte en este momento."

    snapshot = {
        "ultima_actualizacion": datetime.now(Config.TIMEZONE_LOCAL).isoformat(),
        "estados": estados,
    }
    return formatear_estado_actual(snapshot)


def obtener_updates(offset):
    """Long-polling de la API de Telegram."""
    url = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/getUpdates"
    params = {"offset": offset, "timeout": Config.POLLING_TIMEOUT}
    response = requests.get(url, params=params, timeout=Config.POLLING_TIMEOUT + 10)
    response.raise_for_status()
    return response.json()


def _chat_autorizado(chat_id):
    return chat_id is not None and str(chat_id) == str(Config.TELEGRAM_CHAT_ID)


def _fecha_del_mensaje(mensaje):
    valor = mensaje.get("date") if isinstance(mensaje, dict) else None
    try:
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise ValueError("timestamp ausente o inválido")
        if not math.isfinite(valor):
            raise ValueError("timestamp no finito")
        return datetime.fromtimestamp(valor, Config.TIMEZONE_LOCAL).date()
    except (ValueError, OverflowError, OSError, TypeError):
        return datetime.now(Config.TIMEZONE_LOCAL).date()



def escuchar_comandos():
    """Escucha comandos sin consultar EMOVA desde el listener de Telegram."""
    offset = None
    while True:
        try:
            data = obtener_updates(offset)
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                mensaje = update.get("message", {})
                texto = mensaje.get("text", "").strip()
                chat_id = mensaje.get("chat", {}).get("id")
                if not _chat_autorizado(chat_id):
                    continue
                comando = texto.split(maxsplit=1)[0] if texto else ""
                if comando == Config.COMANDO_ESTADO:
                    enviar_mensaje_telegram(obtener_respuesta_estado(), chat_id=chat_id)
                elif comando == "/horarios":
                    fecha = _fecha_del_mensaje(mensaje)
                    enviar_mensaje_telegram(
                        obtener_respuesta_horarios(fecha),
                        chat_id=chat_id,
                    )
        except requests.exceptions.RequestException as error:
            print(f"Error de red al consultar comandos de Telegram: {error}")
        except Exception as error:
            print(f"Error inesperado al escuchar comandos: {error}")

        time.sleep(Config.POLLING_INTERVALO)
