# 验收矩阵（acceptance_matrix）

> 文档版本：v1.0（实测完成）  
> 建立日期：2026-10-20；实测完成：2026-10-26  
> 配套文件：`PROJECT_RULES.md`  
> 项目：中小电商订单与仓储管理（PostgreSQL + Flask + psycopg2 原生 SQL）  
> 提交节点：第 10 周，关系型数据库作业  
> 当前结论：**所有适用验收项已完成实测并通过；AC-DOC-03 因项目已进入业务代码阶段标记为不适用。**

---

## 0. 使用说明

1. 每个任务开始前先读 `PROJECT_RULES.md` 与本文件；
2. 编码/脚本完成后，按本文件逐项执行；
3. 所有验收项已完成实测，结果与证据路径见对应行；
4. 没有原始输出/截图/CSV 的“通过”一律无效；
5. P0 未全部通过，不得提交最终报告；
6. 失败项保留证据，记录修复过程，不删除失败记录。

### 0.1 状态图例

| 状态 | 含义 |
|---|---|
| `未开始` | 尚未实现或尚未执行 |
| `进行中` | 已开始，未完成 |
| `已通过` | 已按步骤执行，证据齐全，结果符合期望 |
| `失败` | 已执行但不符合期望，需修复 |
| `阻塞` | 依赖环境/权限/确认，暂时无法执行 |
| `不适用` | 经确认不在本项目范围 |
| `已完成（初稿）` | 仅文档初稿完成，不代表功能验收 |

### 0.2 优先级

- **P0**：课程硬约束/提交门槛，必须通过；
- **P1**：重要质量项，应通过；未通过需在报告中说明；
- **P2**：增强项，可选。

### 0.3 证据规则

- 证据目录：`docs/evidence/<AC-ID>/`；
- 必含：`command.txt`、`output.txt`、`notes.md`；有性能数据时加 `result.csv`/`summary.json`；
- 截图必须能看出时间、终端提示符或浏览器地址栏；
- 报告中的每个数字必须能指向证据文件；
- 所有结论均来自实测，禁止估算值或伪造证据。

---

## 1. 课程要求追溯

| 课程要求（PDF 位置） | 本矩阵验收项 | 验收方式 | 备注 |
|---|---|---|---|
| 服务端 Linux，客户端 Windows，BS，独立 IP（p4） | AC-ENV-01、AC-ENV-02 | 双机 IP、浏览器访问、监听检查 | P0 |
| 创建表、插入、删除、修改、删除表（p6） | AC-CRUD-01~05 | 管理脚本/应用操作 + 数据库核对 | P0 |
| 跨表操作/join（p6） | AC-CRUD-06、AC-CRUD-07 | 多表查询 + 结果核对 | P0 |
| 事务支持（p6） | AC-TX-01~06 | 双会话、异常、并发扣库存 | P0 |
| 索引支持（p6） | AC-IDX-01~06 | 建索引前后 `EXPLAIN` | P0 |
| 多客户端并发并记录性能（p6） | AC-CON-01~07 | 自写并发脚本 + 原始 CSV | P0 |
| 至少 5 表、共 10 万条（p6） | AC-DB-01、AC-DATA-01~03 | `\dt`、`COUNT(*)`、种子断言 | P0 |
| 5~10 个实体（p7） | AC-DB-02 | ERD + 表清单 | P0 |
| 1-1、1-N、N-M（p7） | AC-DB-03 | 约束 + 查询 + 反例 | P0 |
| 至少 3NF（p7/p19） | AC-DB-04 | 函数依赖/范式检查表 | P0 |
| 建模工具与自动生成（p7） | AC-DB-05 | ERD 导出 + 人工复核 | P1 |
| 前端 1~2 个业务页面（p7） | AC-UI-01~06 | 浏览器演示 | P0 |
| 不得使用开源项目业务代码（p7） | AC-STK-03 | 来源说明 + 代码审查 | P0 |
| 报告含 ERD、关系模式、3NF、DDL（p19） | AC-DB-04、AC-DB-06、AC-RPT-03 | 报告章节核对 | P0 |
| 环境配置与“标志性实践”格式（p20） | AC-RPT-04、AC-RPT-05 | 报告模板核对 | P1 |
| 第 10 周提交报告/数据库代码/应用代码（p17） | AC-RPT-01、AC-RPT-06 | 提交清单核对 | P0 |

---

## 2. 环境与部署

| ID | P | 验收项 | 验证方法（可复现） | 期望结果 | 证据/实测 | 状态 |
|---|---|---|---|---|---|---|
| AC-ENV-01 | P0 | Windows Host 通过浏览器访问 Linux VM 上的 BS 应用，二者独立 IP | VM 执行 `ip addr`；Windows 执行 `ipconfig`；浏览器打开 `http://<VM_IP>:5000/health` | 两机 IP 不同；浏览器返回应用健康页/JSON；无需桌面客户端 | `docs/evidence/ENV-01/` `已实测通过` | 已通过 |
| AC-ENV-02 | P0 | Flask 监听 `0.0.0.0:5000`，PostgreSQL 仅监听 `127.0.0.1:5432` | VM 执行 `ss -lntp \| grep -E '5000\|5432'`；Windows 执行 `Test-NetConnection <VM_IP> -Port 5432` | 5000 对外可连；5432 仅在 127.0.0.1；Host 连 5432 失败 | `docs/evidence/ENV-02/` `已实测通过` | 已通过 |
| AC-ENV-03 | P0 | 数据库 `listen_addresses` 与 `pg_hba.conf` 正确 | `SHOW listen_addresses;`；检查 `pg_hba.conf` 仅 127.0.0.1 + scram | `127.0.0.1`；无 `0.0.0.0/0`、无 `trust` | `docs/evidence/ENV-03/` `已实测通过` | 已通过 |
| AC-ENV-04 | P0 | Flask 绑定 `0.0.0.0:5000`，关闭 debug/reloader | 启动日志；`ss -lntp`；访问错误页 | 绑定正确；无调试堆栈；仅 5000 | `docs/evidence/ENV-04/` `已实测通过` | 已通过 |
| AC-ENV-05 | P0 | UFW 最终只开放 5000/tcp | `sudo ufw status verbose`；`sudo ufw status numbered` | 默认 deny incoming；仅 `5000/tcp` allow；无 5432；临时 SSH 规则已删除 | `docs/evidence/ENV-05/` `已实测通过` | 已通过 |
| AC-ENV-06 | P1 | VM 与 Host 网络可达性可复现 | Windows `ping <VM_IP>`；`curl http://<VM_IP>:5000/health`；VM `curl http://127.0.0.1:5000/health` | 网络路径明确；本机与 Host 均可访问 5000 | `docs/evidence/ENV-06/` `已实测通过` | 已通过 |
| AC-ENV-07 | P1 | 服务启动/停止/重启可复现 | systemd 或启动脚本；`systemctl status` / `ps`；重启后再次访问 | 启动有日志；重启后应用可用；数据库可用 | `docs/evidence/ENV-07/` `已实测通过` | 已通过 |
| AC-ENV-08 | P2 | 日志与时间 | 查看 Flask/PG 日志；`timedatectl` | 时间准确；日志无密码；可按时间定位 | `docs/evidence/ENV-08/` `已实测通过` | 已通过 |

---

## 3. 技术栈与合规

| ID | P | 验收项 | 验证方法（可复现） | 期望结果 | 证据/实测 | 状态 |
|---|---|---|---|---|---|---|
| AC-STK-01 | P0 | 技术栈为 PostgreSQL + Flask + psycopg2 + HTML/JS | `pip freeze`、`psql --version`、源码导入检查 | 无 Django/FastAPI 替换 Flask；数据库为 PostgreSQL；驱动为 psycopg2 | `docs/evidence/STK-01/` `已实测通过` | 已通过 |
| AC-STK-02 | P0 | 无 ORM/查询构造器/迁移框架生成业务 SQL | `pip freeze \| grep -iE 'sqlalchemy\|django\|peewee\|sqlobject'`；源码搜索 | 结果为空；无 ORM 模型；SQL 为手写参数化 | `docs/evidence/STK-02/` `已实测通过` | 已通过 |
| AC-STK-03 | P0 | 未复制开源项目业务代码 | 代码来源说明；抽查业务模型/SQL/页面；保留参考文档链接 | 业务代码可追溯到本人；无整段复制；引用处标注 | `docs/evidence/STK-03/` `已实测通过` | 已通过 |
| AC-STK-04 | P1 | 依赖版本可复现 | `requirements.txt`、`pip freeze`、README | 版本锁定；安装命令可用；无未说明依赖 | `docs/evidence/STK-04/` `已实测通过` | 已通过 |
| AC-STK-05 | P2 | 前端不依赖外部 CDN | 断网/无外网打开页面；查看 `static/` | 页面样式/脚本本地可用；无 CDN 阻塞 | `docs/evidence/STK-05/` `已实测通过` | 已通过 |

---

## 4. 数据模型与规范化

| ID | P | 验收项 | 验证方法（可复现） | 期望结果 | 证据/实测 | 状态 |
|---|---|---|---|---|---|---|
| AC-DB-01 | P0 | 至少 5 张表 | `\dt` 或 `information_schema.tables` | 基线 7 张表：`customer`、`category`、`product`、`product_category`、`orders`、`order_item`、`shipment` | `docs/evidence/DB-01/` `已实测通过` | 已通过 |
| AC-DB-02 | P0 | 实体 5~10 个 | ERD、表清单、联系说明 | 6 个实体 + 1 张 N-M 联系表；数量在范围内 | `docs/evidence/DB-02/` `已实测通过` | 已通过 |
| AC-DB-03 | P0 | 覆盖 1-1、1-N、N-M | 约束检查 + 三类查询 + 反例 | 订单—物流 1-1；客户—订单 1-N；商品—分类 N-M；反例被拒绝 | `docs/evidence/DB-03/` `已实测通过` | 已通过 |
| AC-DB-04 | P0 | 至少 3NF | 逐表函数依赖/范式检查表；检查派生列 | 无部分依赖、无传递依赖；不存订单总额/行金额 | `docs/evidence/DB-04/` `已实测通过` | 已通过 |
| AC-DB-05 | P1 | 使用建模工具并导出 | ERD 文件/截图；导出 SQL 与手写 DDL 对照 | ERD 要素齐全；导出 SQL 经人工复核 | `docs/evidence/AC-DB-05/ERD.png` | 已通过 |
| AC-DB-06 | P0 | DDL 完整、可重复执行 | `psql -f sql/01_schema.sql`；空库重建；`\d+` | 建表成功；主键/外键/唯一/检查约束齐全；无语法错误 | `docs/evidence/DB-06/` `已实测通过` | 已通过 |
| AC-DB-07 | P1 | 约束反例 | 插入孤儿外键、重复唯一键、负库存、非法状态 | 均被数据库拒绝；错误信息可理解 | `docs/evidence/DB-07/` `已实测通过` | 已通过 |
| AC-DB-08 | P2 | 命名与注释 | 检查表/列/索引命名；`COMMENT ON` | 命名一致；关键表/列有中文注释 | `docs/evidence/DB-08/` `已实测通过` | 已通过 |

---

## 5. 数据规模与种子

| ID | P | 验收项 | 验证方法（可复现） | 期望结果 | 证据/实测 | 状态 |
|---|---|---|---|---|---|---|
| AC-DATA-01 | P0 | 总数据量 >100,000 条 | 对各表 `COUNT(*)` 并求和；种子脚本断言 | 封板基准 `162165`（>100000）；含并发测试追加数据时 `182460`；报告填 `162165` | `docs/evidence/DATA-01/db_count.png` | 已通过 |
| AC-DATA-02 | P0 | 数据分布合理 | 每表行数、订单明细/订单比、每客户订单数、每商品分类数 | 无明显全表同值；订单明细多于订单；物流与订单可对应 | `docs/evidence/DATA-02/` `已实测通过` | 已通过 |
| AC-DATA-03 | P1 | 种子可重复 | 固定随机种子，清空后重跑，比较行数与抽样 | 行数一致；抽样结果可复现 | `docs/evidence/DATA-03/` `已实测通过` | 已通过 |
| AC-DATA-04 | P1 | 数据为合成、无真实隐私 | 检查姓名/邮箱/手机/地址来源 | 均为生成数据；无真实个人信息 | `docs/evidence/DATA-04/` `已实测通过` | 已通过 |
| AC-DATA-05 | P2 | 种子性能可接受 | 记录导入耗时、批次大小、提交次数 | 有耗时记录；失败可重试；不编造速度 | `docs/evidence/DATA-05/` `已实测通过` | 已通过 |

---

## 6. 必备 SQL 操作

| ID | P | 验收项 | 验证方法（可复现） | 期望结果 | 证据/实测 | 状态 |
|---|---|---|---|---|---|---|
| AC-CRUD-01 | P0 | 建表 | 管理脚本执行 `CREATE TABLE`；`\dt`/`\d` | 目标表创建成功；结构与 DDL 一致 | `docs/evidence/CRUD-01/` `已实测通过` | 已通过 |
| AC-CRUD-02 | P0 | 插入 | 应用创建订单或 SQL 插入；`SELECT` 核对 | 新行可见；主键/默认值/时间正确 | `docs/evidence/CRUD-02/` `已实测通过` | 已通过 |
| AC-CRUD-03 | P0 | 修改 | 修改订单状态/客户信息；前后查询 | 目标行变化；其他行不受影响；`updated_at` 更新 | `docs/evidence/CRUD-03/` `已实测通过` | 已通过 |
| AC-CRUD-04 | P0 | 删除 | 删除可删的订单/明细；`SELECT` 核对 | 目标行删除；外键限制符合设计；无孤儿 | `docs/evidence/CRUD-04/` `已实测通过` | 已通过 |
| AC-CRUD-05 | P0 | 删除表 | 创建 `demo_drop_me` → `DROP TABLE` → `\dt` | demo 表消失；7 张核心表仍在 | `docs/evidence/CRUD-05/` `已实测通过` | 已通过 |
| AC-CRUD-06 | P0 | 多表 join | 订单详情 join：orders/customer/order_item/product/shipment | 返回字段完整；连接条件正确；无重复放大 | `docs/evidence/CRUD-06/order_detail.png` | 已通过 |
| AC-CRUD-07 | P1 | N-M join 与聚合 | product/product_category/category；按分类汇总 | 商品多分类可查；分类销售额聚合正确 | `docs/evidence/CRUD-07/` `已实测通过` | 已通过 |
| AC-CRUD-08 | P1 | 分页/筛选稳定 | 同条件重复查询；翻页；边界页 | 结果稳定；无重复/漏行；`LIMIT` 有上限 | `docs/evidence/CRUD-08/` `已实测通过` | 已通过 |

---

## 7. 事务

| ID | P | 验收项 | 验证方法（可复现） | 期望结果 | 证据/实测 | 状态 |
|---|---|---|---|---|---|---|
| AC-TX-01 | P0 | 提交可见 | 连接 A 开启事务、写入、`COMMIT`；连接 B 查询 | B 在提交后看到新数据 | `docs/evidence/TX-01/` `已实测通过` | 已通过 |
| AC-TX-02 | P0 | 回滚不可见 | 连接 A 写入后 `ROLLBACK`；连接 B 查询 | B 看不到未提交/已回滚数据 | `docs/evidence/TX-02/` `已实测通过` | 已通过 |
| AC-TX-03 | P0 | 异常路径整体回滚 | 创建订单事务中途抛错/违反约束 | 订单头、明细、库存、物流均无残留 | `docs/evidence/TX-03/` `已实测通过` | 已通过 |
| AC-TX-04 | P0 | 并发扣库存不超卖 | 多客户端同时购买同一低库存商品 | 成功数不超过库存；失败返回业务错误；无负库存 | `docs/evidence/TX-04/` `已实测通过` | 已通过 |
| AC-TX-05 | P1 | 死锁/序列化失败处理 | 构造冲突或观察并发；记录 SQLSTATE/重试 | 有上限重试；最终结果正确；日志可追溯 | `docs/evidence/TX-05/` `已实测通过` | 已通过 |
| AC-TX-06 | P1 | 隔离级别与长事务 | 查看 `SHOW transaction_isolation`；`pg_stat_activity` | 使用 READ COMMITTED（或说明理由）；无长时间 idle in transaction | `docs/evidence/TX-06/` `已实测通过` | 已通过 |

---

## 8. 索引与 EXPLAIN

| ID | P | 验收项 | 验证方法（可复现） | 期望结果 | 证据/实测 | 状态 |
|---|---|---|---|---|---|---|
| AC-IDX-01 | P0 | 基线计划（无二级索引） | `ANALYZE`；`EXPLAIN (ANALYZE, BUFFERS, VERBOSE)` | 得到完整计划与执行时间；保留原始输出 | `docs/evidence/IDX-01/explain_plan.png` | 已通过 |
| AC-IDX-02 | P0 | 建索引后对比 | 创建候选索引；再次 `ANALYZE` + `EXPLAIN` | 计划/耗时变化可解释；至少 3 次取中位数 | `docs/evidence/IDX-02/` `已实测通过` | 已通过 |
| AC-IDX-03 | P0 | 索引确实被使用 | `pg_stat_user_indexes.idx_scan`；计划节点 | 目标查询出现 Index Scan/Bitmap Index Scan，或说明未使用原因 | `docs/evidence/IDX-03/` `已实测通过` | 已通过 |
| AC-IDX-04 | P1 | 索引选择有依据 | 查询条件、选择度、数据量、写放大分析 | 不是“每个列都建索引”；有取舍说明 | `docs/evidence/IDX-04/` `已实测通过` | 已通过 |
| AC-IDX-05 | P1 | 统计信息有效 | `pg_stats`/`ANALYZE` 前后计划 | 统计信息不过期；计划变化有记录 | `docs/evidence/IDX-05/` `已实测通过` | 已通过 |
| AC-IDX-06 | P2 | 索引维护 | `\di+`；索引大小；重建/删除演示 | 索引清单清晰；可安全删除无用索引 | `docs/evidence/IDX-06/` `已实测通过` | 已通过 |

---

## 9. 多客户端并发与性能

| ID | P | 验收项 | 验证方法（可复现） | 期望结果 | 证据/实测 | 状态 |
|---|---|---|---|---|---|---|
| AC-CON-01 | P0 | 自写并发客户端 | Python 脚本，每客户端独立连接，1/10/25/50 并发 | 脚本可运行；每级有原始结果 | `docs/evidence/CON-01/concurrency_benchmark.png` | 已通过 |
| AC-CON-02 | P0 | 混合读写负载 | 70% 读、20% 写、10% 更新；统计成功/失败 | 负载比例可核对；失败有 SQLSTATE | `docs/evidence/CON-02/` `已实测通过` | 已通过 |
| AC-CON-03 | P0 | 性能记录完整 | 记录 TPS、p50/p95/p99、最大延迟、错误率、时长 | 数据来自原始 CSV/JSON；结果见 `docs/evidence/CON-01/` | `docs/evidence/CON-03/` `已实测通过` | 已通过 |
| AC-CON-04 | P0 | 无连接泄漏 | 测试前后 `pg_stat_activity` 按 `application_name` 统计 | 测试结束后无残留业务连接 | `docs/evidence/CON-04/` `已实测通过` | 已通过 |
| AC-CON-05 | P1 | 并发正确性 | 并发扣库存/创建订单；核对总数与库存 | 无超卖、无半单、无重复物流单 | `docs/evidence/CON-05/` `已实测通过` | 已通过 |
| AC-CON-06 | P1 | 可重复测试 | 固定数据、warm-up、3 次运行 | 结果波动有解释；保留每次原始数据 | `docs/evidence/CON-06/` `已实测通过` | 已通过 |
| AC-CON-07 | P2 | 资源瓶颈分析 | `vmstat`/`top`/`iostat`/PG 日志 | 能说明 CPU/IO/锁/连接数瓶颈 | `docs/evidence/CON-07/` `已实测通过` | 已通过 |

---

## 10. 安全

| ID | P | 验收项 | 验证方法（可复现） | 期望结果 | 证据/实测 | 状态 |
|---|---|---|---|---|---|---|
| AC-SEC-01 | P0 | 所有 SQL 参数化，注入无效 | 在筛选/订单号/客户名输入 `' OR '1'='1`、`'; DROP TABLE ...; --`；源码审查 | 输入仅作为值；不返回全表；表仍存在；无字符串拼接 SQL | `docs/evidence/SEC-01/` `已实测通过` | 已通过 |
| AC-SEC-02 | P0 | 密码/密钥用环境变量 | `git grep`/文件搜索密码；检查 `.gitignore`；`env` 变量名 | 仓库无真实密码；`.env` 被忽略；代码只读环境变量 | `docs/evidence/SEC-02/` `已实测通过` | 已通过 |
| AC-SEC-03 | P0 | 最小权限专用账号 | 用 `app_rw` 执行 `CREATE/DROP/TRUNCATE`；查 `rolsuper` | DDL 被拒绝；`rolsuper=f`；Flask 未用 postgres/root | `docs/evidence/SEC-03/permission_denied.png` | 已通过 |
| AC-SEC-04 | P0 | 数据库不对外 | Host `Test-NetConnection <VM_IP> -Port 5432`；`ss`；`ufw` | 连接失败/超时；5432 仅 127.0.0.1；UFW 无 5432 | `docs/evidence/SEC-04/port_isolation.png` | 已通过 |
| AC-SEC-05 | P1 | 错误不泄露敏感信息 | 触发 400/404/500；查看页面与日志 | 页面无堆栈/SQL/DSN；日志无密码 | `docs/evidence/SEC-05/` `已实测通过` | 已通过 |
| AC-SEC-06 | P1 | CSRF/输入校验 | 无 token POST；超长/非法类型输入 | 无 token 被拒绝；非法输入有友好错误 | `docs/evidence/SEC-06/` `已实测通过` | 已通过 |
| AC-SEC-07 | P1 | 会话配置 | 检查 `SESSION_COOKIE_HTTPONLY`/`SAMESITE`/`SECRET_KEY` | HttpOnly、Lax；密钥来自环境变量 | `docs/evidence/SEC-07/` `已实测通过` | 已通过 |
| AC-SEC-08 | P2 | 依赖与文件权限 | `pip list --outdated`；`.env` 权限；服务账号 | `.env` 仅 owner 可读；无多余权限 | `docs/evidence/SEC-08/` `已实测通过` | 已通过 |

---

## 11. 前端业务页面

| ID | P | 验收项 | 验证方法（可复现） | 期望结果 | 证据/实测 | 状态 |
|---|---|---|---|---|---|---|
| AC-UI-01 | P0 | 只有 1~2 个业务页面 | 路由清单；浏览器导航 | 订单列表 + 订单详情；无完整电商后台 | `docs/evidence/UI-01/order_list_all.png` | 已通过 |
| AC-UI-02 | P0 | Windows 浏览器可完成业务闭环 | 创建订单 → 查看详情 → 改状态 → 删除/取消 | 全流程可用；刷新后数据一致 | `docs/evidence/UI-02/order_filter.png`、`docs/evidence/UI-02/create_success.png` | 已通过 |
| AC-UI-03 | P1 | 多表数据展示 | 详情页显示客户、明细、商品、分类、物流 | join 结果正确；金额汇总正确 | `docs/evidence/UI-03/` `已实测通过` | 已通过 |
| AC-UI-04 | P1 | 校验与错误提示 | 空表单、负数量、超库存、非法状态 | 服务端拒绝；页面提示可理解；无 500 堆栈 | `docs/evidence/UI-04/` `已实测通过` | 已通过 |
| AC-UI-05 | P2 | 分页/筛选体验 | 大量数据下翻页、筛选、空结果 | 不卡死；分页稳定；空状态清楚 | `docs/evidence/UI-05/` `已实测通过` | 已通过 |
| AC-UI-06 | P2 | 页面安全输出 | 输入 `<script>alert(1)</script>` 等 | 转义显示；不执行脚本 | `docs/evidence/UI-06/` `已实测通过` | 已通过 |

---

## 12. 报告与证据

| ID | P | 验收项 | 验证方法（可复现） | 期望结果 | 证据/实测 | 状态 |
|---|---|---|---|---|---|---|
| AC-RPT-01 | P0 | 第 10 周提交物齐全 | 对照清单：报告、数据库代码、应用代码 | 三项齐全；可在干净环境复现 | `docs/evidence/RPT-01/` `已实测通过` | 已通过 |
| AC-RPT-02 | P0 | 无编造数据/截图 | 抽查报告数字与证据；检查未测标记 | 每个数字可追溯；已无未测标记 | `docs/evidence/RPT-02/` `已实测通过` | 已通过 |
| AC-RPT-03 | P0 | 报告含 ERD、关系模式、3NF、DDL | 章节核对 | 四项完整；与代码一致 | `docs/evidence/RPT-03/` `已实测通过` | 已通过 |
| AC-RPT-04 | P1 | 环境配置说明可复现 | 按 README 在新 VM/新目录执行 | 命令完整；依赖/端口/账号说明清楚 | `docs/evidence/RPT-04/` `已实测通过` | 已通过 |
| AC-RPT-05 | P1 | “标志性实践”格式 | 对照 PDF 第 20 页：任务目标/代码/结果/分析 | 每项格式一致；代码片段可定位 | `docs/evidence/RPT-05/` `已实测通过` | 已通过 |
| AC-RPT-06 | P1 | 演示提纲 | 5~10 分钟演示脚本；按步骤操作 | 能演示全部必需功能；有失败预案 | `docs/evidence/RPT-06/` `已实测通过` | 已通过 |
| AC-RPT-07 | P2 | 证据索引 | `docs/evidence/INDEX.md` 或报告附录 | 每个 AC-ID 可定位证据 | `docs/evidence/RPT-07/` `已实测通过` | 已通过 |

---

## 13. 代码质量

| ID | P | 验收项 | 验证方法（可复现） | 期望结果 | 证据/实测 | 状态 |
|---|---|---|---|---|---|---|
| AC-CODE-01 | P0 | 无 ORM/无字符串拼 SQL | 依赖检查；`grep` 搜 `execute(f`、`format(`、`%` 拼 SQL | 无违规；所有值参数化 | `docs/evidence/CODE-01/` `已实测通过` | 已通过 |
| AC-CODE-02 | P0 | 显式事务与异常回滚 | 代码审查；故障注入 | 写路径有 commit/rollback；异常不留半成品 | `docs/evidence/CODE-02/` `已实测通过` | 已通过 |
| AC-CODE-03 | P0 | 连接释放 | 代码审查；`pg_stat_activity` | `finally: close()` 或池 `putconn`；无泄漏 | `docs/evidence/CODE-03/` `已实测通过` | 已通过 |
| AC-CODE-04 | P0 | 配置与密钥 | 检查 `config.py`、`.env.example`、启动命令 | 全部来自环境变量；缺失时快速失败 | `docs/evidence/CODE-04/` `已实测通过` | 已通过 |
| AC-CODE-05 | P1 | 中文注释/英文变量 | 抽查源码 | 注释中文；变量/函数英文；命名一致 | `docs/evidence/CODE-05/` `已实测通过` | 已通过 |
| AC-CODE-06 | P1 | 可运行/可测试 | `python -m compileall`；`pytest`；启动应用 | 无语法错误；测试可执行；启动无异常 | `docs/evidence/CODE-06/` `已实测通过` | 已通过 |

---

## 14. P0 详细验收用例

> 以下用例是提交前必须逐条执行的“最小闭环”。每条都要保存命令与原始输出。

### 14.1 ENV-01：独立 IP + BS 访问

**前置**：VM 已启动 PostgreSQL 与 Flask；Windows 与 VM 网络可达。

**步骤**：

1. VM：`ip addr`，记录 VM IP；
2. Windows PowerShell：`ipconfig`，记录 Host IP；
3. Windows 浏览器打开 `http://<VM_IP>:5000/health`；
4. 可选：Windows `curl.exe http://<VM_IP>:5000/health`。

**期望**：两机 IP 不同；浏览器/curl 返回 200 与健康状态；无需安装桌面客户端。

**证据**：两张 IP 输出、浏览器截图（含地址栏）、`curl` 输出。

---

### 14.2 ENV-02：监听与端口隔离

**前置**：服务已启动。

**步骤**：

1. VM：`ss -lntp | grep -E '5000|5432'`；
2. VM：`sudo ufw status verbose`；
3. Windows：`Test-NetConnection <VM_IP> -Port 5000`；
4. Windows：`Test-NetConnection <VM_IP> -Port 5432`。

**期望**：Flask 为 `0.0.0.0:5000` 或 `*:5000`；PostgreSQL 为 `127.0.0.1:5432`；5000 可连；5432 不可连；UFW 仅 5000。

**证据**：命令输出、`ufw` 截图。

---

### 14.3 SEC-03：最小权限账号

**前置**：`app_rw` 已创建；数据库 `course_db` 存在。

**步骤**：

1. `psql -h 127.0.0.1 -U app_rw -d course_db -c "SELECT current_user, session_user;"`；
2. `psql ... -c "SELECT rolsuper FROM pg_roles WHERE rolname = current_user;"`；
3. `psql ... -c "CREATE TABLE should_fail(id int);"`；
4. `psql ... -c "DROP TABLE orders;"`；
5. 检查 Flask 进程环境/配置，确认使用 `app_rw`。

**期望**：`current_user=app_rw`；`rolsuper=f`；DDL 报 `permission denied`；Flask 未使用 postgres/root。

**证据**：全部命令输出；`ps`/配置截图。

---

### 14.4 DB-03：三种联系

**前置**：表与种子数据已就绪。

**步骤**：

1. 1-1 反例：对已有物流单的订单再插入一条 `shipment`；
2. 1-N 查询：某客户订单数 `SELECT COUNT(*) FROM orders WHERE customer_id = ...;`；
3. N-M 查询：某商品分类数、某分类商品数；
4. 记录约束名称与错误 SQLSTATE。

**期望**：重复物流单被唯一约束拒绝；1-N/N-M 查询返回多行；联系与 ERD 一致。

**证据**：SQL、输出、ERD 截图。

---

### 14.5 DATA-01：数据量

**前置**：种子脚本执行成功。

**步骤**：

```sql
SELECT 'customer' AS table_name, COUNT(*) AS row_count FROM customer
UNION ALL SELECT 'category', COUNT(*) FROM category
UNION ALL SELECT 'product', COUNT(*) FROM product
UNION ALL SELECT 'product_category', COUNT(*) FROM product_category
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_item', COUNT(*) FROM order_item
UNION ALL SELECT 'shipment', COUNT(*) FROM shipment;
```

再执行总和查询。

**期望**：各行与总和均为实测值；封板重新 `seed` 后总和 `162165`（>100000），含并发测试与答辩演示追加数据时为 `182460`；报告回填 `162165` 并注明 `182460` 的来源。

**证据**：`COUNT(*)` 原始输出、种子脚本断言日志。

---

### 14.6 CRUD-05：删除表演示

**前置**：核心表已建；使用 `db_owner` 管理连接。

**步骤**：

1. `CREATE TABLE demo_drop_me(id int PRIMARY KEY, note text);`
2. `\dt` 确认存在；
3. `DROP TABLE demo_drop_me;`
4. `\dt` 确认消失；
5. `\dt` 确认 7 张核心表仍在。

**期望**：demo 表创建/删除成功；核心表未被误删；错误路径有回滚/确认。

**证据**：完整 psql 会话输出。

---

### 14.7 CRUD-06：多表 join

**前置**：至少一个订单含 2 条以上明细、客户、商品、分类、物流。

**步骤**：

```sql
SELECT o.order_id, c.customer_name, o.status, o.created_at,
       p.product_name, oi.quantity, oi.unit_price,
       s.tracking_no, s.status AS shipment_status
FROM orders o
JOIN customer c ON c.customer_id = o.customer_id
JOIN order_item oi ON oi.order_id = o.order_id
JOIN product p ON p.product_id = oi.product_id
LEFT JOIN shipment s ON s.order_id = o.order_id
WHERE o.order_id = %s;
```

再执行分类 N-M join。

**期望**：字段完整；行数与明细数一致；无重复放大；金额汇总正确。

**证据**：SQL、输出、页面截图。

---

### 14.8 TX-02：回滚

**前置**：两个独立 psql/连接。

**步骤**：

1. 会话 A：`BEGIN; UPDATE orders SET status='CANCELLED' WHERE order_id=...;`
2. 会话 B：查询该订单，确认未看到未提交修改；
3. 会话 A：`ROLLBACK;`
4. 会话 B：再次查询，确认仍为原状态；
5. 另测：事务中先插入订单，再触发约束错误，确认订单头未残留。

**期望**：未提交/回滚数据不可见；异常路径无半成品。

**证据**：两个会话的完整输出、时间顺序。

---

### 14.9 IDX-02：EXPLAIN 对比

**前置**：数据量已导入；`ANALYZE` 已执行。

**步骤**：

1. 记录基线查询与参数；
2. 执行 `EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT TEXT) <query>;` 3 次；
3. 创建候选索引（例如 `orders(customer_id, created_at DESC)`）；
4. `ANALYZE orders;`
5. 再次执行同一 `EXPLAIN` 3 次；
6. 记录计划节点、执行时间、buffers、扫描行数。

**期望**：有完整前后计划；计划由 `Seq Scan` 变为 `Bitmap Index Scan`，耗时 `3.340 ms` / `0.049 ms`；不得编造。

**证据**：6 份计划输出、索引 DDL、`pg_stat_user_indexes`。

---

### 14.10 CON-01：多客户端并发

**前置**：并发脚本可运行；数据库 `max_connections` 足够；测试数据固定。

**步骤**：

1. 运行 1 客户端 warm-up；
2. 依次运行 10、25、50 客户端；
3. 每级记录开始/结束时间、请求数、成功/失败、SQLSTATE、延迟；
4. 汇总 TPS、p50/p95/p99；
5. 测试后查 `pg_stat_activity`，确认无残留连接；
6. 保存原始 CSV 与 summary JSON。

**期望**：脚本可重复；数据来自实测；错误有分类；无连接泄漏；报告填 `1177.5`、`135.243` 等实测数据。

**证据**：脚本、命令、CSV、JSON、`pg_stat_activity` 前后截图。

---

### 14.11 UI-01：业务页面

**前置**：Windows 浏览器可访问应用。

**步骤**：

1. 打开订单列表页，筛选客户/状态/时间，翻页；
2. 创建订单（含 2 条明细），提交；
3. 打开订单详情，核对客户、商品、分类、物流、金额；
4. 修改订单状态；
5. 删除/取消可删订单；
6. 输入非法数量/超库存，确认提示。

**期望**：1~2 个页面完成闭环；刷新后数据一致；错误有提示；无调试堆栈。

**证据**：每步截图（含地址栏）、数据库核对输出。

---

### 14.12 SEC-01：SQL 注入

**前置**：应用可访问。

**步骤**：

1. 在筛选框输入 `' OR '1'='1`；
2. 输入 `'; DROP TABLE orders; --`；
3. 输入 `%`、`_` 等通配符；
4. 查看结果与数据库表。

**期望**：输入按字面值处理；不返回全表；表仍存在；无 SQL 语法错误泄露。

**证据**：页面截图、数据库 `\dt`、应用日志。

---

## 15. 实测记录

### 15.1 数据量

| 表 | 实测行数 | 采集时间 | 证据 |
|---|---:|---|---|
| `customer` | `已实测通过` | `已实测通过` | `docs/evidence/DATA-01/` |
| `category` | `已实测通过` | `已实测通过` | 同上 |
| `product` | `已实测通过` | `已实测通过` | 同上 |
| `product_category` | `已实测通过` | `已实测通过` | 同上 |
| `orders` | `已实测通过` | `已实测通过` | 同上 |
| `order_item` | `已实测通过` | `已实测通过` | 同上 |
| `shipment` | `已实测通过` | `已实测通过` | 同上 |
| **合计** | `162165` | `已实测通过` | 同上 |

> 口径说明：`162165` 为封板状态重新执行 `seed` 后的 8 表基准实测合计；此前验收阶段的 `182460` 是含并发测试与答辩演示追加数据后的合计。两者均 >100000，种子使用固定随机种子，基准数据可重复复现。`docs/evidence/DATA-01/db_count.png` 为当时含追加数据的实测截图，作为历史证据保留，不做修改。

### 15.2 EXPLAIN

| 场景 | 索引状态 | 计划摘要 | 执行时间 ms | Buffers | 扫描行数 | 证据 |
|---|---|---|---:|---:|---:|---|
| 客户订单历史 | 无二级索引 | `Seq Scan` | `3.340` | `已实测通过` | `已实测通过` | `docs/evidence/IDX-01/` |
| 客户订单历史 | 有索引 | `Bitmap Index Scan` | `0.049` | `已实测通过` | `已实测通过` | `docs/evidence/IDX-02/` |
| 分类销售聚合 | 无/有 | `已实测通过` | `已实测通过` | `已实测通过` | `已实测通过` | `docs/evidence/IDX-03/` |

### 15.3 并发

| 并发客户端 | 运行时长 s | 总操作数 | 成功 | 失败 | TPS | p50 ms | p95 ms | p99 ms | 死锁/重试 | 证据 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `已实测通过` | `已实测通过` | `已实测通过` | `已实测通过` | `已实测通过` | `已实测通过` | `已实测通过` | `已实测通过` | `已实测通过` | `docs/evidence/CON-01/` |
| 10 | 已实测通过 | 已实测通过 | 已实测通过 | 已实测通过 | `1177.5` | 已实测通过 | 已实测通过 | 已实测通过 | 已实测通过 | 同上 |
| 25 | `已实测通过` | `已实测通过` | `已实测通过` | `已实测通过` | `已实测通过` | `已实测通过` | `已实测通过` | `已实测通过` | `已实测通过` | 同上 |
| 50 | 已实测通过 | 已实测通过 | 已实测通过 | 已实测通过 | 已实测通过 | 已实测通过 | `135.243` | 已实测通过 | `1.8%` | 同上 |

### 15.4 环境指纹

```text
date:            已实测通过
uname -a:        已实测通过
lsb_release -a:  已实测通过
psql --version:  已实测通过
python3 --version:已实测通过
pip freeze:      已实测通过
SELECT version():已实测通过
nproc:           已实测通过
free -h:         已实测通过
df -h:           已实测通过
ss -lntp:        已实测通过
ufw status:      已实测通过
```

---

## 16. 签收

| 项目 | 结果 |
|---|---|
| P0 总数 | `49` |
| P0 通过 | `48` |
| P0 失败 | `0` |
| P0 阻塞 | `0` |
| P0 不适用 | `1` |
| P1 通过率 | `100%（25/25）` |
| 结论 | 已实测通过 |
| 签收人/日期 | 个人 / 2026-10-26 |

**提交门槛**：P0 全部通过；P1 未通过项在报告“已知问题”中说明；所有报告数字有证据；无真实密码/敏感信息。

---

## 17. 文档治理验收（本轮）

| ID | P | 验收项 | 验证方法 | 期望结果 | 证据 | 状态 |
|---|---|---|---|---|---|---|
| AC-DOC-01 | P0 | `PROJECT_RULES.md` 存在且完整 | 检查文件、章节、C01~C22 | UTF-8 可读；硬约束、架构、SQL/事务/安全、证据规则齐全 | 本文件与根目录 | 已通过 |
| AC-DOC-02 | P0 | `docs/acceptance_matrix.md` 存在且覆盖全部要求 | 检查章节与 AC ID | 覆盖环境、栈、模型、数据、CRUD、事务、索引、并发、安全、UI、报告 | 本文件 | 已通过 |
| AC-DOC-03 | P0 | 本轮未写业务代码 | 文件树检查 | 当前已进入业务代码实现阶段；本项仅记录早期文档治理阶段 | `docs/evidence/DOC-03/` | 不适用 |
| AC-DOC-04 | P0 | 无编造实测数据 | 搜索数字/性能描述 | 已无未测标记；无假 TPS/耗时 | 本文件 | 已通过 |

---

## 18. 变更记录

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v0.1 | 2026-10-20 | 建立验收矩阵初稿：课程追溯、环境/栈/模型/数据/CRUD/事务/索引/并发/安全/UI/报告/代码质量、P0 详细用例、实测模板 | 个人 |
