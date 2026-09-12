import sys
import threading
from datetime import datetime, time as hora, timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.config import Config
from src.services.analyzer import (
    comparar_snapshots,
    excluir_estados_finalizados,
    snapshot_completo,
)
from src.services.scrapper import EmovaSignalRSource
from src.services.storage import cargar_snapshot, guardar_snapshot
from src.services.telegram_notifier import enviar_alerta_cambios
from src.services.telegram_bot import escuchar_comandos


# Ventana conservadora: cubre los horarios más amplios de la tabla, incluidos
# feriados, sin necesitar una lista local que pueda quedar desactualizada.
INICIO_MONITOREO = hora(5, 30)
FIN_SERVICIO_MAS_TARDE = 90  # 01:30 del día siguiente, sábado.


def fin_monitoreo_minutos():
    return FIN_SERVICIO_MAS_TARDE + Config.MARGEN_FIN_SERVICIO_MINUTOS


def ventana_operativa(ahora=None):
    """Indica si la hora pertenece a la ventana diaria de servicio."""
    ahora = ahora or datetime.now(Config.TIMEZONE_LOCAL)
    minutos = ahora.hour * 60 + ahora.minute
    inicio = INICIO_MONITOREO.hour * 60 + INICIO_MONITOREO.minute
    fin = fin_monitoreo_minutos()
    return minutos >= inicio or minutos < fin


def segundos_hasta_apertura(ahora=None):
    """Calcula el sueño hasta las 05:30 locales siguientes."""
    ahora = ahora or datetime.now(Config.TIMEZONE_LOCAL)
    apertura = ahora.replace(
        hour=INICIO_MONITOREO.hour,
        minute=INICIO_MONITOREO.minute,
        second=0,
        microsecond=0,
    )
    if ahora >= apertura:
        apertura += timedelta(days=1)
    return max(1, (apertura - ahora).total_seconds())


def procesar_estado(estados_actuales, fecha_actualizacion):
    """Compara, persiste y notifica un snapshot válido de EMOVA."""
    if not snapshot_completo(estados_actuales):
        print("Payload incompleto de EMOVA; se descarta sin notificar.")
        return

    data_anterior = cargar_snapshot()
    anterior = data_anterior.get("estados", {})
    estados_operativos = excluir_estados_finalizados(estados_actuales, anterior)
    if not snapshot_completo(estados_operativos):
        print("Snapshot operativo incompleto de EMOVA; se descarta sin notificar.")
        return

    guardar_snapshot(estados_operativos, fecha_actualizacion.isoformat())
    if not anterior:
        print("Snapshot inicial guardado; no se envían alertas.")
        return

    cambios = comparar_snapshots(estados_operativos, anterior)
    if cambios:
        enviar_alerta_cambios(cambios, fecha_actualizacion)
        print(f"Actualización enviada para: {', '.join(cambios)}")
    else:
        print("Estado sin cambios; no se envía alerta.")


def main():
    """Ejecuta Telegram y el listener persistente de EMOVA."""
    print("Iniciando servicio Bot-Subte...")
    stop_event = threading.Event()
    hilo_bot = threading.Thread(target=escuchar_comandos, daemon=True)
    hilo_bot.start()

    fuente = EmovaSignalRSource()
    espera_reconexion = 5
    while not stop_event.is_set():
        if not ventana_operativa():
            espera = segundos_hasta_apertura()
            print(f"Fuera de la ventana operativa. Durmiendo {espera / 3600:.2f} horas.")
            stop_event.wait(espera)
            espera_reconexion = 5
            continue

        try:
            fuente.escuchar(
                procesar_estado,
                duracion=Config.RECONCILIATION_INTERVAL_SECONDS,
                stop_event=stop_event,
            )
            espera_reconexion = 5
        except Exception as error:
            print(f"Error en el ciclo SignalR: {error}")
            if stop_event.wait(espera_reconexion):
                break
            espera_reconexion = min(
                espera_reconexion * 2, Config.RECONNECT_MAX_SECONDS
            )


if __name__ == "__main__":
    main()
