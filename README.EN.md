# Buenos Aires Subway Alert Bot

Automated Telegram bot that monitors Buenos Aires subway line status and sends an alert only when a line changes state.

## How it works

- Connects to the public SignalR/SSE hub used by EMOVA's status page.
- Keeps one connection active during the service window.
- Reconnects with backoff up to 60 seconds.
- Reconciles the connection every 10 minutes (`600` seconds).
- Compares normalized snapshots by line and notifies only real changes.
- Stores the first clean-install snapshot without sending alerts.
- Reports a return to `Normal` as a change.
- Discards incomplete or invalid payloads.
- `/estado` reads the persisted snapshot and answers only the authorized chat.

The EMOVA source is not a documented public API. SignalR details are isolated in the source adapter so site changes do not leak into business logic.

## Service window

The process covers the conservative `05:30`–`02:30` window of the following day. This covers the broadest weekday, Saturday, Sunday, and holiday schedules shown by EMOVA, with a margin after the latest listed departure.

Outside that window the EMOVA connection is closed. The Telegram listener remains active.

## Persistence

The persisted file contains only the latest snapshot:

```json
{
  "ultima_actualizacion": "2026-09-11T12:00:00-03:00",
  "estados": {
    "A": {"original": "Normal", "canonico": "normal"}
  }
}
```

Writes are atomic. The previous format with `estados_actuales` and `historial` is migrated automatically; work and incident history is no longer used.

## Environment variables

- `TELEGRAM_TOKEN`: bot token. Required.
- `TELEGRAM_CHAT_ID`: authorized chat for alerts and commands. Required.
- `RECONCILIATION_INTERVAL_SECONDS`: SignalR reconciliation interval. Default `600`.
- `RECONNECT_MAX_SECONDS`: maximum reconnect backoff. Default `60`.
- `MARGEN_FIN_SERVICIO_MINUTOS`: margin after the latest departure. Default `60`.
- `COMANDO_ESTADO`: query command. Default `/estado`.
- `POLLING_TIMEOUT`: Telegram long-polling timeout. Default `25`.
- `POLLING_INTERVALO`: delay between Telegram cycles. Default `1`.

The application uses the `America/Argentina/Buenos_Aires` timezone.

## Development and execution

```bash
python -m pip install -r requirements.txt
python src/main.py
```

The Docker image does not require Chromium or ChromeDriver:

```bash
docker build -t bot-subte .
docker run --env-file .env -v "$PWD/src/data:/app/src/data" bot-subte
```

## Future sprint

`/horarios` will be implemented separately. It will return the first and last departure for each line and terminal according to the message date, including Sundays and holidays.

## Credits

- Developed by Agustin Monetti.
- Based on public information from EMOVA.
- GitHub: [@agmonetti](https://github.com/agmonetti)
- Email: agus.monetti01@gmail.com

Licensed under the GNU Affero General Public License v3.0.
