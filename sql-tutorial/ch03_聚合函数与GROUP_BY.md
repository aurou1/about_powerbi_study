# ch03 聚合函数与 GROUP BY 📊

> 本章目标：用 `COUNT/SUM/AVG/MIN/MAX` 配合 `GROUP BY` 算出「每个品类的销售额和毛利率」，并用 `HAVING` 过滤分组结果。
> 学完你能回答老板最常问的「分品类、分等级、分地区的汇总」。

---

## 一、本章学习目标

1. 区分**聚合函数**和**分组列**——`SELECT` 里非聚合的列必须进 `GROUP BY`
2. 用 `GROUP BY` 把行按维度分桶，再对每个桶算汇总
3. 用 `HAVING` 过滤「分组之后」的结果（区别于 `WHERE` 过滤行）
4. 算出成交口径毛利率，并理解「加权 vs 简单平均」的坑
5. 锁定本教程三大核心数：有效销售额 7,195,492.73 / 有效利润 1,706,864.78 / 毛利率 23.72%

---

## 二、为什么要先学聚合

过滤（ch02）解决「取哪些行」，但老板要的从来不是行，而是**结论**：

- 「每个品类卖了多少、赚了多少？」
- 「钻石会员贡献了多少销售额？」
- 「哪些品类毛利率低于 20%？」

这些都要先把行**按维度分组**，再对每组算一个汇总值。这就是 `GROUP BY`。

---

## 三、概念：聚合函数

| 函数 | 作用 | 忽略 NULL？ |
|---|---|---|
| `COUNT(列)` | 计数（不含 NULL） | 是 |
| `COUNT(*)` | 数行（含 NULL 行） | 否（数行本身） |
| `SUM(列)` | 求和 | 是 |
| `AVG(列)` | 平均 | 是 |
| `MIN(列)` / `MAX(列)` | 最小 / 最大 | 是 |

> 关键规则：**`SELECT` 里一旦出现聚合函数，所有「没被聚合」的列都必须写进 `GROUP BY`**。否则数据库不知道这列该取哪一行的值，直接报错（MySQL 宽松模式可能不报错但给错值，更危险）。

### 🔍 原理深挖：GROUP BY 在数据库里怎么"分组"？（配图）

GROUP BY 不是魔法，执行时是**把行分进桶里，再对每桶做聚合**：

```
原始行(过滤后, 假设12行, 每行带 category):
  数码 数码 食品 家居 数码 服饰 食品 数码 家居 食品 服饰 数码

① 分桶(按 category 建桶, 相同值进同一桶):
   ┌──数码桶──┐  ┌食品桶┐  ┌家居桶┐  ┌服饰桶┐
   │ 5行       │  │ 3行  │  │ 2行  │  │ 2行  │
   └──────────┘  └──────┘  └──────┘  └──────┘

② 每桶各算聚合(COUNT/SUM/AVG):
   数码: COUNT=5  SUM=xxxx   ← 桶内算, 桶与桶互不干扰
   食品: COUNT=3  SUM=xxxx
   家居: COUNT=2  ...

③ 每组输出一行 → 结果行数 = 桶数(组数)
```

```
多维分组 GROUP BY category, tier = 先按品类分, 品类内再按等级分:
  全表 → [数码桶 → (普通,银卡,金卡,钻石)子桶] + [食品桶 → ...] + ...
  结果 = 品类 × 等级的"格子"(笛卡尔积的组合里非空的那些)
```

**为什么会有"SELECT 中非聚合列必须进 GROUP BY"的规则？** 看图：分桶后，桶里的行被"压"成一行，非聚合列（如某行的 product_name）**没有唯一值可取**——数据库不知道取哪行，所以强制你 GROUP BY 它或包进聚合函数。这就是 SQL 的"分组 = 折叠行"的本质。

---

## 四、实操：从单组到多维分组

### 4.1 全表一个汇总（不分组）

```sql
SELECT COUNT(*)                    AS 有效订单数,
       ROUND(SUM(order_amount),2) AS 有效销售额
FROM fact_order
WHERE status = '已完成';
-- 预期：2366 | 7195492.73
```

### 4.2 按品类分组（核心案例）

```sql
SELECT p.category                                   AS 品类,
       ROUND(SUM(oi.line_amount),2)                 AS 有效销售额,
       ROUND(SUM(oi.line_profit),2)                 AS 有效利润,
       ROUND(SUM(oi.line_profit)/SUM(oi.line_amount)*100, 2) AS 毛利率pct
FROM fact_order_item oi
JOIN dim_product  p ON oi.product_id = p.product_id
JOIN fact_order   o ON oi.order_id  = o.order_id
WHERE o.status = '已完成'
GROUP BY p.category
ORDER BY 毛利率pct;
```

**预期结果**：

| 品类 | 有效销售额 | 有效利润 | 毛利率 |
|---|---:|---:|---:|
| 数码 | 2,612,383.09 | 30,291.28 | **1.16%** |
| 食品 | 441,341.24 | 95,995.03 | 21.75% |
| 家居 | 1,408,258.89 | 383,334.76 | 27.22% |
| 服饰 | 1,351,789.04 | 513,684.38 | 38.00% |
| 美妆 | 1,381,720.47 | 683,559.33 | 49.47% |

> **这条是成交口径毛利率**，全教程统一用它：数码 1.16% < 食品 21.75% < 家居 27.22% < 服饰 38.00% < 美妆 49.47%。（吊牌口径是 12%/30%/35%/45%/55%，那是「不打折」的理论值，详见数据字典。）

### 4.3 `HAVING`：过滤分组结果

`WHERE` 在分组**前**过滤行；`HAVING` 在分组**后**过滤组。

```sql
-- 找出有效销售额超过 100 万的品类
SELECT p.category, ROUND(SUM(oi.line_amount),2) AS 销售额
FROM fact_order_item oi
JOIN dim_product p ON oi.product_id = p.product_id
JOIN fact_order  o ON oi.order_id  = o.order_id
WHERE o.status = '已完成'
GROUP BY p.category
HAVING SUM(oi.line_amount) > 1000000
ORDER BY 销售额 DESC;
```

**预期结果**：数码 2,612,383.09 / 家居 1,408,258.89 / 美妆 1,381,720.47 / 服饰 1,351,789.04（共 4 个，食品 441,341.24 被 `HAVING` 滤掉）。

### 4.4 按客户等级分组

```sql
SELECT c.tier                              AS 等级,
       COUNT(DISTINCT o.order_id)          AS 订单数,
       COUNT(*)                            AS 明细行数,
       ROUND(SUM(oi.line_amount),2)        AS 有效销售额
FROM fact_order o
JOIN fact_order_item oi ON o.order_id = oi.order_id
JOIN dim_customer   c  ON o.customer_id = c.customer_id
WHERE o.status = '已完成'
GROUP BY c.tier
ORDER BY FIELD(c.tier,'普通','银卡','金卡','钻石');
```

**预期结果**：普通 637单/1477行/2,029,219.58；银卡 610/1478/1,920,208.56；金卡 653/1627/1,952,447.38；钻石 466/1104/1,293,617.21。

---

## 五、验证：加权毛利率 vs 简单平均（重要坑）

这是 ch03 最该刻进脑子的一课。

```sql
-- 加权毛利率（金额加权，正确）
SELECT ROUND(SUM(oi.line_profit)/SUM(oi.line_amount)*100, 2) AS 加权毛利率
FROM fact_order_item oi JOIN fact_order o ON oi.order_id=o.order_id
WHERE o.status='已完成';
-- 预期：23.72%

-- 简单平均（每行毛利率先算再平均，错误代表）
SELECT ROUND(AVG(oi.line_profit/oi.line_amount)*100, 2) AS 简单平均毛利率
FROM fact_order_item oi JOIN fact_order o ON oi.order_id=o.order_id
WHERE o.status='已完成';
-- 预期：28.41%
```

**两个数字差了 4.69 个百分点**。为什么？

- **加权 23.72%** = 总利润 ÷ 总销售额，金额大的订单话语权大
- **简单平均 28.41%** = 把 5,686 行各自的毛利率先算出来再平均，**每行话语权一样大**

金额最大的几行全是低毛利数码（单行 1.2 万+，毛利率仅 6-7%），它们在「简单平均」里只算 1 行，被大量高毛利小单稀释了，于是平均被拉高到 28.41%。**汇报毛利率，永远用加权（23.72%）**，否则你会虚假乐观。

> 顺带验证两个极值：数码品类里最惨的一行毛利率 **-14.29%**（亏本甩），美妆最高一行 55.00%（恰好是吊牌口径上限，即没打折）。整体有效利润 **1,706,864.78**、有效销量 **8,626 件**、单件利润 **197.87** 元。

---

## 六、FDE 现场场景：客户要「平均毛利率」

客户：「给我们看各品类的**平均毛利率**。」

你立刻要追问一句：**「您要的是金额加权平均，还是每行简单平均？」**

- 财务/老板看整体盈利 → **加权 23.72%**（唯一正确）
- 选品/采购看「 typical 单品赚多少」 → 简单平均 28.41%（但必须标明是简单平均，且要意识到被大小单扭曲）

> **核心心法**：同一个词「平均」，在 SQL 里可能是 `SUM/SUM`（加权）也可能是 `AVG()`（简单）。不定义清楚，你和客户说的根本不是一个数。这正是 FDE 的「翻译」价值——把业务的模糊词翻成精确的 SQL 语义。

---

## 七、本章小结

| 你学到了 | 关键点 |
|---|---|
| 聚合 + 分组 | 非聚合列必须进 `GROUP BY` |
| `WHERE` vs `HAVING` | `WHERE` 过滤行（分组前）、`HAVING` 过滤组（分组后） |
| 成交毛利率 | 数码 1.16% < 食品 21.75% < 家居 27.22% < 服饰 38.00% < 美妆 49.47% |
| ★ 加权 23.72% | 汇报毛利率用 `SUM/SUM`，别用 `AVG()`（简单平均虚高到 28.41%） |
| 三大核心数 | 销售额 7,195,492.73 / 利润 1,706,864.78 / 销量 8,626 / 单件利润 197.87 |
| 等级汇总 | 普通237万 / 银卡192万 / 金卡195万 / 钻石129万（有效） |

---

## 八、练习题

### 练习 1：各品类销售额与利润率（考：GROUP BY 主案例）

**题目**：重跑 4.2 的品类分组查询，确认 5 行结果。

**预期结果**：见 4.2 表格（数码 1.16% 最低，美妆 49.47% 最高）。

**解析**：`SUM(line_profit)/SUM(line_amount)` 是金额加权的品类毛利率，分母用汇总额而非行数。

---

### 练习 2：客户等级汇总（考：多指标分组）

**题目**：按客户等级统计订单数、明细行数、有效销售额。

```sql
SELECT c.tier, COUNT(DISTINCT o.order_id) 订单数, COUNT(*) 明细行数,
       ROUND(SUM(oi.line_amount),2) 有效销售额
FROM fact_order o JOIN fact_order_item oi ON o.order_id=oi.order_id
JOIN dim_customer c ON o.customer_id=c.customer_id
WHERE o.status='已完成' GROUP BY c.tier
ORDER BY FIELD(c.tier,'普通','银卡','金卡','钻石');
```

**预期结果**：普通 637/1477/2,029,219.58；银卡 610/1478/1,920,208.56；金卡 653/1627/1,952,447.38；钻石 466/1104/1,293,617.21。

**解析**：`COUNT(DISTINCT o.order_id)` 数订单，`COUNT(*)` 数明细行（一对多，行数更多）。

---

### 练习 3：HAVING 过滤（考：分组后过滤）

**题目**：找出有效销售额 > 100 万的品类。

**预期结果**：数码 / 家居 / 美妆 / 服饰 4 个（食品 441,341.24 被滤掉）。

**解析**：`HAVING` 作用在 `GROUP BY` 之后，能用聚合结果（这里是 `SUM(line_amount)`）做条件。

---

### 练习 4：加权 vs 简单平均（考：毛利率口径陷阱）

**题目**：分别跑加权毛利率和简单平均毛利率，说出差多少。

```sql
SELECT ROUND(SUM(oi.line_profit)/SUM(oi.line_amount)*100,2) 加权,
       ROUND(AVG(oi.line_profit/oi.line_amount)*100,2) 简单平均
FROM fact_order_item oi JOIN fact_order o ON oi.order_id=o.order_id
WHERE o.status='已完成';
```

**预期结果**：加权 **23.72%**，简单平均 **28.41%**，差 **4.69 个百分点**。

**解析**：见本章第五节。汇报一律用加权。

---

### 练习 5：各等级平均客单价（考：聚合+分组+除法）

**题目**：每个客户等级的平均客单价（有效销售额 ÷ 有效订单数）是多少？

```sql
SELECT c.tier,
       ROUND(SUM(oi.line_amount)/COUNT(DISTINCT o.order_id),2) AS 平均客单价
FROM fact_order o JOIN fact_order_item oi ON o.order_id=oi.order_id
JOIN dim_customer c ON o.customer_id=c.customer_id
WHERE o.status='已完成'
GROUP BY c.tier
ORDER BY FIELD(c.tier,'普通','银卡','金卡','钻石');
```

**预期结果**：普通 3,185.59 / 银卡 3,147.88 / 金卡 2,989.97 / 钻石 2,776.00。

**解析**：反直觉——等级越高客单价反而越低。因为高等级客户折扣大（钻石 20%）、且买得多摊薄了单价。这提醒你：**别凭直觉下结论，用 SQL 拉出来看**。

---

## 下一步

维度表（品类、等级）你会分组了，但订单和商品还靠 `JOIN` 硬连。下一章系统讲**多表 JOIN**——以及它最阴险的陷阱：JOIN 之后数字悄悄膨胀。

→ [ch04 多表 JOIN](./ch04_多表JOIN.md)
