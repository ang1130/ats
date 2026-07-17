"""Deterministic provenance helpers for preliminary ATS PoC artifacts."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Mapping, Sequence

SCHEMA_VERSION = "preliminary-ats-poc-v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def _git(root: Path, *args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), *args], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def git_info(root: Path) -> dict:
    return {
        "revision": _git(root, "rev-parse", "HEAD"),
        "dirty": bool(_git(root, "status", "--porcelain")),
    }


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def build_provenance(
    root: Path,
    entry_script: Path,
    seed: int,
    deadline_profile: str,
    config_paths: Sequence[Path],
    source_paths: Iterable[Path],
    argv: Sequence[str],
) -> dict:
    """Return serializable, deterministic metadata for a simulation artifact."""
    config_hashes = {
        _relative(root, path): sha256_file(path)
        for path in sorted(config_paths, key=lambda item: str(item))
    }
    source_hashes = {
        _relative(root, path): sha256_file(path)
        for path in sorted(set(source_paths), key=lambda item: str(item))
    }
    fingerprint_input = {
        "schema_version": SCHEMA_VERSION,
        "entry_script": _relative(root, entry_script),
        "seed": seed,
        "deadline_profile": deadline_profile,
        "config_sha256": config_hashes,
        "source_sha256": source_hashes,
        "argv": list(argv),
        "git": git_info(root),
        "runtime": {
            "python": platform.python_version(),
            "simpy": package_version("simpy"),
            "pyyaml": package_version("PyYAML"),
        },
    }
    encoded = json.dumps(fingerprint_input, sort_keys=True, separators=(",", ":")).encode()
    return {
        **fingerprint_input,
        "run_id": hashlib.sha256(encoded).hexdigest()[:16],
    }


def same_experiment_inputs(left: Mapping, right: Mapping) -> bool:
    """Compare the fields that must match when reusing an offline grid result."""
    return all(
        left.get(key) == right.get(key)
        for key in ("seed", "deadline_profile", "config_sha256")
    )
