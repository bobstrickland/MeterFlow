import csv
from collections.abc import Iterable, Iterator
from itertools import islice
from pathlib import Path
from meterflow.meter_reading import MeterReading, InvalidMeterReading, ReadType, QualityFlag
from datetime import datetime


def read_rows(path: Path) -> Iterator[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)

def parse(rows: Iterable[dict[str, str]]) -> Iterator[MeterReading|InvalidMeterReading]:
    for row in rows:
        try:
            yield MeterReading(reading_id=row["reading_id"]
                ,meter_id=row["meter_id"]
                ,interval_start=datetime.fromisoformat(row["interval_start"])
                ,register_kwh=float(row["register_kwh"])
                ,read_type=ReadType(row["read_type"])
                ,received_at=datetime.fromisoformat(row["received_at"])
                ,gateway_id=row["gateway_id"]
                ,gateway_seq=int(row["gateway_seq"])
                ,quality_flag=QualityFlag(row["quality_flag"])
                ,schema_version=int(row["schema_version"])
            )
        except ValueError as e:
            yield InvalidMeterReading(row["reading_id"], str(row), str(e))

def batches[T](items: Iterable[T], size: int) -> Iterator[list[T]]:
    it = iter(items)
    while batch := list(islice(it, size)):
        yield batch
