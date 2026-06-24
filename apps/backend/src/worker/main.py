"""Worker-process Procrastinate app (runs jobs).

Launched by the Procrastinate CLI:

    procrastinate --app=src.worker.main.app worker

Uses the async :class:`~procrastinate.PsycopgConnector` (psycopg3) — the only
connector that can *run* a worker. The web process never imports this module, so
psycopg3's async machinery stays out of the request-serving import graph.
"""

from procrastinate import App, PsycopgConnector

from src.app.settings import settings
from src.worker.tasks import PROCESS_UPLOAD, process_upload_task

app = App(connector=PsycopgConnector(conninfo=settings.psycopg_conninfo))

# Bind the task body (a plain function in tasks.py) onto this app. Registered
# here rather than with an inline @app.task so the body stays importable without
# this module's async connector.
app.task(name=PROCESS_UPLOAD)(process_upload_task)
