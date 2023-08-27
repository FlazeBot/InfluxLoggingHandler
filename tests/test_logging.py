# Standard library imports
import logging
import sys
import time
import unittest
from datetime import datetime
from pathlib import Path
from typing import Optional

# Third party imports
from influxdb_client import InfluxDBClient
from influxdb_client.client.flux_table import FluxRecord

# Local application imports
from influx_logging_handler.handlers import InfluxHandler

MAX_WAIT = 30
PYTHON_37 = sys.version_info < (3, 8)


class TestLogging(unittest.TestCase):
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
        log = logging.getLogger()
        self.handler = InfluxHandler(
            self.url,
            self.org,
            test_bucket_name,
            self.token,
        )
        log.addHandler(self.handler)
        return super().setUp()

    def tearDown(self) -> None:
        self.handler.flush()
        self.handler.close()
        log = logging.getLogger()
        log.removeHandler(self.handler)
        self.client.buckets_api().delete_bucket(self.test_bucket)
        return super().tearDown()

    def get_last(self, field: str = "") -> Optional[FluxRecord]:
        query = [
            f'from(bucket: "{self.test_bucket.name}")',
            "|> range(start: -1h)",
            "|> last()",
        ]

        if field:
            query.insert(2, f'|> filter(fn: (r) => r._field == "{field}")')

        return next(
            self.client.query_api().query_stream(
                "\n".join(query),
                org=self.org,
            ),
            None,
        )

    def test_basic(self) -> None:
        log = logging.getLogger("basic")
        log.setLevel(logging.DEBUG)

        now = datetime.now().timestamp()
        log.info("a very basic log message")

        last_message = self.get_last()
        self.assertIsNotNone(last_message)
        self.assertAlmostEqual(last_message.get_time().timestamp(), now, 1)
        self.assertEqual(last_message.get_field(), "message")
        self.assertEqual(last_message.get_value(), "a very basic log message")
        self.assertEqual(last_message.values["logger"], "basic")
        self.assertEqual(last_message.values["function_name"], "test_basic")
        self.assertEqual(last_message.values["filename"], "test_logging.py")
        self.assertEqual(last_message.values["level"], "INFO")
        self.assertEqual(last_message.values["level_number"], "20")
        self.assertEqual(last_message.values["line_number"], "94")

    def test_tags(self) -> None:
        log = logging.getLogger("tags")
        log.setLevel(logging.DEBUG)

        now = datetime.now().timestamp()
        log.info(
            "a very basic log message with tags",
            extra={
                "tags": {
                    "asd": "dsa",
                    "dsa": "asd",
                },
            },
        )

        last_message = self.get_last()
        self.assertIsNotNone(last_message)
        self.assertAlmostEqual(last_message.get_time().timestamp(), now, 1)
        self.assertEqual(last_message.get_field(), "message")
        self.assertEqual(last_message.get_value(), "a very basic log message with tags")
        self.assertEqual(last_message.values["function_name"], "test_tags")
        self.assertEqual(last_message.values["filename"], "test_logging.py")
        self.assertEqual(last_message.values["level"], "INFO")
        self.assertEqual(last_message.values["level_number"], "20")
        self.assertEqual(
            last_message.values["line_number"],
            "118" if PYTHON_37 else "113",
        )
        self.assertEqual(last_message.values["asd"], "dsa")
        self.assertEqual(last_message.values["dsa"], "asd")

    def test_exception(self) -> None:
        log = logging.getLogger("tags")
        log.setLevel(logging.DEBUG)

        try:
            raise ValueError("a planned ValueError")
        except ValueError:
            now = datetime.now().timestamp()
            log.exception(
                "a very basic log message with tags",
                extra={
                    "tags": {
                        "asd": "dsa",
                        "dsa": "asd",
                    },
                },
            )

        last_message = self.get_last()
        self.assertIsNotNone(last_message)
        self.assertAlmostEqual(last_message.get_time().timestamp(), now, 1)
        self.assertEqual(last_message.get_field(), "message")
        self.assertEqual(last_message.get_value(), "a very basic log message with tags")
        self.assertEqual(last_message.values["function_name"], "test_exception")
        self.assertEqual(last_message.values["filename"], "test_logging.py")
        self.assertEqual(last_message.values["level"], "ERROR")
        self.assertEqual(last_message.values["level_number"], "40")
        self.assertEqual(last_message.values["exception_type"], "ValueError")
        self.assertEqual(
            last_message.values["line_number"],
            "152" if PYTHON_37 else "147",
        )
        self.assertEqual(last_message.values["exception"], "1")
        self.assertEqual(last_message.values["asd"], "dsa")
        self.assertEqual(last_message.values["dsa"], "asd")

        last_message = self.get_last("traceback")
        self.assertEqual(last_message.get_field(), "traceback")
        self.assertEqual(
            last_message.get_value(),
            f'File "{Path(__file__)}", '
            f"line {144 if PYTHON_37 else 144}, in test_exception\r\n"
            '    raise ValueError("a planned ValueError")',
        )
