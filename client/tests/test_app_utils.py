from __future__ import annotations

from mob.app import _hex_to_rgb, contrast_shift, format_gems, format_xp


class TestHexToRgb:
    def test_basic(self):
        assert _hex_to_rgb("#ff0000") == (255, 0, 0)

    def test_without_hash(self):
        assert _hex_to_rgb("00ff00") == (0, 255, 0)

    def test_mixed_case(self):
        assert _hex_to_rgb("#FFaa00") == (255, 170, 0)

    def test_black(self):
        assert _hex_to_rgb("#000000") == (0, 0, 0)

    def test_white(self):
        assert _hex_to_rgb("#ffffff") == (255, 255, 255)

    def test_invalid_length(self):
        assert _hex_to_rgb("#fff") is None

    def test_invalid_chars(self):
        assert _hex_to_rgb("#gggggg") is None

    def test_empty(self):
        assert _hex_to_rgb("") is None

    def test_whitespace_stripped(self):
        assert _hex_to_rgb("  #ff0000  ") == (255, 0, 0)


class TestContrastShift:
    def test_shift_toward_black(self):
        result = contrast_shift("#ffffff", "#000000", 0.5)
        assert result == "#808080"

    def test_shift_toward_white(self):
        result = contrast_shift("#000000", "#ffffff", 0.5)
        assert result == "#808080"

    def test_no_shift(self):
        result = contrast_shift("#ff0000", "#ff0000", 0.5)
        assert result == "#ff0000"

    def test_zero_amount(self):
        result = contrast_shift("#ff0000", "#000000", 0.0)
        assert result == "#ff0000"

    def test_full_amount(self):
        result = contrast_shift("#ff0000", "#000000", 1.0)
        assert result == "#000000"

    def test_none_bg_defaults_to_black(self):
        result = contrast_shift("#ffffff", None, 0.5)
        assert result == "#808080"

    def test_invalid_fg_returns_unchanged(self):
        assert contrast_shift("not-a-color", "#000000") == "not-a-color"


class TestFormatXp:
    def test_small_numbers(self):
        assert format_xp(0) == "0"
        assert format_xp(1) == "1"
        assert format_xp(999) == "999"

    def test_thousands(self):
        assert format_xp(1000) == "1.0k"
        assert format_xp(1500) == "1.5k"
        assert format_xp(10000) == "10k"
        assert format_xp(999999) == "999k"

    def test_millions(self):
        assert format_xp(1000000) == "1.0m"
        assert format_xp(5500000) == "5.5m"
        assert format_xp(10000000) == "10m"

    def test_billions(self):
        assert format_xp(1000000000) == "1.0b"
        assert format_xp(10000000000) == "10b"


class TestFormatGems:
    def test_whole_number(self):
        assert format_gems(10.0) == "10 gems"

    def test_zero(self):
        assert format_gems(0.0) == "0 gems"

    def test_fractional(self):
        assert format_gems(12.3) == "12.3 gems"

    def test_large_whole(self):
        assert format_gems(100.0) == "100 gems"
