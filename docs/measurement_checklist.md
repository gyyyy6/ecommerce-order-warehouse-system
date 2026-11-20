# 实测清单（Linux VM + Windows Host）

> 用途：P1~P8 代码/文档完成后，用户按本清单在真实环境实测并回填。  
> 原则：不得编造行数、耗时、TPS、EXPLAIN、截图；未测写 `【待用户实测】`。

---

## 0. 实测前准备

### Windows Host

```powershell
Set-Location 'E:\2026_2027\DataBase'
python -m compileall -q app scripts tests
python -m pytest -q tests\test_security.py
node --check app\static\app.js
node --check app\static\order_detail.js
```

预期：`compileall` 无错误；安全测试通过；Node 语法检查无输出。

### 上传到 Linux VM

把整个项目目录上传到 VM，例如 `/opt/DataBase`；不要上传 `.env`（在 VM 上新建）。

---

## 1. 环境与网络

```bash
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
```

记录：

- PostgreSQL 版本：`【待用户实测】`
- Python 版本：`【待用户实测】`
- VM IP：`【待用户实测】`
- Host IP：`【待用户实测】`
- 5432 监听：`【待用户实测】`
- 5000 监听：`【待用户实测】`
- UFW：`【待用户实测】`

---

## 2. 数据库角色与 DDL

```bash
cd /opt/DataBase
export DB_OWNER_PASSWORD='<db_owner 强密码>'
export DB_APP_PASSWORD='<app_rw 强密码>'

sudo -u postgres psql \
  -v db_owner_password="$DB_OWNER_PASSWORD" \
  -v app_rw_password="$DB_APP_PASSWORD" \
  -f sql/00_bootstrap_roles.sql

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DB_HOST=127.0.0.1
export DB_PORT=5432
export DB_NAME=course_db
export DB_ADMIN_USER=db_owner
export DB_ADMIN_PASSWORD="$DB_OWNER_PASSWORD"

python3 scripts/init_db.py create-tables
```

检查：

```bash
psql -h 127.0.0.1 -U db_owner -d course_db -c "\dt"
psql -h 127.0.0.1 -U db_owner -d course_db -c "\di"
psql -h 127.0.0.1 -U db_owner -d course_db -c "\d+ order_item"
```

预期：

- 8 张表；
- 7 个二级索引；
- `order_item` 主键 `(order_id, product_id)`；
- `order_item_id` 唯一。

---

## 3. 种子数据与数据量

```bash
python3 scripts/init_db.py seed
python3 scripts/init_db.py count
psql -h 127.0.0.1 -U db_owner -d course_db -f tests/test_db_counts.sql
```

需要回填：

- 各表行数：`【待用户实测】`
- 合计：`{{MEASURED_TOTAL_ROWS}}`
- 是否 `>100000`：`【待用户实测】`

证据保存：

```bash
mkdir -p docs/evidence/DATA-01
psql -h 127.0.0.1 -U db_owner -d course_db -f tests/test_db_counts.sql \
  > docs/evidence/DATA-01/output.txt 2>&1
```

---

## 4. 最小权限验证

```bash
psql -h 127.0.0.1 -U app_rw -d course_db -c "SELECT current_user, session_user;"
psql -h 127.0.0.1 -U app_rw -d course_db -c \
  "SELECT current_user, rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = current_user;"
psql -h 127.0.0.1 -U app_rw -d course_db -c "CREATE TABLE should_fail(id int);"
psql -h 127.0.0.1 -U app_rw -d course_db -c "DROP TABLE orders;"
psql -h 127.0.0.1 -U app_rw -d course_db -c "TRUNCATE orders;"
```

预期：

- `current_user=app_rw`；
- `rolsuper=f`、`rolcreatedb=f`、`rolcreaterole=f`；
- 三条 DDL/TRUNCATE 都 `permission denied`。

保存到 `docs/evidence/SEC-03/`。

---

## 5. 启动 Flask 与 Windows 访问

Linux：

```bash
chmod +x scripts/run_app.sh
./scripts/run_app.sh
```

Windows：

```powershell
Test-NetConnection <VM_IP> -Port 5000
Test-NetConnection <VM_IP> -Port 5432
Start-Process "http://<VM_IP>:5000/health"
Start-Process "http://<VM_IP>:5000/orders"
```

预期：

- 5000 成功；
- 5432 失败/超时；
- `/health` 返回 `{"ok": true, ...}`；
- 订单列表页可打开。

截图：

- `docs/evidence/ENV-01/health.png`
- `docs/evidence/ENV-02/ports.png`
- `docs/evidence/UI-01/orders-list.png`

---

## 6. 业务闭环实测

按 `docs/demo_flow.md` 执行：

1. 订单列表筛选/分页；
2. 创建订单（正常）；
3. 创建订单（库存不足，验证回滚）；
4. 订单详情（多表 join）；
5. 修改状态；
6. 取消订单（库存回补）；
7. 删除明细（库存回补）；
8. 删除被引用商品（409）；
9. 只删 `demo_drop_me`；
10. EXPLAIN 对比；
11. 并发测试。

需要截图：

- 创建订单成功；
- 库存不足错误；
- 订单详情（地址栏 + 客户/明细/分类/物流/金额）；
- 状态修改；
- 取消后库存回补；
- 删除明细；
- `demo_drop_me` 前后 `\dt`；
- EXPLAIN before/after；
- 并发 CSV/JSON 与 `pg_stat_activity`。

---

## 7. 事务与删表

```bash
psql -h 127.0.0.1 -U db_owner -d course_db -f sql/06_drop_table_demo.sql

export TEST_DB_DSN="host=127.0.0.1 port=5432 dbname=course_db user=app_rw password=$DB_APP_PASSWORD"
pytest -q tests/test_transaction.py
```

需要回填：

- commit 可见：`【待用户实测】`
- rollback 不可见：`【待用户实测】`
- 库存不足回滚：`【待用户实测】`
- 核心表仍在：`【待用户实测】`

---

## 8. EXPLAIN

```bash
mkdir -p docs/evidence/IDX-01 docs/evidence/IDX-02
psql -h 127.0.0.1 -U db_owner -d course_db -f sql/07_explain.sql \
  > docs/evidence/IDX-01/output.txt 2>&1
```

如果要把 before/after 分开，可按脚本注释手工拆分输出。

需要回填：

- 无索引执行时间：`{{EXPLAIN_BEFORE_MS}}`
- 有索引执行时间：`{{EXPLAIN_AFTER_MS}}`
- 计划节点变化：`【待用户实测】`
- 是否命中索引：`【待用户实测】`
- 若未命中，原因：`【待用户实测】`

---

## 9. 并发测试

```bash
python3 scripts/benchmark_concurrency.py \
  --clients 1,10,25,50 \
  --duration 30 \
  --warmup 5 \
  --output-dir tests/results
```

保存：

```bash
mkdir -p docs/evidence/CON-01
cp tests/results/concurrency_*.csv tests/results/concurrency_*_summary.json docs/evidence/CON-01/
```

需要回填：

- 1 并发 TPS/p50/p95/p99：`【待用户实测】`
- 10 并发 TPS：`{{TPS_10}}`
- 25 并发：`【待用户实测】`
- 50 并发 p95：`{{P95_50}}`
- 错误率/死锁/重试：`【待用户实测】`
- 无超卖/无半单/无重复物流/无连接泄漏：`【待用户实测】`

---

## 10. 安全测试

### SQL 注入

在页面/API 输入：

```text
' OR '1'='1
'; DROP TABLE orders; --
% _
```

预期：

- 只作为字面值；
- 不返回全表；
- 表仍存在；
- 无 SQL 错误泄露。

### CSRF

- 不带 `X-CSRF-Token` 的 POST/PATCH/DELETE 应返回 403；
- 浏览器页面操作应正常。

### 错误信息

- 触发 404/500；
- 页面无堆栈/SQL/DSN；
- 日志无密码。

---

## 11. 报告回填

需要替换：

- `{{MEASURED_TOTAL_ROWS}}`
- `{{EXPLAIN_BEFORE_MS}}`
- `{{EXPLAIN_AFTER_MS}}`
- `{{TPS_10}}`
- `{{P95_50}}`
- 所有 `【待用户实测】`

报告位置：

- `docs/report/report.md`
- `docs/05_performance.md`
- `docs/06_concurrency.md`
- `docs/acceptance_matrix.md` 的“证据/实测”列

---

## 12. 提交前检查

- [ ] PostgreSQL 只监听 127.0.0.1；
- [ ] Flask 监听 0.0.0.0:5000；
- [ ] UFW 只开放 5000；
- [ ] `app_rw` 不能 DDL；
- [ ] 总行数 >100000；
- [ ] 1-1/1-N/N-M 有反例与查询；
- [ ] 3NF 检查表完整；
- [ ] 建表/插入/删除/修改/删表/join 均有证据；
- [ ] commit/rollback 均有双连接证据；
- [ ] EXPLAIN before/after 各 3 次；
- [ ] 并发 1/10/25/50 有 CSV/JSON；
- [ ] 两个页面截图含地址栏；
- [ ] 报告无编造数字；
- [ ] `.env` 未提交；
- [ ] 所有占位符已回填或明确说明。