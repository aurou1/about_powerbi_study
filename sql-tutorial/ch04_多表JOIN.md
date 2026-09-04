# ch04 多表 JOIN 🔗

> 本章目标：把星型模型的 6 张表串起来算「广东卖了多少、哪个客户最值钱」，并**识破 JOIN 最阴险的陷阱——数字悄悄膨胀**。
> 学完你能放心地跨表查询，而不再担心客单价莫名变成 9,192.99。

---

## 一、本章学习目标

1. 区分 `INNER JOIN` / `LEFT JOIN` / `RIGHT JOIN` 的取数逻辑
2. 把 `fact_order` 连上 4 张维度表，做出带中文维度的报表
3. **识破 JOIN 膨胀**：订单数变多、客单价虚高 3 倍
4. 掌握「先聚合再 JOIN」或「在明细级汇总」两种安全写法
5. 用 `LEFT JOIN` 找出「没有订单的客户」（预览 ch08 的 NULL）

---

## 二、为什么要学 JOIN（而且要怕它）

单表查询（ch01-03）只能回答「这张表内部」的问题。但真实业务：

- 「广东卖了多少」需要 `fact_order.region_id` → `dim_region.province_name`
- 「美妆毛利率」需要 `fact_order_item.product_id` → `dim_product.category`
- 「钻石会员top客户」需要 `fact_order.customer_id` → `dim_customer.tier`

这些都要 JOIN。**但 JOIN 是新手数字翻车的第一现场**——它不会报错，只是让你的行数、金额、客单价悄悄变大。本章 half 篇幅都在讲怎么不被它坑。

---

## 三、概念：三种 JOIN

以「订单 ↔ 客户」为例（一个客户多个订单，一对多）：

| JOIN 类型 | 取什么 | 本例结果 |
|---|---|---|
| `INNER JOIN` | 两表都匹配的行 | 只保留下过单的客户 + 他们的订单 |
| `LEFT JOIN` | 左表全保留，右表无匹配补 NULL | 所有客户都在，没下单的补 NULL |
| `RIGHT JOIN` | 右表全保留，左表无匹配补 NULL | 与 LEFT 相反，少用 |

语法：

```sql
SELECT 列
FROM 左表
[INNER|LEFT|RIGHT] JOIN 右表 ON 左表.键 = 右表.键
WHERE ...;
```

> 本库所有外键都已建好（数据字典第二节）。`ON` 后面写「左表.外键 = 右表.主键」即可。

---

## 四、实操：星型模型 JOIN 实战

### 4.1 订单连客户、地区、日期（一对多，安全）

```sql
SELECT o.order_id, c.customer_name, c.tier, r.province_name, o.order_date, o.order_amount
FROM fact_order o
JOIN dim_customer c ON o.customer_id = c.customer_id
JOIN dim_region   r ON o.region_id   = r.region_id
WHERE o.status = '已完成'
LIMIT 10;
```

**预期**：10 行，每行带客户名、等级、省份、日期（订单头级，没膨胀）。

### 4.2 明细连商品（算品类维度）

```sql
SELECT p.category, ROUND(SUM(oi.line_amount),2) AS 有效销售额
FROM fact_order_item oi
JOIN dim_product p ON oi.product_id = p.product_id
JOIN fact_order  o ON oi.order_id  = o.order_id
WHERE o.status = '已完成'
GROUP BY p.category
ORDER BY 有效销售额 DESC;
-- 预期：数码 2612383.09 / 美妆 1381720.47 / 家居 1408258.89 / 服饰 1351789.04 / 食品 441341.24
```

### 4.3 各省有效销售额排名（多维 JOIN）

```sql
SELECT r.province_name                              AS 省份,
       COUNT(DISTINCT o.order_id)                  AS 有效订单数,
       ROUND(SUM(oi.line_amount),2)                AS 有效销售额
FROM fact_order o
JOIN fact_order_item oi ON o.order_id = oi.order_id
JOIN dim_region     r  ON o.region_id = r.region_id
WHERE o.status = '已完成'
GROUP BY r.province_name
ORDER BY 有效销售额 DESC;
```

**预期结果**：

| 省份 | 有效订单数 | 有效销售额 |
|---|---:|---:|
| 广东 | 352 | 1,078,152.70 |
| 浙江 | 277 | 849,660.63 |
| 上海 | 265 | 816,614.17 |
| 江苏 | 255 | 800,322.96 |
| 北京 | 267 | 761,942.54 |
| 湖北 | 218 | 700,373.18 |
| 山东 | 216 | 672,082.30 |
| 四川 | 177 | 562,613.26 |
| 辽宁 | 167 | 517,676.34 |
| 陕西 | 172 | 436,054.65 |

---

## 五、★ 验证：JOIN 膨胀三大陷阱

这是全教程**最容易让你在客户面前出丑**的地方。逐条跑，记住数字。

### 陷阱 A：订单数被明细行数放大

```sql
SELECT COUNT(*) AS 行数 FROM fact_order o JOIN fact_order_item oi ON o.order_id = oi.order_id WHERE o.status='已完成';
-- 预期：5686（不是 2366！）
```

**一个订单有多个明细行，JOIN 后一行变多行**。正确订单数要用 `COUNT(DISTINCT o.order_id)` = **2,366**。

### 陷阱 B：客单价虚高到 9,192.99

```sql
-- 错误：JOIN 后把订单头金额 order_amount 重复求和（每个订单头被明细行复制了 N 次）
SELECT ROUND(SUM(o.order_amount)/COUNT(DISTINCT o.order_id),2) AS 错误客单价
FROM fact_order o JOIN fact_order_item oi ON o.order_id = oi.order_id WHERE o.status='已完成';
-- 预期：9192.99  ← 错误！

-- 正确：用明细级 line_amount 汇总，或单表 fact_order
SELECT ROUND(SUM(oi.line_amount)/COUNT(DISTINCT o.order_id),2) AS 正确客单价
FROM fact_order o JOIN fact_order_item oi ON o.order_id = oi.order_id WHERE o.status='已完成';
-- 预期：3041.21  ← 正确
```

**为什么 9,192.99？** `SUM(o.order_amount)` 在 JOIN 后，每个订单的「头金额」被复制成「明细行数」份，总和变成 21,750,618.54（是真实 7,195,492.73 的 **3.02 倍**），再除以订单数 → 9,192.99。正确值 3,041.21 是 Power BI 教程 ch04 的基准，二者必须一致。

### 陷阱 C：同时汇总两张事实表 → 金额翻倍/多倍

```sql
SELECT ROUND(SUM(o.order_amount) + SUM(oi.line_amount),2) AS 荒诞金额
FROM fact_order o JOIN fact_order_item oi ON o.order_id = oi.order_id WHERE o.status='已完成';
-- 预期：28946111.27  ← 明显荒谬（真实才 719 万）
```

**为什么？** 订单头和明细的「同订单金额」本就相等（数据字典：表头恒等于明细汇总）。你把两张表都加一遍，又叠加了陷阱 B 的重复 → 飙到 2,894 万。

> **三条保命规则**：
> 1. 数订单 → `COUNT(DISTINCT order_id)`，别用 `COUNT(*)`
> 2. 算金额 → **只用一张事实表**（`fact_order_item.line_amount` 或 `fact_order.order_amount` 二选一），绝不同时加
> 3. 一对多 JOIN 后做聚合，要么「在明细级汇总」(line_amount)，要么「先按订单聚合再 JOIN」

---

## 六、FDE 现场场景：报表数字和财务对不上

财务：「我们系统里客单价是 3,041，你这报表怎么 9,193？」

你秒答：「我把订单头和明细 JOIN 后，订单头金额被明细行数重复加了一遍。改成明细级汇总就好。」——**这句话能让你显得专业，而不是慌张**。

> **核心心法**：JOIN 前后，先想清楚「一行代表什么」。订单头 JOIN 明细后，一行 = 一个商品行，不是一笔订单。所有「按订单」的指标（订单数、客单价）都要 `COUNT(DISTINCT order_id)` 或回到订单头算。

---

## 七、本章小结

| 你学到了 | 关键点 |
|---|---|
| 三种 JOIN | INNER（都匹配）/ LEFT（左全保留）/ RIGHT（右全保留） |
| 星型 JOIN | 事实表 `JOIN` 维度表用外键，取中文维度 |
| ★ 陷阱 A | JOIN 后行数膨胀：5686 vs 正确 2366（用 DISTINCT） |
| ★ 陷阱 B | 客单价虚高 9192.99 vs 正确 3041.21（头金额被复制 3.02 倍） |
| ★ 陷阱 C | 双表求和 → 28946111.27（荒谬） |
| 安全写法 | 金额只用一张事实表；订单数用 COUNT(DISTINCT) |

---

## 八、练习题

### 练习 1：各省销售排名（考：多维 JOIN + GROUP BY）

**题目**：跑 4.3，确认 10 省销售额降序，广东第一。

**预期结果**：见 4.3 表格（广东 1,078,152.70 居首，陕西 436,054.65 垫底）。

**解析**：`fact_order` → `dim_region` 取省份，`fact_order` → `fact_order_item` 取金额，三表 JOIN 一次完成。

---

### 练习 2：2024 各月销售（考：JOIN 日期维度）

**题目**：用 `JOIN dim_date` 取出 2024 年 12 个月的有效销售额。

```sql
SELECT d.month, ROUND(SUM(oi.line_amount),2) AS 销售额
FROM fact_order o JOIN fact_order_item oi ON o.order_id=oi.order_id
JOIN dim_date d ON o.order_date=d.date_key
WHERE o.status='已完成' AND d.year=2024
GROUP BY d.month ORDER BY d.month;
```

**预期结果**：1月238,217.59 … 6月316,127.25（618）… 11月323,919.78（双11）… 12月342,525.66（双12）。12 月合计 2,535,109.95（= ch02 的 2024 有效销售额）。

**解析**：连日期维度是为了拿到 `year/month` 这种层级字段，比用 `MONTH(order_date)` 函数更利于走索引（ch10）。

---

### 练习 3：客单价膨胀（考：陷阱 B 复现）

**题目**：分别算出错误客单价（头金额重复）和正确客单价。

**预期结果**：错误 **9,192.99**，正确 **3,041.21**。

**解析**：见第五节陷阱 B。回家背下来：本库正确客单价 = 3,041.21。

---

### 练习 4：订单数膨胀（考：陷阱 A 复现）

**题目**：JOIN 明细后 `COUNT(*)` 是多少？正确订单数怎么写？

```sql
SELECT COUNT(*) AS 错_rows,
       COUNT(DISTINCT o.order_id) AS 对_订单数
FROM fact_order o JOIN fact_order_item oi ON o.order_id=oi.order_id
WHERE o.status='已完成';
```

**预期结果**：错 5,686，对 2,366。

**解析**：一对多 JOIN 让「一行=一商品」，COUNT(*) 数的是商品行。订单数必须 DISTINCT。

---

### 练习 5：LEFT JOIN 找 0 单客户（考：LEFT + NULL 预览）

**题目**：哪些客户**从没下过已完成订单**？用 LEFT JOIN + IS NULL。

```sql
SELECT c.customer_name, c.tier
FROM dim_customer c
LEFT JOIN fact_order o ON c.customer_id=o.customer_id AND o.status='已完成'
WHERE o.order_id IS NULL;
```

**预期结果**：2 个客户（普通/低活跃）。

**解析**：LEFT JOIN 保留所有客户，没匹配到订单的 `o.order_id` 为 NULL，用 `WHERE o.order_id IS NULL` 捞出。`NULL` 是 ch08 的重头戏，这里先感受它长什么样。

---

## 下一步

多维 JOIN 你会了，但「每个省里卖得最好的客户」「比平均客单价高的订单」这类**嵌套逻辑**，光靠 JOIN 写起来很绕。下一章用**子查询和 CTE** 把复杂逻辑拆成一步步。

→ [ch05 子查询与 CTE](./ch05_子查询与CTE.md)
