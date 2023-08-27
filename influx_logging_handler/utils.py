# Standard library imports
import logging
from datetime import datetime, timezone
from math import ceil, floor
from typing import Dict, Generic, Iterator, List, Optional, TypeVar, Union

try:
    # Standard library imports
    from typing import Literal
except ImportError:  # pragma: no cover
    # Standard library imports
    import sys

    if sys.version_info < (3, 8):
        from typing_extensions import Literal

# Third party imports
from influxdb_client import InfluxDBClient
from influxdb_client.client.flux_table import FluxRecord
from influxdb_client.client.write_api import SYNCHRONOUS, WriteOptions

# Local folder imports
from .handlers import InfluxHandler

T = TypeVar("T")  # pylint: disable=invalid-name
TagDict = Dict[str, str]
TagFilterArgs = Union[Union[T, TagDict], List[Union[T, TagDict]]]


class TagFilter(Generic[T]):  # pylint: disable=too-few-public-methods
    def __init__(
        self,
        filter_type: Literal["and", "or"],
        filter_args: TagFilterArgs,
        _child: bool = False,
    ):
        self.filter_type = filter_type
        self.filter_args = filter_args
        self._child = _child

    def _dict_to_filter(self, filter_args: TagDict) -> str:
        return f" {self.filter_type} ".join(
            [f'r["{key}"] == "{value}"' for key, value in filter_args.items()]
        )

    def to_string(self, _child=None) -> str:
        child = _child or self._child

        if isinstance(self.filter_args, dict):
            if child:
                if len(self.filter_args.keys()) == 1:
                    return f"{self._dict_to_filter(self.filter_args)}"
                return f"({self._dict_to_filter(self.filter_args)})"
            return f"filter(fn: (r) => {self._dict_to_filter(self.filter_args)})"

        if isinstance(self.filter_args, list):
            filter_args = (" and " if self.filter_type == "and" else " or ").join(
                [
                    filter_args.to_string(_child=True)
                    if isinstance(filter_args, TagFilter)
                    else self._dict_to_filter(filter_args)  # type: ignore
                    for filter_args in self.filter_args
                ]
            )
            if child:
                return f"({filter_args})"
            return f"filter(fn: (r) => {filter_args})"

        raise AttributeError("failed converting to string")


class InfluxLogging:  # pylint: disable=too-many-instance-attributes
    def __init__(  # pylint: disable=too-many-arguments
        self,
        url: str,
        org: str,
        bucket: str,
        token: str,
        measurement: str = "logging",
        write_options: WriteOptions = SYNCHRONOUS,
    ) -> None:

        self.client = InfluxDBClient(url=url, token=token)
        self.query_api = self.client.query_api()
        self.url = url
        self.org = org
        self.bucket = bucket
        self.token = token
        self.measurement = measurement
        self.write_options = write_options
        self.handler: Optional[InfluxHandler] = None
        super().__init__()

    @staticmethod
    def __parse_filters(
        tag_filter: Optional[TagFilter] = None,
        **tag_filters: TagDict,
    ) -> Optional[str]:

        # If both are defined, assume AND
        if tag_filter and tag_filters:
            return TagFilter("and", [tag_filter, tag_filters]).to_string()

        return_value = tag_filter or tag_filters

        if return_value and isinstance(return_value, dict):
            return TagFilter("and", return_value).to_string()

        if isinstance(return_value, TagFilter):
            return return_value.to_string()

        return None

    def init_logging(self) -> None:
        log = logging.getLogger()
        self.handler = InfluxHandler(
            self.url,
            self.org,
            self.bucket,
            self.token,
            write_options=self.write_options,
        )
        log.addHandler(self.handler)

    def start_logging(self) -> None:
        return self.init_logging()

    def stop_logging(self):
        if self.handler:
            self.handler.flush()
            self.handler.close()

            log = logging.getLogger()
            log.removeHandler(self.handler)

            self.handler = None

    def query(
        self,
        query: Union[str, list],
        prefix: Optional[str] = None,
    ) -> Iterator[FluxRecord]:

        if isinstance(query, list):
            query = "\n".join(filter(None, query))

        if prefix is None and not query.startswith("from"):
            query = f'from(bucket: "{self.bucket}")\n{query}'

        for record in self.query_api.query_stream(query=query, org=self.org):
            yield record

    def get_last(
        self,
        count: int = 1,
        range_limit: str = "-24h",
        force_iterator: bool = False,
        tag_filter: TagFilter = None,
        **tag_filters: dict,
    ) -> Union[FluxRecord, None, Iterator[FluxRecord]]:

        filter_string = self.__parse_filters(tag_filter, **tag_filters)

        query = [
            f"|> range(start: {range_limit})",
            f'|> filter(fn: (r) => r["_measurement"] == "{self.measurement}")',
            f"|> {filter_string}" if filter_string else "",
            "|> pivot(",
            'rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value"',
            ")",
            "|> group()",
            f'|> top(n: {count}, columns: ["_time"])',
            '|> sort(columns: ["_time"])',
            "|> yield()",
        ]

        query_result = self.query(query)
        # If count == 1 and iterator hasn't been forced
        # -> return single value, defaulting to None
        if count == 1 and force_iterator is False:
            return next(query_result, None)

        return query_result

    def get_by_time(
        self,
        start: datetime,
        end: datetime = None,
        tag_filter: TagFilter = None,
        **tag_filters: dict,
    ) -> Iterator[FluxRecord]:

        if start.tzinfo is None:
            raise ValueError("datetimes must be timezone aware")

        if end is None:
            end = datetime.now(tz=timezone.utc)
        elif end.tzinfo is None:
            raise ValueError("datetimes must be timezone aware")

        filter_string = self.__parse_filters(tag_filter, **tag_filters)

        return self.query(
            [
                "|> range(",
                f"start: {floor(start.timestamp())}, ",
                f"stop: {ceil(end.timestamp())}",
                ")",
                f"|> {filter_string}" if filter_string else "",
                f'|> filter(fn: (r) => r["_measurement"] == "{self.measurement}")',
                "|> pivot("
                'rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value"',
                ")",
                "|> group()",
                '|> sort(columns: ["_time"])',
                "|> yield()",
            ]
        )
