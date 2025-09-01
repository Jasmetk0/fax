from django.test import TestCase

from msa.services.draw import _seed_map_for_draw


class SnakePairingNonPow2Tests(TestCase):
    def test_seed_maps_48_56(self):
        m48, _, _ = _seed_map_for_draw(48, 16)
        m56, _, _ = _seed_map_for_draw(56, 16)
        expected = {1: 1, 2: 64, 3: 32, 4: 33}
        for k, v in expected.items():
            self.assertEqual(m48[k], v)
            self.assertEqual(m56[k], v)
