-- ============================================================
-- 00_bootstrap_roles.sql
-- 作用：由 postgres 超级用户执行一次，创建数据库、db_owner、app_rw。
-- 注意：本文件使用 psql 变量，不能由 psycopg2 直接执行。
-- 运行示例：
--   sudo -u postgres psql \
--     -v db_owner_password="$DB_OWNER_PASSWORD" \
--     -v app_rw_password="$DB_APP_PASSWORD" \
--     -f sql/00_bootstrap_roles.sql
-- 密码只从环境变量传入，不写死在文件里。
-- ============================================================

\set ON_ERROR_STOP on

\if :{?db_owner_password}
\else
  \echo 'ERROR: 缺少 psql 变量 db_owner_password'
  \quit
\endif

\if :{?app_rw_password}
\else
  \echo 'ERROR: 缺少 psql 变量 app_rw_password'
  \quit
\endif

-- 1. 创建非超级用户 db_owner（对象所有者，仅用于 DDL/种子）
SELECT format(
  'CREATE ROLE db_owner LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT CONNECTION LIMIT 20',
  :'db_owner_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'db_owner')
\gexec

SELECT format(
  'ALTER ROLE db_owner WITH LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT CONNECTION LIMIT 20',
  :'db_owner_password'
)
\gexec

-- 2. 创建非超级用户 app_rw（Flask 运行时，仅 DML）
SELECT format(
  'CREATE ROLE app_rw LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT CONNECTION LIMIT 100',
  :'app_rw_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_rw')
\gexec

SELECT format(
  'ALTER ROLE app_rw WITH LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT CONNECTION LIMIT 100',
  :'app_rw_password'
)
\gexec

-- 3. 角色级超时，避免长事务与锁等待拖垮并发测试
ALTER ROLE app_rw SET statement_timeout = '15s';
ALTER ROLE app_rw SET lock_timeout = '5s';
ALTER ROLE app_rw SET idle_in_transaction_session_timeout = '30s';
ALTER ROLE app_rw SET search_path = public, pg_catalog;

ALTER ROLE db_owner SET statement_timeout = '120s';
ALTER ROLE db_owner SET idle_in_transaction_session_timeout = '60s';
ALTER ROLE db_owner SET search_path = public, pg_catalog;

-- 4. 创建数据库（已存在则跳过）
SELECT 'CREATE DATABASE course_db OWNER db_owner'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'course_db')
\gexec

-- 5. 连接到目标数据库，并确保 db_owner 是数据库所有者
\connect course_db
ALTER DATABASE course_db OWNER TO db_owner;

-- 6. 数据库级权限
REVOKE ALL ON DATABASE course_db FROM PUBLIC;
GRANT CONNECT ON DATABASE course_db TO db_owner, app_rw;
ALTER DATABASE course_db SET timezone TO 'UTC';

-- 7. public schema 归 db_owner，app_rw 只有 USAGE
ALTER SCHEMA public OWNER TO db_owner;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO app_rw;
REVOKE CREATE ON SCHEMA public FROM app_rw;

-- 8. 说明
\echo 'OK: course_db / db_owner / app_rw 已创建或更新；接下来由 db_owner 执行 sql/01_schema.sql。'