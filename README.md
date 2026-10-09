# MeterFlow

A smart-meter billing pipeline for a fictional electric utility, built to show how to make a batch data pipeline **idempotent**, **auditable**, and **extensible**.

All data is synthetic. The utility, "Riverbend Electric," is fictional, and no real customer, meter, or company data is used anywhere in this repository.

## Why this project exists

Usage-based billing looks simple until the data misbehaves. Smart meters report every 15 minutes through neighborhood gateways, and those readings arrive late, duplicated, and out of order. Some intervals never arrive and have to be estimated, and an actual reading sometimes replaces an estimate after the bill has already gone out.

MeterFlow ingests all of that, builds trustworthy usage totals, prices them under versioned rate plans, produces monthly bills, and corrects past bills without ever rewriting history.

The domain is electricity, but the engineering problems (deduplication, late data, reconciliation, adjustments, pluggable pricing, lineage) are the same for any usage-based billing system, including cloud and AI platforms.

## What it demonstrates

| Property | How it is shown |
|:--|:--|
| **Idempotency** | Re-running any day's batch, or running days out of order, produces identical output. Writes are partition-overwrite. Readings are deduplicated by a deterministic `reading_id`. A gateway batch sent twice is counted once. Tests enforce all of it. |
| **Auditability** | Every bill line traces to usage days and readings. The raw layer is immutable. Estimated and actual readings are always distinguishable. A reconciliation report proves the numbers add up. Closed billing periods are frozen. |
| **Extensibility** | A new rate plan is one new class or config entry, with no pipeline edits. Reading schemas and rate schedules are versioned with effective dates. |

## Architecture

```
gateways -> [ingest queue] -> RAW (immutable, by ingest date)
                                |
                  validate + dedupe by reading_id
                                |
                     CLEAN  +  QUARANTINE (reject reasons)
                                |
                  detect gaps, fill with labeled estimates
                                |
                     DAILY USAGE (per meter, per usage day)
                                |
                   rate plans (versioned, pluggable)
                                |
                     RATED USAGE -> BILLS (append-only ledger)
                                          |
                    ADJUSTMENTS (true-ups, corrections)

             RECONCILIATION REPORT checks every step above
```

### Data layers

1. **Raw:** readings exactly as received, partitioned by ingest date, never modified.
2. **Clean:** validated and deduplicated; rejects go to a quarantine table with a reason code.
3. **Estimated:** missing intervals filled with a labeled estimate, replaced if the actual reading arrives in time.
4. **Daily usage:** kWh per meter per usage day, with the share of intervals that were estimated.
5. **Rated usage:** daily usage priced under versioned rate plans (flat, tiered, time-of-use).
6. **Bills:** monthly bill lines per account, each pointing to its usage days, readings, and rate version.
7. **Adjustments:** corrections become new credit or debit lines on the next bill; originals are never edited.
8. **Reconciliation report:** source rows equal clean plus duplicates plus rejected; expected intervals equal actual plus estimated; bill totals equal rated usage plus adjustments.

### Reading schema (version 1)

| Field | Purpose |
|:--|:--|
| `reading_id` | Deterministic ID from meter, interval, and channel; the deduplication key |
| `meter_id` | Which physical meter reported |
| `interval_start` | Start of the 15-minute interval (event time) |
| `kwh` | Energy used in the interval |
| `read_type` | `ACTUAL` or `ESTIMATED` |
| `received_at` | Arrival time, used for late-data detection |
| `gateway_id`, `gateway_seq` | Per-gateway sequence numbers to detect missing batches |
| `quality_flag` | `OK`, `SUSPECT`, or `FILLED` |
| `schema_version` | Enables versioned evolution |

A separate `meters` dimension maps each meter to an account and rate plan with effective dates, because meters change accounts when customers move.

## Design rules

- **Event time, not arrival time.** Usage is aggregated by `interval_start`. A usage day closes after a 2-day grace period; later arrivals become adjustment entries.
- **Never edit history.** Corrections are new ledger lines that reference the original.
- **Estimates are always labeled.** An estimated reading can be replaced by an actual one, and that replacement is visible downstream.
- **Reject loudly.** Bad rows go to quarantine with a reason code. Nothing is silently dropped, and every input row ends in exactly one of clean, duplicate, or rejected.
- **Config, not code, for environments.** Endpoints, credentials, and bucket names come from environment variables, so the same code runs against the local stand-ins and real AWS.

## Tech stack

Python 3.12+, PySpark, Parquet, pytest, Pydantic, Docker Compose for local development, and AWS CDK (Python) for deployment. Planned AWS services: S3, Athena, Glue Data Catalog, EMR Serverless, Step Functions, SQS, and Lambda.

## Running it locally

The local stack uses Docker containers as stand-ins for AWS services. Everything runs without accounts or tokens. Pin exact image tags in `docker-compose.yml`, never `latest`, and record them here once chosen.

| AWS service | Local stand-in image | Pinned tag |
|:--|:--|:--|
| S3 | `chrislusf/seaweedfs` | to be pinned |
| SQS (with dead-letter queues) | `softwaremill/elasticmq-native` | to be pinned |
| Lambda (container image) | `public.ecr.aws/lambda/python:3.12` | to be pinned |
| Step Functions | `amazon/aws-stepfunctions-local` | to be pinned |
| Spark (EMR Serverless or Glue) | `spark:python3` | to be pinned (for example `4.2.0-java21-python3`) |
| Athena | `trinodb/trino` | to be pinned |
| Glue Data Catalog | `apache/hive` standalone metastore, plus `postgres` | to be pinned |
| IAM, STS, CloudWatch (API-level tests only) | `motoserver/moto` | to be pinned |

These are stand-ins, not replicas. Step Functions Local is unsupported by AWS and lacks feature parity, Trino is not Athena, and none of the emulators enforce real IAM behavior. The final section of this README lists the differences found when porting to real AWS.

### Quick start (intended interface)

```bash
# 1. Start the local stack
docker compose up -d

# 2. Generate synthetic readings (fixed seed, reproducible)
uv run python -m meterflow.generate --meters 10000 --days 21 --seed 42

# 3. Run one day of the pipeline
uv run python -m meterflow.run --date 2026-10-01

# 4. Re-run it and prove nothing changed
uv run pytest tests/test_idempotency.py

# 5. Reconcile
uv run python -m meterflow.reconcile --date 2026-10-01
```

## Scale target

About 20 million readings (10,000 meters, 96 readings a day, 21 days), with one large commercial account owning roughly 30 percent of the meters to create deliberate data skew. Spark timings, explain plans, and the skew fix are documented in `docs/`.

## Repository layout (planned)

```
meterflow/
  src/meterflow/
    generate.py        synthetic reading generator
    schemas.py         Pydantic models and Spark schemas
    validate.py        validation and quarantine
    dedupe.py          within-batch and cross-batch deduplication
    estimate.py        gap detection and labeled estimates
    usage.py           daily usage aggregation
    rating/            rate plan interface, registry, plans
    ledger.py          append-only bill lines and adjustments
    reconcile.py       reconciliation report
    trace.py           bill line to readings lineage
    mcp_server.py      MCP tools for customer billing questions
  tests/               pytest suites, including idempotency and reconciliation
  infra/               AWS CDK (Python) stack
  docs/
    devlog.md          daily notes: what was built, what surprised me
    adr/               architecture decision records
    runbook.md         rerun a day, backfill, investigate a mismatch
  docker-compose.yml
  pyproject.toml
```

## Testing

Every function ships with a test. The tests that matter most:

- **Idempotency:** running a day twice, and out of order, yields identical output (row counts and a checksum of sorted output).
- **Deduplication:** a duplicate arriving in a later batch is removed exactly once.
- **Late data:** a late reading inside the grace period changes the daily usage; one outside it produces an adjustment and leaves the closed day untouched.
- **Accounting:** every input row ends as exactly one of clean, duplicate, or rejected; every expected interval ends as exactly one of actual or estimated.
- **Extensibility:** a new rate plan can be added in a test without editing pipeline code.
- **Versioning:** the same usage rated under two rate versions gives different totals, and re-rating a closed period uses the version in force at the time.

```bash
uv run pytest
```

## Roadmap

Check items off as they are actually working and tested.

- [ ] **Phase 0 ** repo, pytest loop, validation, local stack, S3A acceptance test
- [ ] **Phase 1 ** PySpark over 20M readings, Parquet layout, joins and windows, explain plans, skew experiment
- [ ] **Phase 2 ** idempotent writes, deduplication, late data, estimation, quarantine, reconciliation
- [ ] **Phase 3 ** port to AWS (Athena, EMR Serverless, Step Functions, SQS and Lambda, CDK), then tear down
- [ ] **Phase 4 ** pluggable rate plans, versioned rates, immutable ledger and true-ups, lineage, CI
- [ ] **Phase 5 ** MCP tools, tracing, documentation, mock interviews, publication

## Architecture decisions

Decision records live in `docs/adr/`. Planned entries:

- Partition-overwrite writes and deterministic reading IDs
- Choice of local S3 stand-in (and the fallback if S3A tests fail)
- Cloud design: services chosen, cost, and failure modes

## Limitations

- Synthetic data only. Real meter data has noise, firmware quirks, and regulatory rules this project does not model.
- Local stand-ins differ from AWS in IAM enforcement, networking, limits, startup latency, and cost.
- This is a learning and portfolio project. It has not been load-tested at production scale, and it is not a billing system to run a business on.

## Local versus AWS: differences found

*To be filled in during Phase 3. One entry per surprise, for example: "worked locally, failed on AWS because of X."*

## License

MIT License - take it, use it, do what you want with it.
