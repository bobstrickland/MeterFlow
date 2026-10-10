import sys
import json
from dataclasses import asdict
from pathlib import Path
from meterflow.meter_reading import MeterReading, InvalidMeterReading
from meterflow.streaming import read_rows, parse, batches


valid_path:Path = Path("valid.csv")
error_path:Path = Path("errors.txt")

def appendLine(fileName:Path, line:str):
    with open(fileName, "a", encoding="utf-8") as f:
        f.write(f"{line}\n")


def validate():
    if (valid_path):
        valid_path.unlink()
    if (error_path):
        error_path.unlink()
    file_path:Path = Path("output.csv")
    rows = read_rows(file_path)
    meter_iterator = parse(rows)
    for batch in batches(meter_iterator, 5):
        for meter_reading in batch:
            match meter_reading:
                case MeterReading():
                    appendLine(valid_path, meter_reading.model_dump_json())
                case InvalidMeterReading():
                    appendLine(error_path, json.dumps(asdict(meter_reading)))
                case _:
                    print ("somethign else?")


if __name__ == "__main__":
    sys.exit(validate())