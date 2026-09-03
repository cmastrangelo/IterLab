"""Register a lab's prompt version files, refusing any change to an existing one.

Layout (under the instance directory)::

    prompts/<lab-slug>/<prompt-slug>/v0.md
    prompts/<lab-slug>/<prompt-slug>/v1.md
    ...

Each file is one immutable version. On sync we:
  - register any version not yet in the database
  - verify every already-registered version is byte-identical to its file
  - never update or delete a Prompt row

If a file for an existing version has been edited, that is *drift*: we log a
loud error, leave the registered text untouched, and (by default) keep going so
the rest of the deployment still boots. Set ``ITERLAB_PROMPT_DRIFT_FATAL=1`` to
turn drift into a hard startup failure instead.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from iterlab.models.lab import Lab
from iterlab.models.prompt import Prompt

logger = logging.getLogger("iterlab.prompts")

_VFILE = re.compile(r"v(\d+)\.md")
_DRIFT_FATAL = os.environ.get("ITERLAB_PROMPT_DRIFT_FATAL", "").lower() in {"1", "true", "yes"}


class PromptDrift(RuntimeError):
    """An already-registered prompt version's file was changed."""


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


async def sync_lab_prompts(
    session: AsyncSession, lab: Lab, instance_dir: Path | None
) -> dict[str, list[int]]:
    """Register/verify prompt version files for ``lab``.

    Returns ``{slug: [versions...]}`` actually present in the database afterwards.
    """
    registered: dict[str, list[int]] = {}
    if instance_dir is None:
        return registered
    root = instance_dir / "prompts" / lab.slug
    if not root.is_dir():
        return registered

    drift: list[str] = []
    for slug_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        slug = slug_dir.name
        files: dict[int, Path] = {}
        for f in slug_dir.iterdir():
            m = _VFILE.fullmatch(f.name)
            if m and f.is_file():
                files[int(m.group(1))] = f
        if not files:
            continue

        existing = {
            p.version: p
            for p in await session.scalars(
                select(Prompt).where(Prompt.lab_id == lab.id, Prompt.slug == slug)
            )
        }
        for version in sorted(files):
            text = files[version].read_text()
            digest = _digest(text)
            prior = existing.get(version)
            if prior is None:
                session.add(
                    Prompt(
                        lab_id=lab.id, slug=slug, version=version, text=text, digest=digest
                    )
                )
                existing[version] = Prompt(  # local marker; real flush below
                    lab_id=lab.id, slug=slug, version=version, text=text, digest=digest
                )
                logger.info("registered prompt %s/%s v%d", lab.slug, slug, version)
            elif prior.digest != digest:
                nxt = max(files) + 1
                drift.append(
                    f"{lab.slug}/{slug} v{version}: file no longer matches the "
                    f"registered version — prompt versions are immutable. Revert "
                    f"{files[version]} or add v{nxt}.md."
                )
        registered[slug] = sorted(existing)

    await session.flush()
    if drift:
        msg = "prompt drift detected:\n  - " + "\n  - ".join(drift)
        if _DRIFT_FATAL:
            raise PromptDrift(msg)
        logger.error("%s\n(runs keep using the registered text; set "
                     "ITERLAB_PROMPT_DRIFT_FATAL=1 to make this fatal)", msg)
    return registered
