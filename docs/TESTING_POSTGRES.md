# Isolated Postgres for Tests and Benchmarks

Purpose: Provide a disposable Postgres instance for concurrency validation (DATA-01)
and performance benchmarking (PERF-01..04) without touching dev/prod data.

## Safety Guarantees
- Separate container: `mrm3_test_db`
- Separate port: `5434`
- Separate volume: `mrm3_postgres_test_data`
- Separate databases: `mrm_test`, `mrm_bench`
- Separate users: `mrm_test_user`, `mrm_bench_user`

Do not point these commands at any production or shared development database.

## Prerequisites
- Docker + Docker Compose
- Repo root contains `docker-compose.test.yml`

## Start the Isolated DB
```bash
docker compose -f docker-compose.test.yml up -d
docker compose -f docker-compose.test.yml ps
```

## Environment Variables
```bash
# Test database (for concurrency tests)
export TEST_DATABASE_URL="postgresql://mrm_test_user:mrm_test_pass@localhost:5434/mrm_test"

# Benchmark database (for performance benchmarks)
export BENCH_DATABASE_URL="postgresql://mrm_bench_user:mrm_bench_pass@localhost:5434/mrm_bench"
```

## Verify Connectivity
```bash
docker exec mrm3_test_db psql -U mrm_test_user -d mrm_test -c "SELECT current_database(), current_user;"
docker exec mrm3_test_db psql -U mrm_bench_user -d mrm_bench -c "SELECT current_database(), current_user;"
```

## Run Postgres Concurrency Test (DATA-01)
```bash
cd api
DATABASE_URL=sqlite:///./test.db SECRET_KEY=test-secret PYTHONPATH=. \
  pytest -m postgres tests/test_postgres_concurrency.py
```

## Run Performance Benchmarks (PERF-01..04)
```bash
python scripts/bench_reports.py --database-url "$BENCH_DATABASE_URL" --reset
```
Note: `--reset` drops and recreates all tables in the benchmark database.

## Teardown (Clean Removal)
```bash
docker compose -f docker-compose.test.yml down -v
docker volume ls | grep mrm3_postgres_test_data  # Should return nothing
```

## Isolation Summary
```
Aspect        Dev DB            Test/Bench DB
Container     mrm3_db           mrm3_test_db
Port          5433              5434
Volume        postgres_data     mrm3_postgres_test_data
Databases     mrm_db            mrm_test, mrm_bench
Users         mrm_user          mrm_test_user, mrm_bench_user
```
