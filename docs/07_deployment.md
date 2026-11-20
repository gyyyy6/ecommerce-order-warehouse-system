# P2 部署文档（数据库部分）

> 阶段：P2 角色、DDL、索引、种子  
> 状态：已实现（待用户实测）  
> 说明：本文件只覆盖 Linux VM 上的 PostgreSQL 部分；Flask 部署见 P8 的 `README.md`。  
> 重要：以下命令中的密码全部通过环境变量/psql 变量传入，不得把真实密码写入文件或截图。

---

## 1. 环境假设

| 项目 | 假设 | 需用户确认 |
|---|---|---|
| VM 系统 | Ubuntu 22.04/24.04 LTS | `lsb_release -a` |
| PostgreSQL | 15/16 | `psql --version` |
| Python | 3.10+ | `python3 --version` |
| 数据库名 | `course_db` | 如需改名，同步修改 `.env` 与 SQL |
| 运行账号 | `app_rw`（仅 DML） | 不得用 postgres/root |
| 管理账号 | `db_owner`（非超级用户） | 仅 DDL/种子 |
| 数据库监听 | `127.0.0.1:5432` | 不对 Host/公网开放 |
| Flask 端口 | `5000` | 唯一对外开放端口 |

---

## 2. 安装 PostgreSQL 与 Python 工具

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib python3-venv python3-pip
sudo systemctl enable --now postgresql
psql --version
```

预期：命令成功，PostgreSQL 服务运行。实际版本写 `【待用户实测】`。

---

## 3. 配置 PostgreSQL 监听与认证

### 3.1 `postgresql.conf`

找到配置文件：

```bash
sudo -u postgres psql -c "SHOW config_file;"
```

编辑（路径以实际输出为准）：

```conf
listen_addresses = '127.0.0.1'
password_encryption = 'scram-sha-256'
```

不要写成 `'*'` 或 `'0.0.0.0'`。

### 3.2 `pg_hba.conf`

保留本机 `postgres` 的管理方式，只新增以下两行：

```conf
# TYPE  DATABASE   USER       ADDRESS        METHOD
host    course_db  db_owner   127.0.0.1/32   scram-sha-256
host    course_db  app_rw     127.0.0.1/32   scram-sha-256
```

禁止出现：

```conf
host all all 0.0.0.0/0 md5
host all all 0.0.0.0/0 trust
```

### 3.3 重启并验证

```bash
sudo systemctl restart postgresql
sudo systemctl status postgresql --no-pager
ss -lntp | grep 5432
```

预期：只看到 `127.0.0.1:5432`，不要看到 `0.0.0.0:5432` 或 `[::]:5432`。

---

## 4. 创建角色与数据库

### 4.1 设置密码环境变量

在 Linux shell 中临时设置，不要把真实值写入仓库：

```bash
export DB_OWNER_PASSWORD='<请替换为强密码>'
export DB_APP_PASSWORD='<请替换为另一个强密码>'
```

### 4.2 执行 bootstrap

```bash
sudo -u postgres psql \
  -v db_owner_password="$DB_OWNER_PASSWORD" \
  -v app_rw_password="$DB_APP_PASSWORD" \
  -f sql/00_bootstrap_roles.sql
```

说明：

- `00_bootstrap_roles.sql` 使用 psql 的 `\gexec` 与变量，不能由 psycopg2 直接执行；
- `db_owner` 和 `app_rw` 都是 `NOSUPERUSER NOCREATEDB NOCREATEROLE`；
- `postgres` 只用于这次 bootstrap，不用于 Flask；
- 脚本会创建 `course_db`（若不存在）、设置 schema 权限、角色级超时。

### 4.3 验证角色

```bash
psql -h 127.0.0.1 -U db_owner -d course_db -c "SELECT current_user, session_user;"
psql -h 127.0.0.1 -U app_rw   -d course_db -c "SELECT current_user, session_user;"
```

预期：分别返回 `db_owner`、`app_rw`。

---

## 5. 建表与索引

### 5.1 配置管理员环境变量

```bash
export DB_HOST=127.0.0.1
export DB_PORT=5432
export DB_NAME=course_db
export DB_ADMIN_USER=db_owner
export DB_ADMIN_PASSWORD="$DB_OWNER_PASSWORD"
```

### 5.2 执行 DDL

方式 A：使用 psql

```bash
psql -h 127.0.0.1 -U db_owner -d course_db -f sql/01_schema.sql
psql -h 127.0.0.1 -U db_owner -d course_db -f sql/02_indexes.sql
```

方式 B：使用管理 CLI

```bash
python3 scripts/init_db.py create-tables
```

预期：

- 8 张表：`customer`、`category`、`product`、`product_category`、`orders`、`order_item`、`shipment`、`access_log`；
- 7 个二级索引；
- `app_rw` 拥有 DML/序列权限，但没有 `CREATE`；
- `demo_drop_me` 不存在（由 P6 单独脚本创建/删除）。

### 5.3 查看表与索引

```bash
psql -h 127.0.0.1 -U db_owner -d course_db -c "\dt"
psql -h 127.0.0.1 -U db_owner -d course_db -c "\di"
psql -h 127.0.0.1 -U db_owner -d course_db -c "\d+ order_item"
```

预期：表/索引齐全，`order_item` 主键为 `(order_id, product_id)`，`order_item_id` 为唯一列。

---

## 6. 导入种子数据

### 6.1 环境变量

```bash
export DB_HOST=127.0.0.1
export DB_PORT=5432
export DB_NAME=course_db
export DB_ADMIN_USER=db_owner
export DB_ADMIN_PASSWORD="$DB_OWNER_PASSWORD"
```

### 6.2 执行种子

```bash
python3 scripts/seed_data.py
# 或
python3 scripts/init_db.py seed
```

脚本行为：

- 固定随机种子 `20261020`；
- 批量 `execute_values`，每批 1000；
- 一个显式事务：失败 `ROLLBACK`，成功 `COMMIT`；
- `finally` 关闭连接；
- 导入后 `ANALYZE`；
- 统计总行数，断言 `>100000`，否则抛错。

预期数据量（计划值，不是实测值）：

| 表 | 计划行数 |
|---|---:|
| `customer` | 5,000 |
| `category` | 50 |
| `product` | 2,000 |
| `product_category` | 约 6,000 |
| `orders` | 30,000 |
| `order_item` | 约 90,000 |
| `shipment` | 30,000 |
| `access_log` | 0 |
| **合计** | **约 163,050** |

实际合计必须用下一节命令实测，填入 `{{MEASURED_TOTAL_ROWS}}`。

---

## 7. 统计行数（必须实测）

```bash
psql -h 127.0.0.1 -U db_owner -d course_db -f tests/test_db_counts.sql
```

预期：

- 输出每张表行数与 `TOTAL`；
- `TOTAL > 100000`；
- 将原始输出保存到 `docs/evidence/DATA-01/output.txt`；
- 报告中写实测值，不得照抄计划值。

---

## 8. 验证最小权限

### 8.1 app_rw 不能 DDL

```bash
psql -h 127.0.0.1 -U app_rw -d course_db -c "CREATE TABLE should_fail(id int);"
psql -h 127.0.0.1 -U app_rw -d course_db -c "DROP TABLE orders;"
psql -h 127.0.0.1 -U app_rw -d course_db -c "TRUNCATE orders;"
```

预期：三条都返回 `permission denied`。

### 8.2 app_rw 不是超级用户

```bash
psql -h 127.0.0.1 -U app_rw -d course_db -c \
  "SELECT current_user, rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = current_user;"
```

预期：`rolsuper = f`、`rolcreatedb = f`、`rolcreaterole = f`。

### 8.3 保存证据

```bash
mkdir -p docs/evidence/SEC-03
# 将上述命令与输出保存为 docs/evidence/SEC-03/command.txt / output.txt
```

---

## 9. 验证网络与防火墙

### 9.1 监听

```bash
ss -lntp | grep -E '5000|5432'
```

预期：

- `127.0.0.1:5432` 是 PostgreSQL；
- `0.0.0.0:5000` 或 `*:5000` 是 Flask（P3 启动后）；
- 不应出现 `0.0.0.0:5432`。

### 9.2 UFW

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 5000/tcp
sudo ufw enable
sudo ufw status verbose
```

预期最终状态：

```text
Default: deny (incoming), allow (outgoing)
5000/tcp ALLOW IN Anywhere
```

不得出现 `5432`。如果临时开放了 SSH，验收前删除并保存 `ufw status numbered` 证据。

### 9.3 Windows Host 侧

```powershell
Test-NetConnection <VM_IP> -Port 5000
Test-NetConnection <VM_IP> -Port 5432
```

预期：5000 成功；5432 失败/超时。

---

## 10. 备份与恢复

```bash
pg_dump -h 127.0.0.1 -U db_owner -d course_db -Fc -f course_db.dump
pg_restore -h 127.0.0.1 -U db_owner -d course_db --clean --if-exists course_db.dump
```

说明：

- 备份文件含数据，不提交仓库；
- 恢复前确认是开发环境；
- 报告中可写备份命令，不需要写真实备份大小。

---

## 11. 数据库部分实测清单

| 项目 | 命令/位置 | 需要回填 |
|---|---|---|
| PostgreSQL 版本 | `psql --version` | `【待用户实测】` |
| 监听地址 | `ss -lntp \| grep 5432` | `【待用户实测】` |
| 表数量 | `\dt` | `【待用户实测】` |
| 索引数量 | `\di` | `【待用户实测】` |
| 总行数 | `tests/test_db_counts.sql` | `{{MEASURED_TOTAL_ROWS}}` |
| app_rw 权限 | `SEC-03` 命令 | `【待用户实测】` |
| UFW | `sudo ufw status verbose` | `【待用户实测】` |
| 截图 | `docs/evidence/ENV-02/`、`SEC-03/`、`DATA-01/` | `【待用户实测】` |

> 本文件中的行数均为计划值；没有 Linux VM 的 `COUNT(*)` 输出，不得写成实测结果。