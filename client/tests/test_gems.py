from __future__ import annotations

import json

from mob import gems


class TestLoad:
    def test_returns_zero_when_no_file(self, config_dir):
        assert gems.load() == 0.0

    def test_returns_zero_for_bad_json(self, config_dir):
        (config_dir / "gems.json").write_text("not json")
        assert gems.load() == 0.0

    def test_returns_zero_for_non_dict(self, config_dir):
        (config_dir / "gems.json").write_text("[1,2,3]")
        assert gems.load() == 0.0

    def test_returns_zero_for_negative(self, config_dir):
        (config_dir / "gems.json").write_text(json.dumps({"gems": -5}))
        assert gems.load() == 0.0

    def test_returns_zero_for_missing_key(self, config_dir):
        (config_dir / "gems.json").write_text(json.dumps({"other": 10}))
        assert gems.load() == 0.0

    def test_returns_zero_for_string_value(self, config_dir):
        (config_dir / "gems.json").write_text(json.dumps({"gems": "ten"}))
        assert gems.load() == 0.0

    def test_loads_integer(self, config_dir):
        (config_dir / "gems.json").write_text(json.dumps({"gems": 42}))
        assert gems.load() == 42.0

    def test_loads_float(self, config_dir):
        (config_dir / "gems.json").write_text(json.dumps({"gems": 12.3}))
        assert gems.load() == 12.3

    def test_rounds_to_one_decimal(self, config_dir):
        (config_dir / "gems.json").write_text(json.dumps({"gems": 12.3456}))
        assert gems.load() == 12.3


class TestSave:
    def test_round_trip(self, config_dir):
        gems.save(45.7)
        assert gems.load() == 45.7

    def test_clamps_negative_to_zero(self, config_dir):
        gems.save(-10.0)
        assert gems.load() == 0.0

    def test_rounds_on_save(self, config_dir):
        gems.save(3.14159)
        assert gems.load() == 3.1

    def test_creates_parent_dirs(self, tmp_path, monkeypatch):
        deep = tmp_path / "deep" / "nested"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(deep))
        gems.save(5.0)
        assert gems.load() == 5.0

    def test_overwrites_previous(self, config_dir):
        gems.save(10.0)
        gems.save(20.0)
        assert gems.load() == 20.0
