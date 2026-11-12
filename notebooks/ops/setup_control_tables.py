# Create the ingestion-control table if it does not already exist.
#
# This table is the pipeline's audit log. It records every attempted load,
# including whether it succeeded, how many rows were written, and any error.
#
# We use STRING for dates here because Bronze preserves source context.
# Silver can later cast dates into proper DATE types if needed.

from pyspark.sql import SparkSession

# Use the real catalog and schema recorded in Feature 1.1.
CATALOG = "trippilot_dev"
BRONZE_SCHEMA = "bronze"

# Full name of the control table.
CONTROL_TABLE = f"{CATALOG}.{BRONZE_SCHEMA}.airbnb_ingestion_control"

# CREATE TABLE IF NOT EXISTS makes this notebook safe to rerun.
# Databricks notebook source
spark.sql('CREATE SCHEMA IF NOT EXISTS trippilot_dev.ops')
spark.sql('''
CREATE TABLE IF NOT EXISTS trippilot_dev.bronze.airbnb_ingestion_control (
  city STRING, snapshot_date STRING, run_id STRING, status STRING,
  row_count LONG, started_at_utc STRING, completed_at_utc STRING,
  error_message STRING
) USING DELTA
''')
spark.sql('''
CREATE TABLE IF NOT EXISTS trippilot_dev.ops.quality_results (
  run_id STRING, source STRING, city STRING, snapshot_date STRING,
  layer STRING, check_name STRING, passed BOOLEAN,
  observed_count LONG, checked_at_utc TIMESTAMP
) USING DELTA
''')

# Confirm that the control table is available.
print(f"Ingestion control table ready: {CONTROL_TABLE}")