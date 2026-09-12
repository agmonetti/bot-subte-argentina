# Bot de Alertas del Subte de Buenos Aires

Bot automatizado que monitorea el estado de las líneas del subte de Buenos Aires y envía alertas a Telegram únicamente cuando cambia el estado de una línea.

## Funcionamiento

- La fuente de estados es el canal público SignalR/SSE de EMOVA, el mismo que alimenta la página `https://aplicacioneswp.metrovias.com.ar/estadolineasEMOVA/desktopEmova.html`.
- El adaptador escucha el evento `estadoLineas`, extrae las siete líneas y compara cada snapshot normalizado.
- Mantiene una conexión persistente durante la ventana operativa del servicio.
- Reintenta conexiones con backoff de hasta 60 segundos.
- Resincroniza cada 10 minutos (`600` segundos).
- Telegram es únicamente el canal de salida y de comandos (`/estado`, `/horarios`); el bot no lee mensajes de Telegram como fuente de estados.
- La página pública de EMOVA no muestra las alertas ni los mensajes enviados por el bot: son dos superficies independientes.
- Envía alertas sólo cuando cambia el estado canónico de una línea; un snapshot idéntico recibido diez minutos después no genera otra publicación.
- El primer snapshot después de una instalación limpia se persiste sin notificar.
- El regreso de una línea a `Normal` sí genera una actualización.
- Un payload incompleto o inválido se descarta para evitar falsas alertas.
- `/estado` responde desde el snapshot persistido y sólo al chat autorizado.

La fuente de EMOVA no es una API pública documentada. El adaptador SignalR está aislado para que un cambio del sitio no afecte la lógica de negocio.

## Ventana operativa

El proceso cubre la ventana conservadora `05:30`–`02:30` del día siguiente. Esto incluye los horarios más amplios de lunes a viernes, sábados, domingos y feriados, con margen sobre la última salida mostrada por EMOVA.

Fuera de esa ventana se cierra la conexión con EMOVA. El listener de Telegram permanece activo.

## Arquitectura

```text
├── src/
│   ├── config.py
│   ├── main.py                 # Scheduler, comparación y orquestación
│   ├── data/
│   │   └── estados_persistentes.json
│   └── services/
│       ├── analyzer.py         # Normalización y comparación de snapshots
│       ├── scrapper.py         # Cliente SignalR/SSE y parser HTML
│       ├── storage.py          # Persistencia atómica y migración
│       ├── telegram_bot.py     # Long-polling y /estado cacheado
│       └── telegram_notifier.py
├── Dockerfile
└── requirements.txt
```

## Persistencia

El archivo contiene sólo el último snapshot:

```json
{
  "ultima_actualizacion": "2026-09-11T12:00:00-03:00",
  "estados": {
    "A": {"original": "Normal", "canonico": "normal"}
  }
}
```

Las escrituras son atómicas. El formato anterior con `estados_actuales` e `historial` se migra automáticamente; el historial de obras y problemas deja de utilizarse.

## Variables de entorno

- `TELEGRAM_TOKEN`: token del bot. Requerido.
- `TELEGRAM_CHAT_ID`: chat autorizado para alertas y comandos. Requerido.
- `RECONCILIATION_INTERVAL_SECONDS`: resincronización SignalR. Por defecto `600`.
- `RECONNECT_MAX_SECONDS`: máximo del backoff de reconexión. Por defecto `60`.
- `MARGEN_FIN_SERVICIO_MINUTOS`: margen posterior a la última salida. Por defecto `60`.
- `COMANDO_ESTADO`: comando de consulta. Por defecto `/estado`.
- `POLLING_TIMEOUT`: timeout del long-polling de Telegram. Por defecto `25`.
- `POLLING_INTERVALO`: espera entre ciclos de Telegram. Por defecto `1`.

La zona horaria usada es `America/Argentina/Buenos_Aires`.

## Desarrollo y ejecución

```bash
python -m pip install -r requirements.txt
python src/main.py
```

El despliegue Docker no requiere Chromium ni ChromeDriver:

```bash
docker build -t bot-subte .
docker run --env-file .env -v "$PWD/src/data:/app/src/data" bot-subte
```

## Próximo sprint

Se implementará `/horarios` por separado. Devolverá la primera y última salida de cada línea y cabecera según el día del mensaje, incluyendo domingos y feriados.

## Créditos

- Desarrollado por Agustin Monetti.
- Basado en información pública de EMOVA.
- GitHub: [@agmonetti](https://github.com/agmonetti).
  
Este proyecto está licenciado bajo GNU Affero General Public License v3.0.
