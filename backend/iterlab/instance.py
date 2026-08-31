"""Deployment-specific ("instance") configuration.

IterLab ships nothing about any particular external system. A deployment adds
its private wiring under an *instance directory* that is entirely git-ignored:

    instance/
      .env                 # secrets (DSNs, tokens) — loaded into the environment
      labs/*.yaml          # lab definitions provisioned into the database
      adapters/*.py        # optional custom BenchmarkAdapter plugins

Nothing here references the instance directory's contents; it only discovers and
loads whatever is present.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
from pathlib import Path

from iterlab.config import get_settings

logger = logging.getLogger("iterlab.instance")

_REPO_ROOT = Path(__file__).resolve().parents[2]


def get_instance_dir() -> Path | None:
    settings = get_settings()
    if settings.instance_dir:
        path = Path(settings.instance_dir).expanduser().resolve()
        return path if path.is_dir() else None
    default = _REPO_ROOT / "instance"
    return default if default.is_dir() else None


def load_instance_env(instance_dir: Path) -> None:
    """Load ``instance/.env`` into ``os.environ`` (does not overwrite existing)."""
    env_file = instance_dir / ".env"
    if not env_file.is_file():
        return
    loaded = 0
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)
        loaded += 1
    logger.info("loaded %d vars from %s", loaded, env_file)


def load_instance_plugins(instance_dir: Path) -> None:
    """Import every ``adapters/*.py`` so custom adapters self-register.

    The adapters directory is put on ``sys.path`` and each module is imported
    under its bare name (``locm_steps``) — not a synthetic package — so that
    functions defined in a plugin can be pickled for multiprocessing (child
    processes re-import ``locm_steps`` from ``sys.path``).
    """
    adapters_dir = instance_dir / "adapters"
    if not adapters_dir.is_dir():
        return
    dir_str = str(adapters_dir)
    if dir_str not in sys.path:
        sys.path.insert(0, dir_str)
    for module_path in sorted(adapters_dir.glob("*.py")):
        if module_path.name.startswith("_"):
            continue
        mod_name = module_path.stem
        spec = importlib.util.spec_from_file_location(mod_name, module_path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = module
        try:
            spec.loader.exec_module(module)
            logger.info("loaded instance adapter plugin: %s", module_path.name)
        except Exception:  # noqa: BLE001
            sys.modules.pop(mod_name, None)
            logger.exception("failed to load instance adapter %s", module_path)


def initialize_instance() -> Path | None:
    """Discover the instance dir, load its env + adapter plugins. Returns the dir."""
    instance_dir = get_instance_dir()
    if instance_dir is None:
        logger.info("no instance directory found — running without instance config")
        return None
    logger.info("using instance directory: %s", instance_dir)
    load_instance_env(instance_dir)
    load_instance_plugins(instance_dir)
    return instance_dir
