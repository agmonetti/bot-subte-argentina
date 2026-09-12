from src.config import Config
from src.services.analyzer import (
    comparar_snapshots,
    excluir_estados_finalizados,
    normalizar_estados,
    normalizar_linea,
    normalizar_texto,
    snapshot_completo,
)


ESTADOS_NORMALES = {linea: "Normal" for linea in Config.LINEAS}


def test_normaliza_etiquetas_y_conserva_texto_original():
    estados = normalizar_estados({"Linea A": "  Estación   Medrano cerrada  "})

    assert normalizar_linea("LÍNEA a") == "A"
    assert estados["A"] == {
        "original": "Estación Medrano cerrada",
        "canonico": "estación medrano cerrada",
    }


def test_snapshot_completo_requiere_las_siete_lineas():
    assert snapshot_completo(normalizar_estados(ESTADOS_NORMALES))
    assert not snapshot_completo(normalizar_estados({"A": "Normal"}))


def test_mismo_estado_no_genera_cambio_por_espacios():
    anterior = normalizar_estados({"A": "Normal", "B": "Demora por incidente"})
    actual = normalizar_estados({"A": " normal ", "B": "Demora   por incidente"})

    assert comparar_snapshots(actual, anterior) == {}


def test_cambio_a_normal_y_cambio_de_incidente_se_detectan():
    anterior = normalizar_estados({"A": "Demora", "B": "Normal"})
    actual = normalizar_estados({"A": "Normal", "B": "Demora por incidente"})

    cambios = comparar_snapshots(actual, anterior)

    assert cambios == {
        "A": {"anterior": "Demora", "actual": "Normal"},
        "B": {"anterior": "Normal", "actual": "Demora por incidente"},
    }


def test_estado_finalizado_no_reemplaza_estado_operativo():
    anterior = normalizar_estados({"A": "Demora"})
    actual = normalizar_estados({"A": Config.ESTADO_REDUNDANTE})

    resultado = excluir_estados_finalizados(actual, anterior)

    assert resultado["A"] == anterior["A"]


def test_normaliza_texto_sin_eliminar_informacion():
    assert normalizar_texto(" C. de Tucumán — obras ") == "c. de tucumán — obras"
