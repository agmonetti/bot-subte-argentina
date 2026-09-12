import html
import json
import logging
import re
from datetime import date
from pathlib import Path

import holidays


LOGGER = logging.getLogger(__name__)
ARCHIVO_HORARIOS = Path(__file__).resolve().parents[1] / "resources" / "horarios.json"
CALENDARIO_FERIADOS = holidays.country_holidays(
    "AR",
    categories=holidays.PUBLIC,
    observed=True,
    language="es",
)

_DIAS = ("habil", "sabado", "domingo_feriado")
_GRUPOS_ESPERADOS = (
    ("A", None),
    ("B", None),
    ("C", None),
    ("D", None),
    ("E", None),
    ("H", None),
    ("Premetro", "Centro Cívico"),
    ("Premetro", "General Savio"),
)
_HORA_RE = re.compile(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]")
_INDISPONIBLE = "No se pudieron cargar los horarios programados en este momento."
_PIE = (
    "Horarios programados según la tabla de referencia. "
    "Consultá los avisos del servicio para cambios operativos."
)


def cargar_horarios() -> dict:
    """Lee y valida el catálogo empaquetado de horarios."""
    with ARCHIVO_HORARIOS.open("r", encoding="utf-8") as archivo:
        datos = json.load(archivo)
    _validar_catalogo(datos)
    return datos


def tipo_dia(fecha: date) -> str:
    """Devuelve la columna aplicable para una fecha local del calendario."""
    if not isinstance(fecha, date):
        raise ValueError("La fecha debe ser un objeto date")
    if fecha.weekday() == 6 or fecha in CALENDARIO_FERIADOS:
        return "domingo_feriado"
    if fecha.weekday() == 5:
        return "sabado"
    return "habil"


def obtener_respuesta_horarios(fecha: date) -> str:
    """Construye la respuesta completa o informa indisponibilidad sin parcialidades."""
    try:
        catalogo = cargar_horarios()
        columna = tipo_dia(fecha)
        respuesta = _formatear_respuesta(catalogo, fecha, columna)
        if len(respuesta) >= 4096:
            raise ValueError("La respuesta de horarios excede el límite de Telegram")
        return respuesta
    except (OSError, json.JSONDecodeError, ValueError):
        LOGGER.exception("No se pudo cargar o validar el catálogo de horarios")
    except Exception:
        LOGGER.exception("No se pudo determinar el calendario de horarios")
    return _INDISPONIBLE


def _validar_catalogo(datos):
    if not isinstance(datos, dict) or set(datos) != {"lineas"}:
        raise ValueError("El catálogo debe contener únicamente lineas")
    grupos = datos["lineas"]
    if not isinstance(grupos, list) or len(grupos) != len(_GRUPOS_ESPERADOS):
        raise ValueError("El catálogo debe contener ocho grupos")

    vistos = []
    for grupo, esperado in zip(grupos, _GRUPOS_ESPERADOS):
        if not isinstance(grupo, dict) or set(grupo) != {"linea", "ramal", "cabeceras"}:
            raise ValueError("Grupo de línea inválido")
        identidad = (grupo["linea"], grupo["ramal"])
        if identidad != esperado or identidad in vistos:
            raise ValueError("Grupos de línea inválidos o duplicados")
        vistos.append(identidad)
        cabeceras = grupo["cabeceras"]
        if not isinstance(cabeceras, list) or len(cabeceras) != 2:
            raise ValueError("Cada grupo debe tener dos cabeceras")
        for cabecera in cabeceras:
            _validar_cabecera(cabecera)


def _validar_cabecera(cabecera):
    if not isinstance(cabecera, dict) or set(cabecera) != {
        "nombre",
        "habil",
        "sabado",
        "domingo_feriado",
    }:
        raise ValueError("Cabecera inválida")
    if not isinstance(cabecera["nombre"], str) or not cabecera["nombre"].strip():
        raise ValueError("La cabecera debe tener un nombre")
    for dia in _DIAS:
        horarios = cabecera[dia]
        if not isinstance(horarios, dict) or set(horarios) != {"primero", "ultimo"}:
            raise ValueError("Horario diario inválido")
        for hora in horarios.values():
            if not isinstance(hora, str) or not _HORA_RE.fullmatch(hora):
                raise ValueError("Hora inválida")


def _formatear_respuesta(catalogo, fecha, columna):
    nombres_dia = {
        "habil": "lunes a viernes",
        "sabado": "sábado",
        "domingo_feriado": "domingo/feriado",
    }
    partes = [
        f"Horarios del subte — {fecha:%d/%m/%Y} ({nombres_dia[columna]})",
        "",
    ]
    for grupo in catalogo["lineas"]:
        titulo = grupo["linea"]
        if grupo["ramal"]:
            titulo += f" — {grupo['ramal']}"
        partes.append(f"<b>{html.escape(titulo)}</b>")
        for cabecera in grupo["cabeceras"]:
            horarios = cabecera[columna]
            marca = " (día siguiente)" if _es_dia_siguiente(horarios) else ""
            nombre = html.escape(cabecera["nombre"])
            partes.append(
                f"{nombre}: primero {html.escape(horarios['primero'])} · "
                f"último {html.escape(horarios['ultimo'])}{marca}"
            )
        partes.append("")

    if columna == "habil" and fecha.weekday() in (4, 5):
        partes.extend(
            [
                "Línea B — horario extendido viernes y sábado: último tren desde "
                "J. M. de Rosas 01:00 y desde Leandro N. Alem 01:30 (día siguiente).",
                "",
            ]
        )
    partes.append(_PIE)
    return "\n".join(partes)


def _es_dia_siguiente(horarios):
    primero = _minutos(horarios["primero"])
    ultimo = _minutos(horarios["ultimo"])
    return ultimo < primero


def _minutos(hora):
    horas, minutos = hora.split(":")
    return int(horas) * 60 + int(minutos)
