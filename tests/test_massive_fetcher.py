import unittest

from _paths import add_work_board_repo

add_work_board_repo()

from data_plane.prefetch.massive_fetcher import _agg_to_dict


class MassiveFetcherTests(unittest.TestCase):
    def test_agg_to_dict_preserves_raw_dict_values(self):
        row = {"o": 1.0, "h": 2.0, "l": 0.5, "c": 1.5, "v": 100, "t": 123}

        self.assertEqual(_agg_to_dict(row), row)

    def test_agg_to_dict_maps_object_attributes(self):
        class Agg:
            open = 1.0
            high = 2.0
            low = 0.5
            close = 1.5
            volume = 100
            timestamp = 123

        mapped = _agg_to_dict(Agg())

        self.assertEqual(mapped["o"], 1.0)
        self.assertEqual(mapped["h"], 2.0)
        self.assertEqual(mapped["l"], 0.5)
        self.assertEqual(mapped["c"], 1.5)
        self.assertEqual(mapped["v"], 100)
        self.assertEqual(mapped["t"], 123)


if __name__ == "__main__":
    unittest.main()
