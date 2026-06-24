"""Worker-process Procrastinate app (runs jobs).

Launched by the Procrastinate CLI:

    procrastinate --app=src.worker.main.app worker

Uses the async :class:`~procrastinate.PsycopgConnector` (psycopg3) — the only
connector that can *run* a worker. The web process never imports this module, so
psycopg3's async machinery stays out of the request-serving import graph.
"""

from procrastinate import App, PsycopgConnector

from src.app.settings import settings
from src.worker.tasks import NAMESPACE, blueprint

app = App(connector=PsycopgConnector(conninfo=settings.psycopg_conninfo))
app.add_tasks_from(blueprint, namespace=NAMESPACE)
