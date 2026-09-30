"""PROGRAM_VERSION stays a semantic version and matches pyproject.toml."""

from __future__ import annotations

from pathlib import Path
import re
import tomllib

from lupaxa.github_token_validator.constants import PROGRAM_VERSION

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")


def test_program_version_matches_semver() -> None:
    assert _SEMVER.fullmatch(PROGRAM_VERSION)


def test_pyproject_version_matches_program_version() -> None:
    path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    with path.open("rb") as handle:
        version = tomllib.load(handle)["project"]["version"]
    assert isinstance(version, str)
    assert _SEMVER.fullmatch(version)
    assert version == PROGRAM_VERSION
