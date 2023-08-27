# Standard library imports
import logging
import sys
import time
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

# Third party imports
from influxdb_client import InfluxDBClient

# Local application imports
from influx_logging_handler.utils import InfluxLogging, TagFilter

MAX_WAIT = 30
PYTHON_37 = sys.version_info < (3, 8)


class TestFetching(unittest.TestCase):
    url = "http://influxdb:8086"
    org = "testing"
    token = (
        "D_ongyBJAhWCckWehz4TDyuJnhgnl1zB9OVBNfbq0CN8"
        "Tal_BmbAO6u8_zKtxg1n_7y1V-0BNfDbhvs6JylcRA=="
    )

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = InfluxDBClient(url=cls.url, token=cls.token)

        i = 1
        while cls.client.ready().status != "ready":
            print(f"Waiting for InfluxDB to be ready {i}/{MAX_WAIT}...")
            i += 1
            time.sleep(1.0)

        i = 1
        while not cls.client.organizations_api().find_organizations(org=cls.org):
            print(f"Waiting for InfluxDB organization {i}/{MAX_WAIT}...")
            i += 1
            time.sleep(1.0)

        return super().setUpClass()

    def setUp(self) -> None:
        test_bucket_name = f"testing-{int(time.time() * 1e6)}"
        self.test_bucket = self.client.buckets_api().create_bucket(
            bucket_name=test_bucket_name,
            org=self.org,
        )

        self.logging = InfluxLogging(
            self.url,
            self.org,
            test_bucket_name,
            self.token,
        )
        self.logging.start_logging()

        return super().setUp()

    def tearDown(self) -> None:
        self.logging.stop_logging()
        self.client.buckets_api().delete_bucket(self.test_bucket)

        return super().tearDown()

    def test_stop_logging_without_init(self) -> None:
        self.logging.stop_logging()

    def test_basic_fetching(self) -> None:
        log = logging.getLogger("test_basic_fetching")
        log.setLevel(logging.DEBUG)

        start = datetime.now(tz=timezone.utc)
        log.debug("test1.")
        log.info("test2.")
        log.error("test3.")
        self.logging.handler.flush()

        self.assertEqual(self.logging.get_last()["message"], "test3.")
        self.assertEqual(
            [record["message"] for record in self.logging.get_last(3)],
            ["test1.", "test2.", "test3."],
        )
        self.assertEqual(
            [record["level"] for record in self.logging.get_last(3)],
            ["DEBUG", "INFO", "ERROR"],
        )

        self.assertEqual(
            [record["message"] for record in self.logging.get_by_time(start=start)],
            ["test1.", "test2.", "test3."],
        )
        self.assertEqual(
            [record["level"] for record in self.logging.get_by_time(start=start)],
            ["DEBUG", "INFO", "ERROR"],
        )

        with self.assertRaises(ValueError, msg="datetimes must be timezone aware"):
            self.assertEqual(
                [
                    record["message"]
                    for record in self.logging.get_by_time(
                        start=start.replace(tzinfo=None)
                    )
                ],
                ["test1.", "test2.", "test3."],
            )

        self.assertEqual(
            [
                record["message"]
                for record in self.logging.get_by_time(
                    start=start, end=datetime.now(tz=timezone.utc)
                )
            ],
            ["test1.", "test2.", "test3."],
        )

        with self.assertRaises(ValueError, msg="datetimes must be timezone aware"):
            self.assertEqual(
                [
                    record["message"]
                    for record in self.logging.get_by_time(
                        start=start, end=datetime.now()
                    )
                ],
                ["test1.", "test2.", "test3."],
            )

        self.assertEqual(
            [
                record["message"]
                for record in self.logging.get_by_time(
                    start=datetime.now(tz=timezone.utc) - timedelta(seconds=10),
                    end=datetime.now(tz=timezone.utc) - timedelta(seconds=2),
                )
            ],
            [],
        )

    def test_realistic(self) -> None:
        log = logging.getLogger("test_realistic")
        log.setLevel(logging.DEBUG)
        extra = {"tags": {"building": "c2c1bf16-bab9-4ca9-bd21-dad5084e1193"}}

        start = datetime.now(tz=timezone.utc)
        log.debug("test1.")
        log.info("test2.")
        log.error("test3.")
        log.debug("test1.", extra=extra)
        log.info("test2.", extra=extra)
        log.error("test3.", extra=extra)
        self.logging.handler.flush()

        self.assertEqual(
            [record["level"] for record in self.logging.get_last(3)],
            ["DEBUG", "INFO", "ERROR"],
        )
        self.assertEqual(
            [record["level"] for record in self.logging.get_last(6)],
            ["DEBUG", "INFO", "ERROR", "DEBUG", "INFO", "ERROR"],
        )

        self.assertEqual(
            [
                record["level"]
                for record in self.logging.get_last(
                    30,
                    building="c2c1bf16-bab9-4ca9-bd21-dad5084e1193",
                )
            ],
            ["DEBUG", "INFO", "ERROR"],
        )

        self.assertEqual(
            [
                record["level"]
                for record in self.logging.get_last(
                    30,
                    tag_filter=TagFilter(
                        "and", {"building": "c2c1bf16-bab9-4ca9-bd21-dad5084e1193"}
                    ),
                )
            ],
            ["DEBUG", "INFO", "ERROR"],
        )

        self.assertEqual(
            [
                (record["message"], record["level"])
                for record in self.logging.get_last(
                    30,
                    building="c2c1bf16-bab9-4ca9-bd21-dad5084e1193",
                    level="INFO",
                )
            ],
            [("test2.", "INFO")],
        )

        self.assertEqual(
            [
                record["level"]
                for record in self.logging.get_by_time(
                    start=start,
                    building="c2c1bf16-bab9-4ca9-bd21-dad5084e1193",
                )
            ],
            ["DEBUG", "INFO", "ERROR"],
        )

        self.assertEqual(
            [
                (record["message"], record["level"])
                for record in self.logging.get_by_time(
                    start=start,
                    building="c2c1bf16-bab9-4ca9-bd21-dad5084e1193",
                    level="INFO",
                )
            ],
            [("test2.", "INFO")],
        )

        self.assertEqual(
            [
                (record["message"], record["level"])
                for record in self.logging.get_by_time(
                    start=start,
                    building="c2c1bf16-bab9-4ca9-bd21-dad5084e1193",
                    tag_filter=TagFilter("and", {"level": "INFO"}),
                )
            ],
            [("test2.", "INFO")],
        )

    def test_realistic_2(self) -> None:
        log = logging.getLogger("test_realistic_2")
        log.setLevel(logging.DEBUG)

        start = datetime.now(tz=timezone.utc)

        for i in range(10):
            building = f"{uuid4()}"

            for j in range(1, 10):
                trait = f"{uuid4()}"
                extra = {"tags": {"building": building, "trait": trait}}

                log.info("test", extra=extra)

                self.logging.handler.flush()

                self.assertEqual(
                    len(list(self.logging.get_by_time(start=start, trait=trait))),
                    1,
                )

                self.assertEqual(
                    len(
                        list(
                            self.logging.get_by_time(
                                start=start, building=building, trait=trait
                            )
                        )
                    ),
                    1,
                )

                self.assertEqual(
                    len(
                        list(
                            self.logging.get_by_time(
                                start=start,
                                building=building,
                            )
                        )
                    ),
                    j,
                )

                self.assertEqual(
                    len(
                        list(
                            self.logging.get_by_time(
                                start=start,
                            )
                        )
                    ),
                    i * 9 + j,
                )

    def test_fulfill_stupid_100_percent_requirement(self) -> None:
        log = logging.getLogger("test_fulfill_stupid_100_percent_requirement")
        log.setLevel(logging.DEBUG)

        log.debug("test1.")
        self.logging.handler.flush()

        self.assertEqual(
            len(list(self.logging.query("|> range(start: -1m)\n|> yield()"))),
            1,
        )

        self.assertEqual(
            len(
                list(
                    self.logging.query(
                        f'from(bucket: "{self.test_bucket.name}")\n'
                        "|> range(start: -1m)\n|> yield()"
                    )
                )
            ),
            1,
        )
