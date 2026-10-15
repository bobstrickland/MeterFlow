from datetime import datetime, timezone
from dataclasses import dataclass
from enum import StrEnum
from typing import Self
from pydantic import (AwareDatetime, BaseModel, ConfigDict, Field,
                      field_validator, model_validator)

class ReadType(StrEnum):
    ACTUAL="ACTUAL"
    ESTIMATED="ESTIMATED"

class QualityFlag(StrEnum):
    OK="OK"
    SUSPECT="SUSPECT"
    FILLED="FILLED"

class MeterReading(BaseModel):
    model_config=ConfigDict(frozen=True, extra="forbid")

    reading_id:str = Field(min_length=1)
    meter_id:str = Field(min_length=1)
    interval_start: AwareDatetime
    register_kwh:float = Field(ge=0, allow_inf_nan=False)
    read_type:ReadType
    received_at:AwareDatetime
    gateway_id:str = Field(min_length=1)
    gateway_seq:int = Field(ge=0)
    quality_flag: QualityFlag
    schema_version:int = Field(ge=1)

    @field_validator("interval_start", "received_at")
    @classmethod
    def to_utc(cls, v:datetime) -> datetime:
        return v.astimezone(timezone.utc)

    @field_validator("interval_start")
    @classmethod
    def on_quarter_hour(cls, v:datetime):
        if v.minute % 15 != 0:
            raise ValueError("Interval start must fall on 15-minute boundry.")
        return v

    @model_validator(mode="after")
    def consistency_check(self) -> Self:
        if self.reading_id != f"{self.meter_id}|{self.interval_start:%Y-%m-%dT%H:%M:%SZ}|kWh" :
            raise ValueError(f"Reading ID should be: {self.meter_id}|{self.interval_start:%Y-%m-%dT%H:%M:%SZ}|kWh")
        if (self.received_at < self.interval_start):
            raise ValueError("Interval Start should be before Reveived At")
        return self

@dataclass(frozen=True, slots=True)
class InvalidMeterReading:
    reading_id:str
    row:str
    error:str


@dataclass(frozen=True)
class MeterAccount:
    meter_id:str
    account_number:str
    rate_plan:str
    effective_date:datetime
    effective_to:datetime


    
