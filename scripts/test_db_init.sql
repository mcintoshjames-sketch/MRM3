-- Isolated test databases for mrm_inv_3
-- This script runs automatically on container first start
-- SAFE TO DROP/RECREATE - completely separate from dev/prod

-- Create test user and database (for concurrency tests)
CREATE USER mrm_test_user WITH PASSWORD 'mrm_test_pass';
CREATE DATABASE mrm_test OWNER mrm_test_user;
GRANT ALL PRIVILEGES ON DATABASE mrm_test TO mrm_test_user;

-- Create bench user and database (for performance benchmarks)
CREATE USER mrm_bench_user WITH PASSWORD 'mrm_bench_pass';
CREATE DATABASE mrm_bench OWNER mrm_bench_user;
GRANT ALL PRIVILEGES ON DATABASE mrm_bench TO mrm_bench_user;

-- Grant schema creation privileges (needed for SQLAlchemy create_all)
\c mrm_test
GRANT ALL ON SCHEMA public TO mrm_test_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO mrm_test_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO mrm_test_user;

\c mrm_bench
GRANT ALL ON SCHEMA public TO mrm_bench_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO mrm_bench_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO mrm_bench_user;
