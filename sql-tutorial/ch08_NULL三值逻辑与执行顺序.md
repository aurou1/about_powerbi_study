# ch08 NULL、三值逻辑与执行顺序 🚧

> 本章目标：搞懂 SQL 里最阴险的两个坑——`NULL` 让 `NOT IN` 整段返回 0 行，以及「为什么 WHERE 里不能用 SELECT 起的别名」。
> 学完你能避开 90% 的「查询明明没报错，结果却少了一半」的事故。

---

## 一、本章学习目标

1. 理解 SQL 的**三值逻辑**：TRUE / FALSE / UNKNOWN
2. 记住铁律：**任何和 NULL 的比较结果都是 UNKNOWN**，不是 TRUE 也不是 FALSE
3. 躲开 `NOT IN (子查询)` 含 NULL 返回 0 行的坑
4. 分清 `COUNT(*)` 和 `COUNT(列)` 对 NULL 的不同态度
5. 背下 **SQL 执行顺序**，明白为什么 `WHERE` 用不了 `SELECT` 别名

---

## 二、为什么要单独学 NULL 和执行顺序

前两章你写的查询如果「少了几行」，往往不是 JOIN 错了，而是：

- 子查询里混进一个 NULL，`NOT IN` 直接**整段返回 0 行**（你以为是逻辑问题，其实是 NULL）
- 想 `WHERE 毛利率 > 30` 但 `毛利率` 是 SELECT 里起的别名 → **报错**（因为执行顺序里 WHERE 先于 SELECT）

这两个坑都不报错，只让你「安静地得到错误答案」。FDE 现场最怕的就是这种——客户拿你的数字去决策，三天后才发现是 NULL 吞了数据。

---

## 三、概念：三值逻辑

普通编程是二值（真/假）。SQL 多一个 **UNKNOWN**：

| 表达式 | 结果 |
|---|---|
| `1 > 0` | TRUE |
| `1 > 2` | FALSE |
| `1 > NULL` | **UNKNOWN** |
| `NULL = NULL` | **UNKNOWN**（不是 TRUE！） |
| `NULL IS NULL` | TRUE |

**关键规则**：

- `WHERE` 只保留**结果为 TRUE** 的行；UNKNOWN 和 FALSE 一样——**被排除**
- 所以 `WHERE col = NULL` 永远取不到任何行（因为 `col = NULL` 是 UNKNOWN），正确写法是 `WHERE col IS NULL`

### 🔍 原理深挖：三值逻辑的真值表（AND/OR/NOT）

一个 NULL 掺进布尔运算，结果常常"出乎直觉"——背下这张表就不会被坑：

```
AND 真值表        TRUE   FALSE  UNKNOWN
        TRUE      TRUE   FALSE  UNKNOWN
        FALSE     FALSE  FALSE  FALSE
        UNKNOWN   UNKNOWN FALSE  UNKNOWN

OR 真值表         TRUE   FALSE  UNKNOWN
        TRUE      TRUE   TRUE   TRUE
        FALSE     TRUE   FALSE  UNKNOWN
        UNKNOWN   TRUE   UNKNOWN UNKNOWN

NOT:  NOT TRUE = FALSE | NOT FALSE = TRUE | NOT UNKNOWN = UNKNOWN

直觉解释:
  UNKNOWN AND FALSE = FALSE   → 一边确定是假, 整个就是假
  UNKNOWN OR  TRUE  = TRUE    → 一边确定是真, 整个就是真
  UNKNOWN AND TRUE  = UNKNOWN → 结果取决于那个"不知道", 仍是不知道
```
> 所以 `WHERE x > 5 OR x <= 5` 按理覆盖所有情况——**但当 x 是 NULL 时两条都 UNKNOWN，行还是被排除**！这就是为什么"补集查询"（NOT IN / NOT EXISTS）最容易漏 NULL 行（4.1 的 0 行事故）。**给列加 `NOT NULL` 约束（ch13）能从根上消灭一大半这种 bug。**

### 3.1 验证三值逻辑

```sql
SELECT 1 WHERE 1 > NULL;        -- 预期：返回 0 行（UNKNOWN 被排除）
SELECT 1 WHERE NULL = NULL;     -- 预期：返回 0 行（UNKNOWN）
SELECT 1 WHERE NULL IS NULL;    -- 预期：返回 1 行（TRUE）
```

---

## 四、★ 实战：NOT IN 含 NULL 的致命坑

这是全教程**最经典的 NULL 事故**。

### 4.1 真实反例：子查询藏 NULL

```sql
-- 想找「没下过已完成订单」的客户
SELECT customer_id FROM dim_customer
WHERE customer_id NOT IN (
  SELECT customer_id FROM fact_order WHERE status = '已完成'
);
-- 预期：2（有 2 个客户从没成交，ch04/05 见过）
```

上面这条**没问题**，因为 `fact_order.customer_id` 没有 NULL。但一旦子查询的来源列**可能含 NULL**（比如一张 optional 外键表），灾难来了：

```sql
-- 故意在列表里塞一个 NULL，模拟真实子查询漏进 NULL 的情况
SELECT COUNT(*) FROM dim_region
WHERE region_id NOT IN (1, 2, NULL);
-- 预期：0 行！！！
```

**为什么是 0 行？** `region_id NOT IN (1,2,NULL)` 对每一行等价于：
`region_id <> 1 AND region_id <> 2 AND region_id <> NULL`
而 `region_id <> NULL` 的结果是 **UNKNOWN**，于是整个 `AND` 链变成 UNKNOWN → 每行都被排除 → **0 行**。

> 🚨 **保命规则**：写 `NOT IN (子查询)` 前，先确认子查询的列**不可能为 NULL**；不确定就用 `NOT EXISTS`（它不怕 NULL）：
> ```sql
> SELECT c.customer_id FROM dim_customer c
> WHERE NOT EXISTS (SELECT 1 FROM fact_order o WHERE o.customer_id = c.customer_id AND o.status='已完成');
> -- 预期：2（和 NOT IN 正确版一致，且永不因 NULL 翻车）
> ```

### 4.2 正确找「无订单客户」

```sql
-- 写法 A：LEFT JOIN + IS NULL（推荐，语义清晰）
SELECT c.customer_name, c.tier
FROM dim_customer c
LEFT JOIN fact_order o ON c.customer_id = o.customer_id AND o.status = '已完成'
WHERE o.order_id IS NULL;
-- 预期：2 个客户

-- 写法 B：NOT EXISTS（也推荐）
SELECT c.customer_name
FROM dim_customer c
WHERE NOT EXISTS (SELECT 1 FROM fact_order o WHERE o.customer_id = c.customer_id AND o.status='已完成');
-- 预期：2 个客户
```

---

## 五、概念：COUNT(*) vs COUNT(列)

```sql
SELECT COUNT(*) AS a, COUNT(order_profit) AS b FROM fact_order;
-- 预期：a = 3529, b = 3529
```

本库 `fact_order` 所有列都 `NOT NULL`，所以两者相等。但原理不同：

- `COUNT(*)` 数**行数**，含 NULL 行
- `COUNT(列)` 数**该列非 NULL 的行数**，自动忽略 NULL

**真实业务里**，若某列有 NULL（如「退货原因」可能为空），`COUNT(退货原因)` 会**少于** `COUNT(*)`，不小心用错会少算。这也是为什么「平均值」要警惕：`AVG(列)` 忽略 NULL，可能和你以为的「总行数分母」不一致。

---

## 六、概念：SQL 执行顺序（必须背）

你写的顺序是 `SELECT → FROM → WHERE → GROUP BY → HAVING → ORDER BY`，但**数据库实际执行顺序**是：

```
1. FROM        -- 先确定从哪些表取数
2. JOIN        -- 连表
3. WHERE       -- 过滤行（分组前）
4. GROUP BY    -- 分组
5. HAVING      -- 过滤组（分组后）
6. SELECT      -- 选列、算表达式、起别名  ← 别名在这才生成
7. ORDER BY    -- 排序（能用 SELECT 别名）
8. LIMIT       -- 截取
```

**配图理解（一条 SQL 的"流水线"，行数一路变少）：**

```
SELECT category, COUNT(*) AS 商品数 FROM dim_product
WHERE brand <> '鲜踪' GROUP BY category HAVING COUNT(*) >= 5 ORDER BY 商品数 DESC LIMIT 3;

① FROM dim_product          200 行(全部商品)
      │
② WHERE brand <> '鲜踪'     过滤 → 假设剩 190 行  ← 行级过滤先做, 少算后面
      │
③ GROUP BY category         分组 → 5 组(数码/食品/家居/服饰/美妆)
      │
④ HAVING COUNT(*)>=5        组级过滤 → 留下 ≥5 的组
      │
⑤ SELECT 聚合+起别名        算 COUNT(*) 生成"商品数"列
      │
⑥ ORDER BY 商品数 DESC      按别名排序
      │
⑦ LIMIT 3                  只取前3行 → 输出
```

**两条由此而来的铁律**：

1. **`WHERE` 里不能用 `SELECT` 起的别名**——因为 WHERE（第 3 步）跑在 SELECT（第 6 步）之前，别名还没出生。
   ```sql
   SELECT ROUND(SUM(line_amount),2) AS 销售额
   FROM fact_order_item
   WHERE 销售额 > 1000000;     -- ❌ 报错：Unknown column '销售额'
   -- 改成：WHERE SUM(line_amount) > 1000000 也不行（WHERE 在聚合前）→ 用 HAVING
   ```
2. **`ORDER BY` 能用别名**，也能用窗口函数结果（窗口函数在 SELECT 阶段算完）。

3. **窗口函数在 WHERE/GROUP 之后、SELECT 之前算**（ch06 深挖）——所以想按 `ROW_NUMBER` 结果过滤必须包一层子查询。

---

## 七、FDE 现场场景：报表数字「少了一半」

客户：「我系统里这指标有 500 个客户，你报表才 498。」

你查发现：子查询用了 `NOT IN`，而来源表有个 NULL 把整段吞了 → 实际是「找反了」。改成 `NOT EXISTS` 后恢复 498（那 2 个本就是 0 单客户）。**NULL 不会报错，只会安静地删数据**——这就是为什么 FDE 写 `NOT IN` 前必查 NULL。

---

## 八、本章小结

| 你学到了 | 关键点 |
|---|---|
| 三值逻辑 | TRUE / FALSE / UNKNOWN；UNKNOWN 被 WHERE 排除 |
| NULL 比较 | `col = NULL` 是 UNKNOWN → 用 `col IS NULL` |
| ★ NOT IN 坑 | 子查询含 NULL → 整段 0 行；改用 `NOT EXISTS` |
| 无订单客户 | 2 人（LEFT JOIN IS NULL / NOT EXISTS） |
| COUNT | `COUNT(*)` 数行；`COUNT(列)` 忽略 NULL |
| 执行顺序 | FROM→JOIN→WHERE→GROUP BY→HAVING→SELECT→ORDER BY→LIMIT；WHERE 不能用 SELECT 别名 |

---

## 八、练习题（编号续）

### 练习 1：NOT IN 含 NULL 翻车（考：致命坑）

**题目**：执行 `SELECT COUNT(*) FROM dim_region WHERE region_id NOT IN (1,2,NULL);`

**预期结果**：**0 行**。

**解析**：列表里的 NULL 让每行比较变 UNKNOWN，全被排除。真实子查询若来源列可能为 NULL，同样翻车。

---

### 练习 2：找无成交客户（考：LEFT JOIN IS NULL）

**题目**：用 LEFT JOIN 找从没下过已完成订单的客户。

**预期结果**：**2 人**。

**解析**：`LEFT JOIN ... AND status='已完成'` + `WHERE o.order_id IS NULL` 捞出 0 单客户。

---

### 练习 3：三值逻辑（考：NULL 比较）

**题目**：分别执行 `WHERE 1>NULL`、`WHERE NULL=NULL`、`WHERE NULL IS NULL`，各返回几行？

**预期结果**：前两个 **0 行**（UNKNOWN），第三个 **1 行**（TRUE）。

**解析**：见第三节。记住 `NULL = NULL` 不是真，要用 `IS NULL`。

---

### 练习 4：COUNT 的 NULL 态度（考：聚合细节）

**题目**：`SELECT COUNT(*), COUNT(order_profit) FROM fact_order;` 结果？

**预期结果**：**3529 / 3529**（本库该列无 NULL，故相等）。

**解析**：`COUNT(*)` 数行；`COUNT(列)` 忽略 NULL。真实表若有 NULL 列，两者会不等——平均值同理要警惕。

---

### 练习 5：WHERE 不能用别名（考：执行顺序）

**题目**：为什么 `SELECT ROUND(SUM(line_amount),2) AS 销售额 ... WHERE 销售额>1000000` 报错？

**预期结果**：报 `Unknown column '销售额'`。

**解析**：执行顺序里 WHERE（第 3 步）早于 SELECT（第 6 步），别名尚未生成。过滤聚合结果要用 `HAVING`（第 5 步，在聚合后）。

---

## 下一步

NULL 和执行顺序都懂了，但「改数据」还没碰——插入、更新、删除。它们威力大、风险也大，下一章讲怎么**安全地**用事务保护每一次改动。

→ [ch09 数据操作 INSERT/UPDATE/DELETE](./ch09_数据操作INSERT_UPDATE_DELETE.md)
