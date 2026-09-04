# ch10 性能优化：索引与 EXPLAIN 🚀

> 本章目标：用 `EXPLAIN` 看懂一条查询是「全表扫」还是「走索引」，并知道为什么索引会失效、怎么救。
> 学完你能自己判断「这条 SQL 会不会慢」，而不用等它真跑几分钟。

---

## 一、本章学习目标

1. 理解索引为什么能加速（B+ 树，像书本目录）
2. 用 `EXPLAIN` 看执行计划，重点盯 `type` / `key` / `rows`
3. 识别三种最常见的**索引失效**：对列套函数、最左前缀跳过、前导通配符
4. 会建/删索引：`CREATE INDEX` / `DROP INDEX`
5. 锁定本库实测：PK 查 `const`(1 行) / 无索引 `ALL`(3529 行) / 函数破坏索引变 `ALL`

---

## 二、为什么要学执行计划

前 9 章只关心「对不对」，不关心「快不快」——因为本库才 1.5 万行，怎么写都秒回。但真实业务表**千万行起步**，一条烂 SQL 能跑几分钟，拖垮整个报表刷新。

你没法靠「感觉」判断快慢，要靠**执行计划**——MySQL 用 `EXPLAIN` 告诉你：它打算怎么找数据、扫多少行、走没走索引。这是 SQL 优化员的望远镜。

---

## 三、概念：索引与 EXPLAIN 怎么读

### 3.1 索引是什么

索引 ≈ 书本的目录。没有目录，找「广东」要翻完整本书（**全表扫描**）；有目录，直接跳到对应页。

MySQL 默认索引结构是 **B+ 树**：查询时从树根二分下钻，几次 IO 就定位到目标行，不用扫全表。

#### 🔍 原理深挖 1：B+ 树长什么样（为什么查找 O(log n)）

```
B+ 树 = 多路平衡搜索树，所有数据只存在"叶子层"，非叶子只放"路标":

                     [ 50 | 100 ]              ← 非叶子: 路标(索引键)
                    /      |       \
        [ 10 | 25 | 40 ] [ 60 | 80 ] [ 120 | 150 ]   ← 非叶子
         /    |    |  \    ...
  叶子(真正存数据, 且用链表串起来):
   [1..10] ⇄ [11..25] ⇄ [26..40] ⇄ ... ⇄ [120..150]
     ↑ 叶子之间有序链表 → 范围查询(>50)只要顺着链表走, 不用回头

为什么"矮胖"多路(一个节点存几百个键)而不是二叉树?
  磁盘一次 IO 读一页(16KB), 节点越大一次 IO 覆盖越多键
  → 树高只有 3~4 层, 查 1000 万行也只要 3~4 次磁盘 IO

查找 process:
  WHERE order_id = 100 → 根(50,100)→ 走右/中...→ 叶子定位 → 3次IO 找到
  vs 全表扫描 = 把 3529 行一页页读完 → 几十次IO → type=ALL 慢的原因

叶子链表的威力(范围查询):
  WHERE order_date BETWEEN '2024-01-01' AND '2024-01-31'
  → 找到起点叶子后顺链表扫 → 不需要回树根重新找 (这就是 type=range)
```

#### 🔍 原理深挖 2：聚簇索引 & 回表（为什么"少取列"会快）

```
InnoDB 表 = 一棵"以主键为序"的 B+ 树, 叶子直接存整行数据 → 聚簇索引
  PRIMARY KEY 索引 → 叶子 = 整行 → 按主键查, 一次到位(type=const)

二级索引(普通 KEY idx_cust) → 叶子只存"索引列 + 主键"
  WHERE customer_id=10 走 idx_cust:
    ① 在 idx_cust 树找到主键(order_id)    ← 索引树
    ② 拿主键回聚簇树"回表"取整行           ← 第2次查找!
  若 SELECT 只要 customer_id,order_id → 不用回表 → 覆盖索引, 更快

图形:
  idx_cust 树                    聚簇树(主键)
  [cust,order_id]               [order_id,整行]
      │ 找到order_id=88              │ 按88找
      └─────────── 回表 ────────────▶┘ 取整行

为什么 SELECT * 比 SELECT 索引列 慢?
  * 要整行 → 几乎总要回表; 只查索引里有的列 → 覆盖索引免回表
  这就是"别无脑 SELECT *"的性能原因之一
```

> 回到 3.1 的比喻：**目录（索引）帮你找到页码（主键），翻到那页才是内容（回表取行）**。索引设计三原则先记住：① 主键必建（自动）② 高频 WHERE/JOIN/ORDER BY 的列建索引 ③ 别对索引列套函数（5.1 会证明为什么失效）。

### 3.2 EXPLAIN 重点看三列

```sql
EXPLAIN SELECT * FROM fact_order WHERE order_id = 100;
```

| 列 | 含义 | 你要盯什么 |
|---|---|---|
| `type` | 访问类型（性能从好到差） | `const` > `ref` > `range` > `ALL`；**`ALL` = 全表扫描，最差** |
| `key` | 实际用了哪个索引 | `NULL` = 没走索引（危险） |
| `rows` | 预估扫描行数 | 越小越好；`ALL` 时 ≈ 全表行数 |

> `type` 速记：**`const`（主键/唯一，1 行）> `ref`（普通索引，几行）> `range`（范围，一段）> `ALL`（全表，全扫）**。

---

## 四、实操：对比执行计划（本库实测）

### 4.1 主键查询——走索引，最优

```sql
EXPLAIN SELECT * FROM fact_order WHERE order_id = 100;
```

**预期**：`type=const`，`key=PRIMARY`，`rows=1`。主键定位，只扫 1 行。

### 4.2 普通索引列——走索引

```sql
EXPLAIN SELECT * FROM fact_order WHERE customer_id = 10;
-- 预期：type=ref, key=idx_cust, rows=6（该客户约 6 单）

EXPLAIN SELECT * FROM fact_order WHERE order_date = '2024-06-15';
-- 预期：type=ref, key=idx_date, rows=8（当天约 8 单）
```

### 4.3 无索引列——全表扫描

```sql
EXPLAIN SELECT * FROM fact_order WHERE status = '已完成';
```

**预期**：`type=ALL`，`key=NULL`，`rows=3529`。`status` 没建索引，只能扫全表 3,529 行。（小表无所谓，千万行表就崩了。）

### 4.4 加索引前后对比

```sql
CREATE INDEX idx_pay ON fact_order(payment_method);   -- 练手，用完删
EXPLAIN SELECT * FROM fact_order WHERE payment_method = '微信';
-- 预期：type=ref, key=idx_pay, rows=1140（之前是 ALL 3529）
DROP INDEX idx_pay ON fact_order;                     -- 收尾，删掉练手索引
```

**加索引后从 `ALL`(3529) 降到 `ref`(1140)**——这就是索引的价值。

---

## 五、★ 三种索引失效（必考）

### 5.1 对索引列套函数 → 失效

```sql
EXPLAIN SELECT * FROM fact_order WHERE YEAR(order_date) = 2024;
```

**预期**：`type=ALL`，`possible_keys=idx_date` 但 `key=NULL`，`rows=3529`。

**为什么？** 你对 `order_date` 套了 `YEAR()`，MySQL 得先对**每一行**算函数才能比较，索引的「有序性」被破坏了 → 只能全表扫。`possible_keys` 显示「其实有 idx_date 能用」，但 `key=NULL` 说明**没用上**。

✅ 改法：用范围代替函数，让索引可见：

```sql
EXPLAIN SELECT * FROM fact_order
WHERE order_date BETWEEN '2024-01-01' AND '2024-12-31';
-- 预期：type=ref, key=idx_date（索引生效，rows 大幅下降）
```

### 5.2 最左前缀原则——跳过左列 → 失效

复合索引 `(region_id, status)` 要先看 `region_id` 再看 `status`。

```sql
CREATE INDEX idx_region_status ON fact_order(region_id, status);

EXPLAIN SELECT * FROM fact_order WHERE region_id = 1 AND status = '已完成';
-- 预期：type=ref, key=idx_region_status, rows=352（两列都给，生效）

EXPLAIN SELECT * FROM fact_order WHERE status = '已完成';
-- 预期：type=ALL, key=NULL（只给右列 status，跳过最左 region_id → 失效）

DROP INDEX idx_region_status ON fact_order;   -- 收尾
```

**最左前缀**：复合索引 `(A,B,C)` 只能按 `A` / `(A,B)` / `(A,B,C)` 用，**不能跳过 A 直接用 B 或 C**。就像查电话簿先按「姓」再按「名」，只记得名就找不到目录。

### 5.3 前导通配符 → 失效

```sql
EXPLAIN SELECT * FROM dim_product WHERE product_name LIKE '%面膜%';
-- 预期：type=ALL（'%面膜%' 开头是通配符，索引用不上）
-- 若改成 '鲜踪%'（后缀通配符），且 product_name 有索引，则能走 range
```

`'%x%'` 或 `'%x'` 开头模糊，索引无法定位起点 → 全表扫。业务上尽量用 `'x%'` 后缀匹配。

---

## 六、FDE 现场场景：报表刷新突然变慢

客户：「这个报表以前 2 秒，现在 2 分钟。」

你 `EXPLAIN` 一查：`type=ALL`，`key=NULL`。原因八成是：

- 开发改了查询，给索引列套了函数（`DATE(order_date)`）
- 或新加的筛选条件没建索引
- 或 `LIKE '%关键词%'`

加个索引 / 改回范围查询，2 分钟变 2 秒。**优化 = 让 `type` 从 `ALL` 变 `ref/range`，让 `rows` 从全表变几十**。

---

## 七、本章小结

| 你学到了 | 关键点 |
|---|---|
| 索引 | B+ 树，像目录；`CREATE INDEX` / `DROP INDEX` |
| EXPLAIN 三列 | `type`(const>ref>range>ALL) / `key`(NULL=没走) / `rows`(越小越好) |
| 实测 | PK `const`(1) / 无索引 `ALL`(3529) / 加索引 `ref`(1140) |
| ★ 失效1 | 对索引列套函数 `YEAR()` → `ALL`（用范围代替） |
| ★ 失效2 | 复合索引跳过最左列 → `ALL`（最左前缀） |
| ★ 失效3 | `LIKE '%x%'` 前导通配 → `ALL`（用 `'x%'`） |

---

## 八、练习题

### 练习 1：主键查询（考：最优访问）

**题目**：`EXPLAIN SELECT * FROM fact_order WHERE order_id = 100;`

**预期结果**：`type=const`，`key=PRIMARY`，`rows=1`。

**解析**：主键定位，只扫 1 行，性能天花板。

---

### 练习 2：无索引全扫（考：最差访问）

**题目**：`EXPLAIN SELECT * FROM fact_order WHERE status='已完成';`

**预期结果**：`type=ALL`，`key=NULL`，`rows=3529`。

**解析**：`status` 无索引 → 全表扫。小表无感，大表致命。

---

### 练习 3：函数破坏索引（考：失效1）

**题目**：`EXPLAIN ... WHERE YEAR(order_date)=2024;` 看 `key` 是什么？

**预期结果**：`type=ALL`，`possible_keys=idx_date` 但 **`key=NULL`**（失效）。

**解析**：`YEAR()` 破坏索引有序性。改 `order_date BETWEEN '2024-01-01' AND '2024-12-31'` 即可走索引。

---

### 练习 4：最左前缀（考：失效2）

**题目**：建复合索引 `(region_id, status)`，分别查「两列都给」和「只给 status」。

**预期结果**：两列都给 → `type=ref, key=idx_region_status`；只给 status → `type=ALL`（跳过最左列）。

**解析**：复合索引必须从左列开始用，不能跳。

---

### 练习 5：建索引前后（考：救慢查询）

**题目**：给 `payment_method` 建索引，再 EXPLAIN `WHERE payment_method='微信'`。

**预期结果**：建前 `ALL`(3529) → 建后 `type=ref, key=idx_pay, rows=1140`。

**解析**：加索引把全表扫降为索引查找。练完记得 `DROP INDEX` 清理。

---

## 下一步

索引让你「查得快」，但很多重复逻辑（月报、审计）值得**封装成数据库对象**复用。下一章讲**存储过程与触发器**——把月报逻辑存进库里，并用触发器自动留审计痕迹。

→ [ch11 企业级：存储过程与触发器](./ch11_企业级_存储过程与触发器.md)
