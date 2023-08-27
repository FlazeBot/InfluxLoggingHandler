# Standard library imports
import unittest

# Local application imports
from influx_logging_handler.utils import TagFilter


class TestTagFilter(unittest.TestCase):
    def test_bullshit(self) -> None:
        filter = TagFilter("and", "this is bullshit.")
        with self.assertRaises(AttributeError, msg="failed converting to string"):
            filter.to_string()

    def test_basic(self) -> None:
        filter = TagFilter("and", {"asd": "dsa"})
        self.assertEqual(
            filter.to_string(),
            'filter(fn: (r) => r["asd"] == "dsa")',
        )

        filter = TagFilter("and", {"dsa": "asd"})
        self.assertEqual(
            filter.to_string(),
            'filter(fn: (r) => r["dsa"] == "asd")',
        )

        filter = TagFilter("and", [{"asd": "dsa"}])
        self.assertEqual(
            filter.to_string(),
            'filter(fn: (r) => r["asd"] == "dsa")',
        )

        filter = TagFilter("and", {"asd": "dsa", "dsa": "asd"})
        self.assertEqual(
            filter.to_string(),
            'filter(fn: (r) => r["asd"] == "dsa" and r["dsa"] == "asd")',
        )

        filter = TagFilter("or", {"asd": "dsa", "dsa": "asd"})
        self.assertEqual(
            filter.to_string(),
            'filter(fn: (r) => r["asd"] == "dsa" or r["dsa"] == "asd")',
        )

    def test_combine(self) -> None:
        filter = TagFilter(
            "and",
            [{"asd": "dsa"}, TagFilter("or", {"asd": "dsa", "dsa": "asd"})],
        )
        self.assertEqual(
            filter.to_string(),
            'filter(fn: (r) => r["asd"] == "dsa" and ('
            'r["asd"] == "dsa" or r["dsa"] == "asd")'
            ")",
        )

        filter = TagFilter(
            "and",
            [
                TagFilter("and", {"asd": "dsa"}),
                TagFilter("or", {"asd": "dsa", "dsa": "asd"}),
            ],
        )
        self.assertEqual(
            filter.to_string(),
            'filter(fn: (r) => r["asd"] == "dsa" and ('
            'r["asd"] == "dsa" or r["dsa"] == "asd")'
            ")",
        )

    def test_realistic(self) -> None:
        filter = TagFilter(
            "and",
            [
                {"building": "c2c1bf16-bab9-4ca9-bd21-dad5084e1193"},
                TagFilter(
                    "or",
                    [
                        {"trait": "b5734a99-7737-4c39-bfe8-f7dcad33dc8c"},
                        {"trait": "57da1fa3-2742-43b0-9975-c234043a380d"},
                    ],
                ),
            ],
        )
        self.assertEqual(
            filter.to_string(),
            'filter(fn: (r) => r["building"] == "c2c1bf16-bab9-4ca9-bd21-dad5084e1193"'
            " and ("
            'r["trait"] == "b5734a99-7737-4c39-bfe8-f7dcad33dc8c" '
            'or r["trait"] == "57da1fa3-2742-43b0-9975-c234043a380d")'
            ")",
        )

        filter = TagFilter(
            "and",
            [
                {"building": "c2c1bf16-bab9-4ca9-bd21-dad5084e1193"},
                TagFilter(
                    "or",
                    [
                        {"trait": "b5734a99-7737-4c39-bfe8-f7dcad33dc8c"},
                        {"trait": "57da1fa3-2742-43b0-9975-c234043a380d"},
                    ],
                ),
            ],
        )
        self.assertEqual(
            filter.to_string(),
            'filter(fn: (r) => r["building"] == "c2c1bf16-bab9-4ca9-bd21-dad5084e1193"'
            " and ("
            'r["trait"] == "b5734a99-7737-4c39-bfe8-f7dcad33dc8c" '
            'or r["trait"] == "57da1fa3-2742-43b0-9975-c234043a380d")'
            ")",
        )
