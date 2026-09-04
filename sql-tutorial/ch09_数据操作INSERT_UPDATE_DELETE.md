# ch09 数据操作 INSERT / UPDATE / DELETE ✏️

> 本章目标：安全地插入、更新、删除数据，并用**事务**把每次改动变成「可反悔」的操作。
> 学完你敢改库，也知道怎么不把生产库改崩。

---

## 一、本章学习目标

1. 写出 `INSERT` / `UPDATE` / `DELETE` 的标准语法
2. 牢记铁律：**UPDATE / DELETE 不写 WHERE = 全表改写**（灾难）
3. 理解**外键约束**会阻止「删掉还有子记录的主表行」
4. 用 `BEGIN` / `COMMIT` / `ROLLBACK` 把改动包成事务，出错能撤销
5. 养成「先 SELECT 确认，再改，再核对」的改数三板斧

---

## 二、为什么要单独、谨慎地学 DML

前 8 章都是 `SELECT`——**只读，永远不会破坏数据**。而 `INSERT/UPDATE/DELETE` 会**永久改写库**：

- 漏写 `WHERE` → 把 500 个客户的状态全改成「退款」
- 误删一张主表行 → 外键约束报错，或（没约束时）留下孤儿明细
- 改错一个金额 → 财务报表全错

真实交付里，**改数权限往往比查数权限更敏感**。FDE 现场改库前，通常要客户邮件确认、要在测试库先跑、要能回滚。本章教的就是这套「安全带」。

> ⚠️ **本教程的演示库是固定种子（可复现）**：任何持久改动都会破坏「数字对得上」的前提。所以本章**所有演示都包在事务里，跑完 `ROLLBACK`**，绝不在你的库留痕。你照做也一样。

---

## 三、概念：事务 ACID 与三命令

**事务**（Transaction）= 一组要么全做、要么全不做的 SQL。

| 命令 | 作用 |
|---|---|
| `BEGIN`（或 `START TRANSACTION`） | 开启事务 |
| `COMMIT` | 确认改动，落盘 |
| `ROLLBACK` | 撤销自 BEGIN 以来的所有改动 |

我们这章用「BEGIN → 改 → 看 → ROLLBACK」的**沙盘模式**练手，确认无误才把 ROLLBACK 换成 COMMIT。

### 🔍 原理深挖：UPDATE/DELETE 是怎么"安全回滚"的？（undo log）

为什么 `ROLLBACK` 能让改过的数据回到原样？靠的是 InnoDB 的 **undo log（回滚日志）**——每次修改前先记下"旧值"：

```
UPDATE dim_customer SET tier='钻石' WHERE customer_id=1;
  ① 先把旧值('普通')写进 undo log     ← 内存/日志
  ② 再改数据页: 1 的 tier → '钻石'
  ③ COMMIT → undo log 标记可清理(不再需要回滚)
  如果中途 ROLLBACK → 拿 undo log 里的旧值把 1 改回 '普通' ✅

图形:
   事务开始 ──▶ 记undo(旧值) ──▶ 改数据页 ──▶ COMMIT(丢弃undo)
                         │
                         └─ ROLLBACK时: 用undo旧值覆盖回来 ──▶ 还原

INSERT 的 undo = 记"这行要删"; DELETE 的 undo = 记"这行原样"(可恢复)
```

> 这就是为什么 DML 后立刻 `SELECT` 能看到新值、`ROLLBACK` 又能还原——ch12 的 MVCC 快照读、事务回滚全靠这份 undo log。**别在生产裸跑不带 WHERE 的 UPDATE/DELETE**——就算有 undo，回滚也要时间，而事故现场往往等不起。

---

## 四、实操：三类 DML + 安全演示

### 4.1 INSERT（插入一行）

```sql
BEGIN;   -- 开事务（练手用，真实插入确认后再 COMMIT）

INSERT INTO dim_customer
  (customer_id, customer_name, gender, city, region_id, register_date, tier)
VALUES
  (99999, '测试员', '男', '测试市', 1, '2026-01-01', '普通');

SELECT COUNT(*) FROM dim_customer;   -- 预期：501（原 500 + 1）
ROLLBACK;                            -- 撤销，库回到 500
SELECT COUNT(*) FROM dim_customer;   -- 预期：500（已恢复）
```

**验证结果**：插入后 501，回滚后 **500**——库毫发无损。

> 本库 `customer_id` 插入时需显式给一个未占用的值（如 99999）；若你的表主键设为自增，则可省略该列让数据库自动分配。

### 4.2 UPDATE（更新，必须带 WHERE）

```sql
BEGIN;
UPDATE fact_order
SET status = '退款'
WHERE order_id = 1;          -- ★ 必须带 WHERE，只改 1 单
SELECT status FROM fact_order WHERE order_id = 1;   -- 预期：退款
ROLLBACK;                     -- 撤销
```

**灾难对照（千万别这么写）**：

```sql
UPDATE fact_order SET status = '退款';   -- ❌ 没有 WHERE → 3529 单全变「退款」！
```

**没有 WHERE 的 UPDATE 会改写全表 3,529 行**。务必先 `SELECT` 确认影响范围，再决定 `COMMIT` 还是 `ROLLBACK`。

### 4.3 DELETE（删除，必须带 WHERE + 当心外键）

```sql
BEGIN;
DELETE FROM fact_order WHERE order_id = 9999;   -- 假设这单不存在 → 影响 0 行，安全
ROLLBACK;
```

**外键约束保护**：想删一个「还有订单的客户」会被数据库拒绝：

```sql
DELETE FROM dim_customer WHERE customer_id = 1;
-- 预期报错：(1451, "Cannot delete or update a parent row: a foreign key constraint fails")
```

**为什么？** `fact_order.customer_id` 是引用 `dim_customer.customer_id` 的外键。MySQL 不允许删掉「被子表引用的父行」，否则会留下孤儿订单。要删得先删该客户的所有订单（或设级联删除，但生产环境慎用）。

---

## 五、验证：事务真的能反悔

把 4.1 的沙盘跑一遍，确认「改了能撤」：

```sql
SELECT COUNT(*) FROM dim_customer;          -- 500
BEGIN;
INSERT INTO dim_customer (customer_id, customer_name, gender, city, region_id, register_date, tier)
VALUES (99999, '测试员','男','测试市',1,'2026-01-01','普通');
SELECT COUNT(*) FROM dim_customer;          -- 501
ROLLBACK;
SELECT COUNT(*) FROM dim_customer;          -- 500（恢复）
```

**结论**：只要改动在 `BEGIN` 之后、`COMMIT` 之前，一句 `ROLLBACK` 就能让库回到改动前。这是你改生产库时最后的安全网。

---

## 六、FDE 现场场景：客户让你「把这批订单状态改一下」

正确流程（改数三板斧）：

1. **先 SELECT**：`SELECT COUNT(*) FROM fact_order WHERE <条件>;` 看清影响几行
2. **开事务改**：`BEGIN;` → `UPDATE ... WHERE <条件>;` → 再 SELECT 核对结果
3. **确认或撤销**：对了 `COMMIT`，错了 `ROLLBACK`
4. **留痕**：把 SQL 和客户确认邮件存档（ch11 触发器能自动留审计）

> **核心心法**：永远假设「我可能会改错」。所以改动前必开事务，改动后必核对，没把握必 ROLLBACK。数据库不替你后悔，事务替你兜底。

---

## 七、本章小结

| 你学到了 | 关键点 |
|---|---|
| INSERT | 显式给值（含 PK），包事务练手 |
| ★ UPDATE 铁律 | **必须带 WHERE**，否则改写全表 3529 行 |
| ★ DELETE 铁律 | 必须带 WHERE；外键会阻止删有子记录的主行（报错 1451） |
| 事务 | `BEGIN` → 改 → `COMMIT` / `ROLLBACK`（反悔） |
| 沙盘验证 | 插入 500→501→`ROLLBACK`→500，库不变 |
| 改数三板斧 | 先 SELECT 确认 → 事务改 → 核对再 COMMIT |

---

## 八、练习题

### 练习 1：安全插入（考：事务 + 显式 PK）

**题目**：在事务里插入一个测试客户，确认行数变化后回滚。

**预期结果**：`BEGIN` 后 `COUNT` = 501，回滚后 = **500**。

**解析**：见第四节 / 第五节。所有练手改动都包事务，绝不持久化。

---

### 练习 2：UPDATE 必须有 WHERE（考：灾难意识）

**题目**：`UPDATE fact_order SET status='退款';`（无 WHERE）会影响多少行？

**预期结果**：**3,529 行**全变退款——灾难。必须加 `WHERE order_id=...`。

**解析**：无 WHERE 的 UPDATE/DELETE 作用于全表。写之前先 `SELECT` 看影响范围。

---

### 练习 3：外键拦截删除（考：约束）

**题目**：`DELETE FROM dim_customer WHERE customer_id=1;`

**预期结果**：**报错 1451**（外键约束失败，该客户有订单）。

**解析**：外键保护引用完整性。删主表行前需先处理子表（或级联删除）。

---

### 练习 4：事务回滚（考：反悔机制）

**题目**：BEGIN 后改一行，不 COMMIT 直接 ROLLBACK，库变了吗？

**预期结果**：**不变**（改动被撤销）。

**解析**：ROLLBACK 回到 BEGIN 时的状态，是改生产库的最后安全网。

---

### 练习 5：改数安全清单（考：流程，概念题）

**题目**：客户让你批量改订单状态，写出你的标准操作步骤。

**预期步骤**：①`SELECT` 确认影响行数 → ②`BEGIN` 开事务 → ③执行 UPDATE（带 WHERE）→ ④再 SELECT 核对 → ⑤对了 `COMMIT`、错了 `ROLLBACK` → ⑥SQL 与确认邮件存档。

**解析**：这就是「改数三板斧」+ 留痕。宁可慢一步，不可改崩库。

---

## 下一步

改数据你会安全做了。但「查得慢」是另一类问题——本库虽小，真实业务表动辄千万行，一条烂 SQL 能跑几分钟。下一章讲**索引与 EXPLAIN**，让你看懂查询为什么慢、怎么救。

→ [ch10 性能优化：索引与 EXPLAIN](./ch10_性能优化索引与EXPLAIN.md)
