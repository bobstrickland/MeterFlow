import random
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, TimestampType, Row
from meterflow.meter_reading import MeterAccount
from collections.abc import Iterable, Iterator
from datetime import datetime , timezone, timedelta
from pyspark.sql.dataframe import DataFrame

randomSeed:int = 233


def getRatePlan() -> str:
    if random.random() < 0.8:
        return "Flat"
    elif random.random() < 0.8:
        return "Tiered"
    else:
        return "Time-Of-Use"


def scramble_id(counter_id: int) -> int:
    PRIME = 7465321871
    MOD = 10**10
    for _ in range(4):
        counter_id = (counter_id * PRIME + 1234567891) % MOD
        counter_id = counter_id ^ 0x5555555555
    return (counter_id % MOD)

def getAccountNumber(accountNumberCounter:int) -> str:
    return f"A{scramble_id(accountNumberCounter)}"



meter_schema:StructType = StructType([
    StructField("meter_id", StringType(), True),
    StructField("account_number", StringType(), True),
    StructField("rate_plan", StringType(), True),
    StructField("effective_date", TimestampType(), True),
    StructField("effective_to", TimestampType(), True)
])

def getEffectiveDate() -> datetime :
    e_year:int = random.randint(1985, 2025)
    e_month:int = random.randint(1, 12)
    e_day:int = random.randint(1,28)
    e_hour:int = random.randint(0,23)
    e_minute:int = random.randint(0, 3)*15
    rv:datetime = datetime.strptime(f"{e_year}-{e_month}-{e_day}", "%Y-%m-%d") \
        .replace(tzinfo=timezone.utc,hour=e_hour, minute=e_minute, second=0, microsecond=0) 
    return rv

def getExpirationDate(eff_date:datetime, noNone:bool = False) -> datetime :
    rv:datetime = None
    if random.random() < 0.05 or noNone:
        e_year:int = 2026
        if eff_date != None:
            e_year = random.randint(eff_date.year, 2026)
        e_month:int = 10 # random.randint(1, 12)
        e_day:int = random.randint(1,21)
        e_hour:int = random.randint(0,23)
        e_minute:int = random.randint(0, 3)*15
        rv = datetime.strptime(f"{e_year}-{e_month}-{e_day}", "%Y-%m-%d") \
            .replace(tzinfo=timezone.utc,hour=e_hour, minute=e_minute, second=0, microsecond=0) 
    return rv

def process_meter(rows: Iterable[Row]) -> Iterator[MeterAccount]:
    accountNumberCounter:int = 542
    for row in rows:
        accountNumberCounter += 1
        effective_date :datetime = getEffectiveDate()
        expiration_date:datetime = getExpirationDate(effective_date)
        yield MeterAccount(meter_id=row["meter_id"],
                            account_number=getAccountNumber(accountNumberCounter),
                            rate_plan=getRatePlan(),
                            effective_date=effective_date,
                            effective_to=expiration_date
                           )
        if expiration_date != None:
            accountNumberCounter += 1
            yield MeterAccount(meter_id=row["meter_id"],
                                        account_number=getAccountNumber(accountNumberCounter),
                                        rate_plan=getRatePlan(),
                                        #effective_date=getExpirationDate(expiration_date, True),
                                        effective_date=expiration_date+timedelta(minutes=15),
                                        effective_to=None
                                       )
     


if __name__ == "__main__":
    random.seed(randomSeed)
    spark:SparkSession = SparkSession.builder.remote("sc://localhost:15002").getOrCreate()
    df=spark.read.parquet("s3a://test-bucket/output/output.parquet")
    meters=df.select("meter_id").distinct()
    meter_iterator:Iterator[MeterAccount]  = process_meter(meters.toLocalIterator())
    df2:DataFrame = spark.createDataFrame(data=meter_iterator, schema=meter_schema)
    df2.repartition(1).write.mode(saveMode="overwrite").parquet(path="s3a://test-bucket/accounts/meter_account.parquet")
    df2.show(df2.count())
    print(f"Showing {df2.count()} rows.")