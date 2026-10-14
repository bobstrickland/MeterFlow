import glob
from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, TimestampType


spark:SparkSession = SparkSession.builder.remote("sc://localhost:15002").getOrCreate()

my_schema:StructType = StructType([
    StructField("reading_id", StringType(), True),
    StructField("meter_id", StringType(), True),
    StructField("interval_start", TimestampType(), True),
    StructField("register_kwh", DoubleType(), True),
    StructField("read_type", StringType(), True),
    StructField("received_at", TimestampType(), True),
    StructField("gateway_id", StringType(), True),
    StructField("gateway_seq", IntegerType(), True),
    StructField("quality_flag", StringType(), True),
    StructField("schema_version", IntegerType(), True)
])

df = spark.read.format("csv") \
    .option("header", "true") \
    .schema(my_schema) \
    .load("../apps/day3/output*.csv")
df = df.withColumn("received_date", F.to_date("received_at"))
df.show()
df.hint("rebalance", "received_date") \
    .write \
    .parquet(path="s3a://test-bucket/output/output.parquet", mode="overwrite")
