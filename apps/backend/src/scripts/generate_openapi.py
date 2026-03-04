import json
from pathlib import Path

from src.app.main import create_app

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "__generated__" / "openapi.json"

app = create_app()

SCHEMA_PATH.write_text(json.dumps(app.openapi(), indent=2) + "\n")

print(f"OpenAPI schema written to {SCHEMA_PATH}")
