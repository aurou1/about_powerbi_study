# ch05 子查询与 CTE 🧩

> 本章目标：把「比平均客单价高的订单」「每个省卖得最好的客户」这类嵌套逻辑，拆成一步步的子查询或 CTE，写出既对又易懂的 SQL。
> 学完你能告别「一堆 JOIN 揉成一团」的噩梦。

---

## 一、本章学习目标

1. 区分**子查询**的三种位置：SELECT 里（标量）/ WHERE 里（列或行）/ FROM 里（派生表）
2. 用 `IN` 子查询、`EXISTS` 子查询处理「集合包含」问题
3. 用**关联子查询**让内层查询引用外层行（逐行比对）
4. 用 `WITH ... AS`（CTE）把中间结果命名，提升可读性
5. 锁定：平均客单价 3,041.21 / 高于平均的订单 909 单 / 有成交客户 498 人

---

## 二、为什么要学子查询和 CTE

ch04 的多表 JOIN 解决「跨表取数」，但有些问题本质是**嵌套的**：

- 「比**平均客单价**高的订单」——平均客单价本身要先用一条 SQL 算出来
- 「有**已完成订单**的客户」——要判断「存在性」
- 「每个客户的消费额**排名**」——要先把客户汇总，再排序

这些「查询结果里套查询结果」的需求，靠 JOIN 硬写会很绕。子查询和 CTE 就是干这个的。

---

## 三、概念：子查询长在哪

| 位置 | 返回什么 | 例子 |
|---|---|---|
| `SELECT` 里 | 单行单列（标量） | `SELECT (SELECT AVG(...) FROM ...) AS 全局平均` |
| `WHERE` 里（IN） | 单列多行（集合） | `WHERE customer_id IN (SELECT ...)` |
| `WHERE` 里（EXISTS） | 布尔（存在否） | `WHERE EXISTS (SELECT 1 FROM ...)` |
| `FROM` 里 | 一张表（派生表） | `FROM (SELECT ... ) t` |

> CTE（`WITH x AS (...) SELECT ... FROM x`）本质也是「FROM 里的派生表」，但**先命名、后引用**，可读性远好于嵌套 `(SELECT ...)`。

---

## 四、实操：四类子查询 + CTE

### 4.1 标量子查询（SELECT 里，单行单列）

```sql
SELECT ROUND(AVG(order_amount),2) AS 全局平均客单价
FROM fact_order WHERE status = '已完成';
-- 预期：3041.21

-- 把它嵌进查询，找出高于平均的订单
SELECT order_id, order_amount
FROM fact_order
WHERE status = '已完成'
  AND order_amount > (SELECT AVG(order_amount) FROM fact_order WHERE status='已完成')
ORDER BY order_amount DESC
LIMIT 5;
```

**预期**：返回高于 3,041.21 的订单（共 **909 单**中金额最高的 5 行）。

### 4.2 列子查询 + `IN`

```sql
-- 钻石会员的有效订单有哪些？
SELECT order_id, order_amount
FROM fact_order
WHERE status = '已完成'
  AND customer_id IN (SELECT customer_id FROM dim_customer WHERE tier = '钻石')
ORDER BY order_amount DESC
LIMIT 5;
```

**预期**：钻石客户的有效订单（共 **466 单**），降序前 5。

### 4.3 `EXISTS`：判断存在性

```sql
-- 哪些客户下过已完成订单？（有=保留）
SELECT COUNT(*) AS 有成交客户数
FROM dim_customer c
WHERE EXISTS (
  SELECT 1 FROM fact_order o
  WHERE o.customer_id = c.customer_id AND o.status = '已完成'
);
-- 预期：498
```

> `EXISTS` 比 `IN` 更适合「存在性」判断：它一旦找到一行就返回真，**不关心返回几列**（所以写 `SELECT 1`），大表上常比 `IN` 快。

### 4.4 关联子查询（内层引用外层）

```sql
-- 每个客户的消费额，并标注是否高于该客户所在等级的平均
SELECT c.customer_name, c.tier,
       (SELECT ROUND(SUM(oi.line_amount),2)
        FROM fact_order o JOIN fact_order_item oi ON o.order_id=oi.order_id
        WHERE o.customer_id = c.customer_id AND o.status='已完成') AS 该客户消费
FROM dim_customer c
LIMIT 5;
```

**预期**：前 5 个客户的名字、等级、各自消费额。

### 4.5 CTE：把逻辑命名复用

```sql
WITH 省份销售 AS (
  SELECT r.province_name AS 省份,
         COUNT(DISTINCT o.order_id) AS 订单数,
         ROUND(SUM(oi.line_amount),2) AS 销售额
  FROM fact_order o
  JOIN fact_order_item oi ON o.order_id = oi.order_id
  JOIN dim_region     r  ON o.region_id = r.region_id
  WHERE o.status = '已完成'
  GROUP BY r.province_name
)
SELECT * FROM 省份销售 ORDER BY 销售额 DESC;
```

**预期**：和 ch04 的 4.3 完全一致（10 省降序，广东 1,078,152.70 居首）。区别是——逻辑被命名成「省份销售」，后续还能 `JOIN` 它、`WHERE` 它，无需复制整段。

---

## 五、验证：CTE + 排名（为 ch06 窗口函数铺垫）

用 CTE 先汇总客户消费，再用 `ORDER BY` 排出 TOP 5 客户：

```sql
WITH 客户消费 AS (
  SELECT c.customer_id, c.customer_name, c.tier,
         ROUND(SUM(oi.line_amount),2) AS 消费额
  FROM fact_order o
  JOIN fact_order_item oi ON o.order_id = oi.order_id
  JOIN dim_customer   c  ON o.customer_id = c.customer_id
  WHERE o.status = '已完成'
  GROUP BY c.customer_id
)
SELECT customer_name, tier, 消费额
FROM 客户消费
ORDER BY 消费额 DESC
LIMIT 5;
```

**预期结果**：

| 客户 | 等级 | 消费额 |
|---|---|---:|
| 梁诗 | 钻石 | 70,022.89 |
| 唐宇伟 | 钻石 | 67,890.55 |
| 马晨博 | 钻石 | 66,012.90 |
| 吴涛 | 钻石 | 65,767.42 |
| 彭艳鑫 | 钻石 | 61,699.01 |

> 注意：TOP 5 全是钻石会员——高等级 + 多订单（钻石均价 25 单 vs 普通 2.6 单）叠加出最高消费。ch06 会用 `RANK()` 给每个客户打名次，而不只是 `LIMIT 5`。

---

## 六、FDE 现场场景：老板要「异常订单」

老板：「把那些金额明显高于平均的订单挑出来，我看看是不是有大客户。」

你一句 CTE + 标量子查询搞定，还能把「平均」作为列展示在每一行旁边，老板一眼看出偏离度。**子查询的价值，是把「人脑里的比较」翻译成「SQL 里的参照值」**——平均、阈值、同业水位，都是这么用的。

---

## 七、本章小结

| 你学到了 | 关键点 |
|---|---|
| 子查询位置 | SELECT（标量）/ WHERE-IN（集合）/ WHERE-EXISTS（存在）/ FROM（派生表） |
| `IN` vs `EXISTS` | 集合包含用 IN；存在性判断用 EXISTS（常更快） |
| 关联子查询 | 内层 `WHERE` 引用外层列，逐行比对 |
| CTE `WITH` | 命名中间结果，可读性 >> 嵌套派生表 |
| 三个基准 | 平均客单价 3041.21 / 高于平均 909 单 / 有成交客户 498 人 |
| TOP5 客户 | 梁诗 70,022.89 居首，全为钻石 |

---

## 八、练习题

### 练习 1：CTE 重写省份排名（考：WITH 基础）

**题目**：用 CTE 重写 ch04 的省份销售排名。

**预期结果**：10 省降序，广东 1,078,152.70 居首（同 ch04 4.3）。

**解析**：CTE 把「GROUP BY 省份」命名成「省份销售」，主查询只负责排序展示，逻辑分层清晰。

---

### 练习 2：标量子查询（考：平均客单价 + 高于平均的订单）

**题目**：已完成订单里，金额高于全局平均客单价（3,041.21）的有多少单？

```sql
SELECT COUNT(*) AS 高于平均的订单数
FROM fact_order
WHERE status='已完成'
  AND order_amount > (SELECT AVG(order_amount) FROM fact_order WHERE status='已完成');
```

**预期结果**：**909 单**。

**解析**：子查询算出平均 3,041.21，外层数出高于它的订单。909 < 总数 2366 的一半，符合「平均线划分」直觉。

---

### 练习 3：IN 子查询（考：钻石客户订单）

**题目**：钻石会员的有效订单共多少单？

```sql
SELECT COUNT(*) AS 钻石有效订单数
FROM fact_order
WHERE status='已完成'
  AND customer_id IN (SELECT customer_id FROM dim_customer WHERE tier='钻石');
```

**预期结果**：**466 单**（与 ch03 钻石「订单数 466」一致）。

**解析**：`IN` 左侧是钻石客户 ID 集合，外层订单命中即计入。

---

### 练习 4：EXISTS（考：存在性）

**题目**：下过已完成订单的客户有多少人？

```sql
SELECT COUNT(*) AS 有成交客户数
FROM dim_customer c
WHERE EXISTS (SELECT 1 FROM fact_order o WHERE o.customer_id=c.customer_id AND o.status='已完成');
```

**预期结果**：**498 人**（总 500 人，2 人从未下过成交单，ch04 练习 5 已见）。

**解析**：`EXISTS` 对每位客户判断「有没有成交订单」，有则计数。

---

### 练习 5：CTE + 客户 TOP（考：综合）

**题目**：用 CTE 汇总每个客户消费额，取 TOP 5。

**预期结果**：梁诗 70,022.89 / 唐宇伟 67,890.55 / 马晨博 66,012.90 / 吴涛 65,767.42 / 彭艳鑫 61,699.01。

**解析**：见本章第五节。`LIMIT 5` 取前 5，ch06 会教你用 `RANK()` 给全量打名次。

---

## 下一步

`ORDER BY + LIMIT` 只能取前 N，却给不出「第几名」；「每个省内的客户排名」「累计到本月」「和上个月比环比」更需要**窗口函数**。下一章开始两章专攻它。

→ [ch06 窗口函数（上）：排序与排名](./ch06_窗口函数上_排序与排名.md)
