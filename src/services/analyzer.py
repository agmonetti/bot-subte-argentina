import re
import sys
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.config import Config


def normalizar_linea(nombre):
    """Convierte las etiquetas de EMOVA al identificador interno de línea."""
    texto = normalizar_texto(nombre)
    texto = re.sub(r"^línea\s+|^linea\s+", "", texto, flags=re.IGNORECASE)
    lineas = {linea.casefold(): linea for linea in Config.LINEAS}
    return lineas.get(texto, "")


def normalizar_texto(texto):
    """Normaliza formato sin borrar información del estado."""
    if not isinstance(texto, str):
        return ""
    texto = unicodedata.normalize("NFC", texto)
    return " ".join(texto.split()).casefold()


def normalizar_estados(estados):
    """Crea el snapshot comparable conservando el texto original."""
    resultado = {}
    if not isinstance(estados, dict):
        return resultado

    for linea, estado in estados.items():
        clave = normalizar_linea(linea)
        if clave and isinstance(estado, str) and estado.strip():
            original = " ".join(estado.split())
            resultado[clave] = {
                "original": original,
                "canonico": normalizar_texto(original),
            }
    return resultado


def snapshot_completo(estados):
    """Indica si el payload contiene exactamente todas las líneas esperadas."""
    return set(estados) == set(Config.LINEAS) and all(
        isinstance(valor, dict)
        and valor.get("original")
        and valor.get("canonico")
        for valor in estados.values()
    )


def excluir_estados_finalizados(actual, anterior):
    """No reemplaza un estado operativo por el cierre diario del servicio."""
    resultado = {}
    estado_finalizado = normalizar_texto(Config.ESTADO_REDUNDANTE)
    for linea, datos in actual.items():
        if datos.get("canonico") == estado_finalizado:
            if linea in anterior:
                resultado[linea] = anterior[linea]
            continue
        resultado[linea] = datos
    return resultado


def comparar_snapshots(actual, anterior):
    """Devuelve sólo las líneas cuyo estado canónico cambió."""
    cambios = {}
    for linea in Config.LINEAS:
        estado_actual = actual.get(linea)
        estado_anterior = anterior.get(linea)
        if not estado_actual:
            continue
        if not estado_anterior or estado_actual["canonico"] != estado_anterior.get("canonico"):
            cambios[linea] = {
                "anterior": estado_anterior.get("original") if estado_anterior else None,
                "actual": estado_actual["original"],
            }
    return cambios
