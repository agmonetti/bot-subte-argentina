import json
import os
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.config import Config
from src.services.analyzer import normalizar_linea, normalizar_texto


def _migrar_estados(data):
    """Convierte el formato histórico y el formato actual a un snapshot común."""
    estados = data.get("estados")
    if isinstance(estados, dict):
        resultado = {}
        for linea, valor in estados.items():
            clave = normalizar_linea(linea)
            if isinstance(valor, dict):
                original = valor.get("original", "")
                canonico = valor.get("canonico") or normalizar_texto(original)
            else:
                original = str(valor)
                canonico = normalizar_texto(original)
            if clave and original.strip():
                resultado[clave] = {
                    "original": original.strip(),
                    "canonico": canonico,
                }
        return resultado

    estados_anteriores = data.get("estados_actuales", {})
    if not isinstance(estados_anteriores, dict):
        return {}

    resultado = {}
    for linea, estado in estados_anteriores.items():
        clave = normalizar_linea(linea)
        if clave and isinstance(estado, str) and estado.strip():
            resultado[clave] = {
                "original": estado.strip(),
                "canonico": normalizar_texto(estado),
            }
    return resultado


def cargar_snapshot():
    """Lee el snapshot actual y migra transparentemente el formato anterior."""
    try:
        if not Config.ARCHIVO_ESTADO.exists():
            return {}
        with Config.ARCHIVO_ESTADO.open("r", encoding="utf-8") as archivo:
            data = json.load(archivo)
        if not isinstance(data, dict):
            return {}
        estados = _migrar_estados(data)
        if not estados:
            return {}
        return {
            "ultima_actualizacion": data.get("ultima_actualizacion"),
            "estados": estados,
        }
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        print(f"Error de I/O al cargar estados: {error}")
        return {}


def guardar_snapshot(estados, fecha_actualizacion):
    """Guarda un snapshot completo mediante reemplazo atómico."""
    data = {
        "ultima_actualizacion": fecha_actualizacion,
        "estados": estados,
    }
    Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporal = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=Config.DATA_DIR,
            prefix=f"{Config.ARCHIVO_ESTADO.name}.",
            suffix=".tmp",
            delete=False,
        ) as archivo:
            temporal = Path(archivo.name)
            json.dump(data, archivo, indent=2, ensure_ascii=False)
            archivo.flush()
            os.fsync(archivo.fileno())
        os.replace(temporal, Config.ARCHIVO_ESTADO)
    except (OSError, TypeError, ValueError) as error:
        if temporal:
            temporal.unlink(missing_ok=True)
        print(f"Error de I/O al guardar estados: {error}")
