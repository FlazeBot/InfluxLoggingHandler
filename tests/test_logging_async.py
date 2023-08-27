# Standard library imports
import logging
import time
from typing import Optional

# Third party imports
from influxdb_client.client.flux_table import FluxRecord
from influxdb_client.client.write_api import ASYNCHRONOUS

# Local application imports
from influx_logging_handler.handlers import InfluxHandler

# Local folder imports
from .test_logging import TestLogging


class TestAsyncLogging(TestLogging):
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
            write_options=ASYNCHRONOUS,
        )
        log.addHandler(self.handler)

    def get_last(self, field: str = "") -> Optional[FluxRecord]:
        time.sleep(0.1)
        return super().get_last(field=field)
