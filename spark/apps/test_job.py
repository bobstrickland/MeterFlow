# apps/test_job.py
from pyspark.sql import SparkSession
import sys

if __name__ == "__main__":
    print(f"Running PySpark with Python version: {sys.version}")

    # Initialize Spark Session pointing to the master container
    spark = SparkSession.builder \
        .appName("DockerPySparkTest") \
        .getOrCreate()

    # Create dummy data
    data = [("Alice", 34), ("Bob", 45), ("Catherine", 29)]
    columns = ["Name", "Age"]

    df = spark.createDataFrame(data, schema=columns)
    df.show()

    # Filter data to test cluster execution
    df.filter(df.Age > 30).show()

    spark.stop()
