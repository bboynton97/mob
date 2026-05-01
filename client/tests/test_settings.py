from __future__ import annotations

import json

from mob import settings


class TestGetSet:
    def test_default_when_no_file(self, config_dir):
        assert settings.get("missing") is None

    def test_custom_default(self, config_dir):
        assert settings.get("missing", 42) == 42

    def test_round_trip_string(self, config_dir):
        settings.set("name", "whiskers")
        assert settings.get("name") == "whiskers"

    def test_round_trip_int(self, config_dir):
        settings.set("count", 7)
        assert settings.get("count") == 7

    def test_round_trip_bool(self, config_dir):
        settings.set("flag", True)
        assert settings.get("flag") is True

    def test_round_trip_list(self, config_dir):
        settings.set("items", [1, 2, 3])
        assert settings.get("items") == [1, 2, 3]

    def test_overwrites_previous(self, config_dir):
        settings.set("key", "old")
        settings.set("key", "new")
        assert settings.get("key") == "new"

    def test_multiple_keys(self, config_dir):
        settings.set("a", 1)
        settings.set("b", 2)
        assert settings.get("a") == 1
        assert settings.get("b") == 2

    def test_bad_json_returns_default(self, config_dir):
        (config_dir / "settings.json").write_text("not json")
        assert settings.get("key", "fallback") == "fallback"

    def test_non_dict_returns_default(self, config_dir):
        (config_dir / "settings.json").write_text('"just a string"')
        assert settings.get("key") is None
