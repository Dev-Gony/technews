import unittest

import numpy as np

import bgm


class BgmTest(unittest.TestCase):
    def test_length_and_peak(self):
        samples = bgm.generate_bgm(10.0, seed="2026-11-03")

        self.assertEqual(len(samples), int(10.0 * bgm.SAMPLE_RATE))
        self.assertLessEqual(np.max(np.abs(samples)), 0.9 + 1e-9)
        self.assertGreater(np.max(np.abs(samples)), 0.5)

    def test_same_seed_same_music(self):
        a = bgm.generate_bgm(5.0, seed="2026-11-03")
        b = bgm.generate_bgm(5.0, seed="2026-11-03")

        np.testing.assert_array_equal(a, b)

    def test_fades_in_and_out(self):
        samples = bgm.generate_bgm(8.0, seed="2026-11-04")

        self.assertEqual(samples[0], 0)
        self.assertAlmostEqual(samples[-1], 0, places=6)


if __name__ == "__main__":
    unittest.main()
