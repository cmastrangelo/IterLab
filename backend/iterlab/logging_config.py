from __future__ import annotations

import logging
import sys

try:  # pythonjsonlogger>=3.1
    from pythonjsonlogger.json import JsonFormatter
except ImportError:  # pragma: no cover - older versions
    from pythonjsonlogger.jsonlogger import JsonFormatter


def configure_logging(level: str = "INFO", *, json: bool = True) -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    if json:
        handler.setFormatter(JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s"))
    root.addHandler(handler)
    root.setLevel(level.upper())
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
