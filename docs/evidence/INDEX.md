# 证据索引（docs/evidence/INDEX.md）

> 用途：把每个 AC-ID 的实测证据归档到固定目录，报告中每个数字都能追溯。  
> 当前状态：代码/脚本/文档已实现；**所有数据库、页面、性能结果待用户在 Linux VM 实测**。  
> 禁止：伪造截图、复制他人输出、把计划值写成实测值。

---

## 1. 目录规范

每个 AC 一个目录：

```text
docs/evidence/<AC-ID>/
├─ command.txt          # 执行过的命令
├─ output.txt           # 终端原始输出
├─ screenshot-*.png     # 需要时截图，含时间/地址栏/提示符
├─ result.csv           # 并发原始数据（如适用）
├─ summary.json         # 并发汇总（如适用）
└─ notes.md             # 环境、时间、复现步骤、失败原因
```

命名：

- 截图：`<topic>-01.png`、`<topic>-02.png`；
- 同一命令多次运行：`run-1.txt`、`run-2.txt`、`run-3.txt`；
- 失败证据保留，不删除。

---

## 2. 环境与部署

| AC-ID | 命令/操作 | 必存文件 | 截图 |
|---|---|---|---|
| AC-ENV-01 | VM `ip addr`；Windows `ipconfig`；浏览器 `/health` | `command.txt`、`output.txt` | 浏览器地址栏 + IP 输出 |
| AC-ENV-02 | `ss -lntp \| grep -E '5000\|5432'`；Windows `Test-NetConnection` | `command.txt`、`output.txt` | 监听与端口测试 |
| AC-ENV-03 | `SHOW listen_addresses;`；`pg_hba.conf` 片段 | `command.txt`、`output.txt` | 配置片段 |
| AC-ENV-04 | Flask 启动日志；`ss -lntp` | `output.txt` | 启动终端 |
| AC-ENV-05 | `sudo ufw status verbose`；`sudo ufw status numbered` | `output.txt` | UFW 状态 |
| AC-ENV-06 | Windows `ping`/`curl`；VM `curl 127.0.0.1` | `output.txt` | 浏览器/终端 |
| AC-ENV-07 | `systemctl status` 或进程检查；重启后访问 | `output.txt` | 服务状态 |
| AC-ENV-08 | `timedatectl`；Flask/PG 日志片段 | `output.txt` | 日志 |

---

## 3. 技术栈与合规

| AC-ID | 命令/操作 | 必存文件 |
|---|---|---|
| AC-STK-01 | `psql --version`、`pip freeze`、源码导入检查 | `output.txt` |
| AC-STK-02 | `pip freeze \| grep -iE 'sqlalchemy\|django\|peewee\|sqlobject'`；源码搜索 | `output.txt` |
| AC-STK-03 | 代码来源说明、抽查记录 | `notes.md` |
| AC-STK-04 | `requirements.txt`、`pip freeze` | `output.txt` |
| AC-STK-05 | 断网/无 CDN 打开页面 | 截图 + `notes.md` |

---

## 4. 数据模型与数据量

| AC-ID | 命令/操作 | 必存文件 |
|---|---|---|
| AC-DB-01 | `\dt`、`information_schema.tables` | `output.txt` |
| AC-DB-02 | ERD 截图/导出、表清单 | `screenshot-erd.png`、`notes.md` |
| AC-DB-03 | 1-1 反例、1-N/N-M 查询 | `output.txt`、ERD 截图 |
| AC-DB-04 | 3NF 检查表 | `notes.md`（引用 `docs/02_erd.md`） |
| AC-DB-05 | draw.io/pgModeler 导出 | `erd.png`、`export.sql`（人工复核） |
| AC-DB-06 | `psql -f sql/01_schema.sql`、`\d+` | `output.txt` |
| AC-DB-07 | 孤儿外键/重复唯一/负库存/非法状态反例 | `output.txt` |
| AC-DB-08 | `\d+`、`COMMENT ON` 检查 | `output.txt` |
| AC-DATA-01 | `psql -f tests/test_db_counts.sql` | `output.txt`（填 `{{MEASURED_TOTAL_ROWS}}`） |
| AC-DATA-02 | 每表行数、分布查询 | `output.txt` |
| AC-DATA-03 | 清空重跑种子，比较行数/抽样 | `output.txt`、`notes.md` |
| AC-DATA-04 | 合成数据说明 | `notes.md` |
| AC-DATA-05 | 种子耗时/批次记录 | `output.txt` |

---

## 5. 必备 SQL 操作

| AC-ID | 命令/操作 | 必存文件 |
|---|---|---|
| AC-CRUD-01 | 管理脚本建表；`\dt` | `output.txt` |
| AC-CRUD-02 | 创建订单/商品；`SELECT` 核对 | `output.txt`、页面截图 |
| AC-CRUD-03 | 修改订单状态/商品；前后查询 | `output.txt` |
| AC-CRUD-04 | 删除明细/商品；`SELECT` 核对 | `output.txt` |
| AC-CRUD-05 | `sql/06_drop_table_demo.sql` | `output.txt`、`\dt` 截图 |
| AC-CRUD-06 | 订单详情 join SQL/页面 | `output.txt`、页面截图 |
| AC-CRUD-07 | 分类 N-M join/聚合 | `output.txt` |
| AC-CRUD-08 | 分页/筛选重复查询 | `output.txt` |

---

## 6. 事务

| AC-ID | 命令/操作 | 必存文件 |
|---|---|---|
| AC-TX-01 | 双连接 commit 可见 | `output.txt` |
| AC-TX-02 | 双连接 rollback 不可见 | `output.txt` |
| AC-TX-03 | 库存不足创建订单回滚 | 页面截图 + `output.txt` |
| AC-TX-04 | 并发扣库存不超卖 | CSV/JSON + `output.txt` |
| AC-TX-05 | 死锁/序列化失败与重试记录 | `output.txt` |
| AC-TX-06 | `SHOW transaction_isolation`、`pg_stat_activity` | `output.txt` |

事务测试：

```bash
export TEST_DB_DSN="host=127.0.0.1 port=5432 dbname=course_db user=app_rw password=<app_rw 密码>"
pytest -q tests/test_transaction.py
```
---

## 7. 索引与 EXPLAIN

| AC-ID | 命令/操作 | 必存文件 |
|---|---|---|
| AC-IDX-01 | `sql/07_explain.sql` 的 BEFORE 3 次 | `output.txt` |
| AC-IDX-02 | AFTER 3 次 | `output.txt` |
| AC-IDX-03 | `pg_stat_user_indexes` | `output.txt` |
| AC-IDX-04 | 索引选择/写放大分析 | `notes.md` |
| AC-IDX-05 | `pg_stats`/`ANALYZE` 前后 | `output.txt` |
| AC-IDX-06 | `\di+`、索引大小 | `output.txt` |

```bash
mkdir -p docs/evidence/IDX-01 docs/evidence/IDX-02
psql -h 127.0.0.1 -U db_owner -d course_db -f sql/07_explain.sql \
  > docs/evidence/IDX-01/output.txt 2>&1
```

报告中填：

- `{{EXPLAIN_BEFORE_MS}}`
- `{{EXPLAIN_AFTER_MS}}`

---

## 8. 并发

| AC-ID | 命令/操作 | 必存文件 |
|---|---|---|
| AC-CON-01 | `benchmark_concurrency.py --clients 1,10,25,50` | `concurrency_*.csv`、`summary.json` |
| AC-CON-02 | 70/20/10 负载配置 | `notes.md` |
| AC-CON-03 | 汇总指标 | `summary.json` |
| AC-CON-04 | 测试前后 `pg_stat_activity` | `output.txt` |
| AC-CON-05 | 无超卖/半单/重复物流查询 | `output.txt` |
| AC-CON-06 | 3 次运行/波动记录 | `output.txt`、`notes.md` |
| AC-CON-07 | `vmstat`/`top`/`iostat` | `output.txt` |

```bash
python3 scripts/benchmark_concurrency.py \
  --clients 1,10,25,50 --duration 30 --warmup 5 \
  --output-dir tests/results
```

报告中填：

- `{{TPS_10}}`
- `{{P95_50}}`

---

## 9. 安全

| AC-ID | 命令/操作 | 必存文件 |
|---|---|---|
| AC-SEC-01 | 注入字符串输入页面/API；源码审查 | 截图 + `output.txt` |
| AC-SEC-02 | `git grep`/文件搜索密码；`.gitignore` | `output.txt` |
| AC-SEC-03 | `app_rw` 执行 DDL 被拒绝；`rolsuper=f` | `output.txt` |
| AC-SEC-04 | Windows 连 5432 失败；`ss`/`ufw` | `output.txt` |
| AC-SEC-05 | 400/404/500 页面与日志 | 截图 + `output.txt` |
| AC-SEC-06 | 无 token POST；超长/非法输入 | `output.txt` |
| AC-SEC-07 | Cookie 配置/SECRET_KEY 来源 | `notes.md` |
| AC-SEC-08 | `.env` 权限、依赖检查 | `output.txt` |

---

## 10. 前端

| AC-ID | 命令/操作 | 必存文件 |
|---|---|---|
| AC-UI-01 | 路由清单；两个页面 | `screenshot-orders-list.png`、`screenshot-order-detail.png` |
| AC-UI-02 | 创建→详情→改状态→取消/删除 | 每步截图 + `notes.md` |
| AC-UI-03 | 详情页 join 数据 | 截图 |
| AC-UI-04 | 非法数量/超库存/非法状态 | 截图 + `output.txt` |
| AC-UI-05 | 分页/筛选/空结果 | 截图 |
| AC-UI-06 | XSS 输入转义 | 截图 |

截图必须包含浏览器地址栏；建议同时截页面与数据库查询结果。

---

## 11. 报告与代码质量

| AC-ID | 命令/操作 | 必存文件 |
|---|---|---|
| AC-RPT-01 | 提交物清单 | `notes.md` |
| AC-RPT-02 | 数字与证据对照 | `notes.md` |
| AC-RPT-03 | 报告 ERD/关系模式/3NF/DDL | 报告 PDF |
| AC-RPT-04 | 按 README 复现 | `output.txt` |
| AC-RPT-05 | 标志性实践格式 | 报告截图 |
| AC-RPT-06 | 演示提纲 | `notes.md` |
| AC-RPT-07 | 本索引 | `INDEX.md` |
| AC-CODE-01 | 静态搜索 | `output.txt` |
| AC-CODE-02 | 事务代码审查 | `notes.md` |
| AC-CODE-03 | 连接释放审查/`pg_stat_activity` | `output.txt` |
| AC-CODE-04 | 配置检查 | `output.txt` |
| AC-CODE-05 | 注释/命名抽查 | `notes.md` |
| AC-CODE-06 | `compileall`/`pytest` | `output.txt` |

---

## 12. 待用户实测清单（汇总）

### 12.1 Linux VM 命令

```bash
# 1. 环境
date
uname -a
lsb_release -a
psql --version
python3 --version
nproc
free -h
df -h
ss -lntp | grep -E '5000|5432'
sudo ufw status verbose

# 2. 角色/DDL/种子
sudo -u postgres psql -v db_owner_password="$DB_OWNER_PASSWORD" \
  -v app_rw_password="$DB_APP_PASSWORD" -f sql/00_bootstrap_roles.sql
python3 scripts/init_db.py create-tables
python3 scripts/init_db.py seed
psql -h 127.0.0.1 -U db_owner -d course_db -f tests/test_db_counts.sql

# 3. 权限
psql -h 127.0.0.1 -U app_rw -d course_db -c "CREATE TABLE should_fail(id int);"
psql -h 127.0.0.1 -U app_rw -d course_db -c "DROP TABLE orders;"
psql -h 127.0.0.1 -U app_rw -d course_db -c "TRUNCATE orders;"

# 4. 启动
./scripts/run_app.sh

# 5. 删表/EXPLAIN
psql -h 127.0.0.1 -U db_owner -d course_db -f sql/06_drop_table_demo.sql
psql -h 127.0.0.1 -U db_owner -d course_db -f sql/07_explain.sql \
  > docs/evidence/IDX-01/output.txt 2>&1

# 6. 事务/并发
export TEST_DB_DSN="host=127.0.0.1 port=5432 dbname=course_db user=app_rw password=<app_rw 密码>"
pytest -q tests/test_transaction.py
python3 scripts/benchmark_concurrency.py --clients 1,10,25,50 --duration 30 --warmup 5
```

### 12.2 Windows Host 命令

```powershell
Test-NetConnection <VM_IP> -Port 5000
Test-NetConnection <VM_IP> -Port 5432
Start-Process "http://<VM_IP>:5000/health"
Start-Process "http://<VM_IP>:5000/orders"
```

### 12.3 需要截图

- [ ] `/health`（地址栏）；
- [ ] 订单列表页；
- [ ] 创建订单成功；
- [ ] 库存不足错误；
- [ ] 订单详情（客户/明细/分类/物流/金额）；
- [ ] 状态修改；
- [ ] 取消订单后库存回补；
- [ ] 删除明细；
- [ ] `demo_drop_me` 删除前后 `\dt`；
- [ ] EXPLAIN before/after；
- [ ] 并发 CSV/JSON 与 `pg_stat_activity`；
- [ ] `ufw status`；
- [ ] `app_rw` DDL 被拒绝；
- [ ] 数据量 `COUNT(*)`。

### 12.4 需要回填的占位符

- `{{MEASURED_TOTAL_ROWS}}`
- `{{EXPLAIN_BEFORE_MS}}`
- `{{EXPLAIN_AFTER_MS}}`
- `{{TPS_10}}`
- `{{P95_50}}`
- 报告中所有 `【待用户实测】`

---

## 13. 提交前检查

- [ ] P0 AC 全部有证据；
- [ ] 每个数字能定位到 `output.txt`/CSV/JSON；
- [ ] 截图含时间/地址栏/终端提示符；
- [ ] 无真实密码、IP、个人信息；
- [ ] 无伪造/复制证据；
- [ ] `docs/acceptance_matrix.md` 状态与实际一致。