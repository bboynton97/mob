from __future__ import annotations

import json

from mob import xp


class TestLoad:
    def test_returns_zero_when_no_file(self, config_dir):
        assert xp.load("frog") == 0

    def test_returns_zero_for_bad_json(self, config_dir):
        (config_dir / "xp.json").write_text("garbage")
        assert xp.load("frog") == 0

    def test_returns_zero_for_non_dict(self, config_dir):
        (config_dir / "xp.json").write_text("[1]")
        assert xp.load("frog") == 0

    def test_returns_zero_for_missing_animal(self, config_dir):
        (config_dir / "xp.json").write_text(json.dumps({"cat": 100}))
        assert xp.load("frog") == 0

    def test_returns_zero_for_negative(self, config_dir):
        (config_dir / "xp.json").write_text(json.dumps({"frog": -5}))
        assert xp.load("frog") == 0

    def test_returns_zero_for_string_value(self, config_dir):
        (config_dir / "xp.json").write_text(json.dumps({"frog": "lots"}))
        assert xp.load("frog") == 0

    def test_loads_valid_xp(self, config_dir):
        (config_dir / "xp.json").write_text(json.dumps({"frog": 42}))
        assert xp.load("frog") == 42


class TestSave:
    def test_round_trip(self, config_dir):
        xp.save("frog", 100)
        assert xp.load("frog") == 100

    def test_clamps_negative(self, config_dir):
        xp.save("frog", -50)
        assert xp.load("frog") == 0

    def test_multiple_animals(self, config_dir):
        xp.save("frog", 10)
        xp.save("cat", 20)
        assert xp.load("frog") == 10
        assert xp.load("cat") == 20

    def test_overwrites_previous(self, config_dir):
        xp.save("frog", 10)
        xp.save("frog", 50)
        assert xp.load("frog") == 50

    def test_preserves_other_animals(self, config_dir):
        xp.save("frog", 10)
        xp.save("cat", 20)
        xp.save("frog", 99)
        assert xp.load("cat") == 20
