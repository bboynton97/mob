from __future__ import annotations

import json

from mob.decorations import (
    CATALOG,
    Decoration,
    load_equipped,
    load_positions,
    load_purchased,
    save_position,
    save_purchase,
    toggle_equip,
)


class TestCatalog:
    def test_has_items(self):
        assert len(CATALOG) > 0

    def test_all_have_required_fields(self):
        for deco in CATALOG.values():
            assert isinstance(deco, Decoration)
            assert deco.id
            assert deco.name
            assert deco.cost > 0
            assert deco.art.strip()

    def test_known_items_exist(self):
        for item_id in ("yarn", "plant", "fish", "bed"):
            assert item_id in CATALOG

    def test_costs_are_positive(self):
        for deco in CATALOG.values():
            assert deco.cost > 0


class TestPurchased:
    def test_empty_when_no_file(self, config_dir):
        assert load_purchased() == []

    def test_bad_json(self, config_dir):
        (config_dir / "decorations.json").write_text("nope")
        assert load_purchased() == []

    def test_filters_unknown_ids(self, config_dir):
        (config_dir / "decorations.json").write_text(
            json.dumps({"purchased": ["yarn", "fake_item"]})
        )
        assert load_purchased() == ["yarn"]

    def test_filters_non_strings(self, config_dir):
        (config_dir / "decorations.json").write_text(
            json.dumps({"purchased": ["yarn", 123, None]})
        )
        assert load_purchased() == ["yarn"]


class TestSavePurchase:
    def test_saves_and_loads(self, config_dir):
        save_purchase("yarn")
        assert "yarn" in load_purchased()

    def test_auto_equips(self, config_dir):
        save_purchase("plant")
        assert "plant" in load_equipped()

    def test_no_duplicates(self, config_dir):
        save_purchase("yarn")
        save_purchase("yarn")
        assert load_purchased().count("yarn") == 1

    def test_multiple_items(self, config_dir):
        save_purchase("yarn")
        save_purchase("plant")
        purchased = load_purchased()
        assert "yarn" in purchased
        assert "plant" in purchased


class TestEquipped:
    def test_empty_when_no_file(self, config_dir):
        assert load_equipped() == []

    def test_must_be_purchased(self, config_dir):
        (config_dir / "decorations.json").write_text(
            json.dumps({"equipped": ["yarn"], "purchased": []})
        )
        assert load_equipped() == []

    def test_filters_unknown(self, config_dir):
        (config_dir / "decorations.json").write_text(
            json.dumps({"equipped": ["fake"], "purchased": ["fake"]})
        )
        assert load_equipped() == []


class TestToggleEquip:
    def test_unequips_equipped(self, config_dir):
        save_purchase("yarn")
        assert "yarn" in load_equipped()
        result = toggle_equip("yarn")
        assert result is False
        assert "yarn" not in load_equipped()

    def test_re_equips(self, config_dir):
        save_purchase("yarn")
        toggle_equip("yarn")
        result = toggle_equip("yarn")
        assert result is True
        assert "yarn" in load_equipped()


class TestPositions:
    def test_empty_when_no_file(self, config_dir):
        assert load_positions() == {}

    def test_save_and_load(self, config_dir):
        save_position("yarn", 15, 3)
        pos = load_positions()
        assert pos["yarn"] == (15, 3)

    def test_backwards_compat_int_position(self, config_dir):
        (config_dir / "decorations.json").write_text(
            json.dumps({"positions": {"yarn": 10}})
        )
        pos = load_positions()
        assert pos["yarn"] == (10, 0)

    def test_list_position(self, config_dir):
        (config_dir / "decorations.json").write_text(
            json.dumps({"positions": {"yarn": [5, 2]}})
        )
        pos = load_positions()
        assert pos["yarn"] == (5, 2)

    def test_overwrites_previous(self, config_dir):
        save_position("yarn", 5, 0)
        save_position("yarn", 20, 1)
        assert load_positions()["yarn"] == (20, 1)
