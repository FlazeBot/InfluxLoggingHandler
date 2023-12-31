# Standard library imports
import logging
import traceback
from typing import Any, Iterator, Tuple

# Third party imports
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS, WriteOptions


class InfluxHandler(logging.Handler):
    def __init__(
            self,
            url: str,
            org: str,
            bucket: str,
            token: str,
            measurement: str = "logging",
            flaze: bool = False,
            bot: str = None,
            shard_id: str = None,
            write_options: WriteOptions = SYNCHRONOUS,
    ) -> None:
        self.flaze = flaze
        self.client = InfluxDBClient(url=url, token=token)
        self.write_api = self.client.write_api(write_options=write_options)
        self.org = org
        self.bucket = bucket
        self.bot = bot
        self.shard_id = shard_id
        self.measurement = measurement
        super().__init__()

    @staticmethod
    def _get_additional_tags(record: logging.LogRecord) -> Iterator[Tuple[str, Any]]:
        if "tags" in record.__dict__ and isinstance(record.__dict__["tags"], dict):
            for key, value in record.__dict__["tags"].items():
                yield (key, value)

    def emit(self, record: logging.LogRecord) -> None:
        if not self.flaze:
            point = (
                Point(self.measurement)
                .tag("logger", record.name)
                .tag("level", record.levelname)
                .tag("level_number", record.levelno)
                .tag("filename", record.filename)
                .tag("line_number", record.lineno)
                .tag("function_name", record.funcName)
                .field("message", record.getMessage())
                .time(
                    int(record.created * 1e6),
                    write_precision=WritePrecision.US,
                )
            )
        else:
            exception = record.exc_info
            if exception:
                custom_msg = f"""[{record.asctime}] [{record.levelname:<8}] {record.name}: {record.getMessage()}\n""".join(traceback.format_exception(exception[0], value=exception[1], tb=exception[2])).strip()
                point = (
                    Point(self.measurement)
                    .tag("bot", self.bot)
                    .tag("shard_id", self.shard_id)
                    .tag("exception_type", exception[1].__class__.__name__)
                    .field("message", custom_msg)
                    .time(
                        int(record.created * 1e6),
                        write_precision=WritePrecision.US,
                    )
                )
            else:
                custom_msg = f"""[{record.asctime}] [{record.levelname:<8}] {record.name}: {record.getMessage()}"""
                point = (
                    Point(self.measurement)
                    .tag("bot", self.bot)
                    .tag("shard_id", self.shard_id)
                    .field("message", custom_msg)
                    .time(
                        int(record.created * 1e6),
                        write_precision=WritePrecision.US,
                    )
                )

        for tag, value in self._get_additional_tags(record):
            point = point.tag(tag, value)

        self.write_api.write(self.bucket, self.org, point)

    def flush(self) -> None:
        self.write_api.flush()
        return super().flush()

    def close(self) -> None:
        self.write_api.close()
        return super().close()
