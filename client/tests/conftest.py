from __future__ import annotations

import pytest


@pytest.fixture()
def config_dir(tmp_path, monkeypatch):
    """Redirect all mob config files to a temp directory."""
    mob_dir = tmp_path / "mob"
    mob_dir.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return mob_dir
