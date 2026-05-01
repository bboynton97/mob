from __future__ import annotations

from mob.art import ANIMALS, Animal


class TestAnimals:
    def test_has_animals(self):
        assert len(ANIMALS) >= 2

    def test_known_animals_exist(self):
        assert "frog" in ANIMALS
        assert "cat" in ANIMALS

    def test_all_have_required_poses(self):
        required = {"idle", "eating", "eating2", "sleeping", "blink", "happy"}
        for name, animal in ANIMALS.items():
            assert isinstance(animal, Animal)
            missing = required - set(animal.poses.keys())
            assert not missing, f"{name} is missing poses: {missing}"

    def test_poses_are_non_empty(self):
        for name, animal in ANIMALS.items():
            for pose_name, art in animal.poses.items():
                assert art.strip(), f"{name}.{pose_name} is empty"

    def test_width_is_positive(self):
        for animal in ANIMALS.values():
            assert animal.width > 0

    def test_frog_hops(self):
        assert ANIMALS["frog"].behavior.movement == "hop"
        assert "hop" in ANIMALS["frog"].poses

    def test_cat_crawls(self):
        cat = ANIMALS["cat"]
        assert cat.behavior.movement == "crawl"
        assert "walk_left" in cat.poses
        assert "walk_right" in cat.poses

    def test_cat_has_secondary_idles(self):
        cat = ANIMALS["cat"]
        assert cat.behavior.secondary_idles
        for idle in cat.behavior.secondary_idles:
            assert idle in cat.poses
