# Power BI + SQL 学习练习清单

配套数据库：`study_powerbi_demodata`（MySQL 8.0，共 **15,780** 行 = 维度 1,806 + 事实 11,974）
生成脚本：`generate_powerbi_demo.py`（重跑即重建，数据可复现）

## 一、库结构速览（星型模型）
| 表 | 类型 | 行数 | 说明 |
|---|---|---|---|
| dim_region | 维度 | 10 | 省 / 大区 |
| dim_product | 维度 | 200 | 商品 / 品类 / 品牌 / 成本 / 吊牌价 |
| dim_customer | 维度 | 500 | 客户 / 性别 / 城市 / 等级(tier) |
| dim_date | 维度 | 1096 | 2023-01-01 ~ 2025-12-31 日期维度 |
| fact_order | 事实(头) | 3529 | 订单 / 客户 / 地区 / 日期 / 状态 / 金额 |
| fact_order_item | 事实(明细) | 8445 | 订单明细 / 商品 / 数量 / 单价 / 折扣 / 金额 / 利润 |

**关系**：fact_order_item → fact_order → dim_customer / dim_region / dim_date；fact_order_item → dim_product；dim_customer → dim_region。

**数据里埋好的"可分析差异"（练SQL/Power BI 才有意义）**：
- 地区：广东单量/销售额明显高于其他省
- 品类毛利率：美妆≈50% > 服饰≈38% > 家居≈27% > 食品≈22% > 数码≈1%
- 客户等级：钻石/金卡订单更多、折扣更高（241/149/83/27 人）
- 时间：6月(618)、11月(双11)、12月(双12) 订单量显著冲高
- 状态：约 1/3 订单是 已取消/退款（算有效销售额要 `WHERE status='已完成'`）

> ⚠️ `fact_order.order_amount` 恒等于其明细汇总；取消/退款订单金额不为零，只是用 `status` 标记。所以**有效销售额**必须加 `WHERE status='已完成'`。

---

## 二、SQL 练习（15 题，由浅入深）

### 基础：JOIN + 聚合（练多表关联、GROUP BY）
1. **各省订单数、总销售额**（JOIN fact_order + dim_region，按省分组）
2. **各品类销售额与利润**（JOIN fact_order_item + dim_product，GROUP BY category）
3. **客单价最高的 10 个客户**（JOIN 客户，按客户汇总金额，ORDER BY 客单价 DESC LIMIT 10）
4. **各支付方式占比**（GROUP BY payment_method）
5. **有效订单（已完成）的销售额**（加 `WHERE status='已完成'`）

### 中级：子查询 + CTE
6. **销售额高于平均客单价的订单**（子查询算平均值再过滤）
7. **用 CTE 先算"各省年度销售额"，再筛选超过 50 万的省**
8. **查找"下过单但等级是普通"的客户**（事实表 LEFT JOIN 维度 + 条件）
9. **各品类销售额占比（子查询算总额做分母）**
10. **复购客户数**：下过 ≥2 笔有效订单的客户有多少（GROUP BY customer_id HAVING COUNT>=2）

### 高级：窗口函数（重点）
11. **各省销售额排名**：`RANK() OVER (ORDER BY SUM(order_amount) DESC)`
12. **每个客户按时间累计消费**：`SUM(order_amount) OVER (PARTITION BY customer_id ORDER BY order_date)`
13. **各品类内按销量的商品排名**：`ROW_NUMBER() OVER (PARTITION BY category ORDER BY SUM(quantity) DESC)`
14. **月度销售额环比**：`LAG(月销售额) OVER (ORDER BY 月份)` 算 `(本月-上月)/上月`
15. **把客户按累计消费分 4 档**：`NTILE(4) OVER (ORDER BY 累计消费 DESC)`；再算每档人数

> 进阶可选：各月销售额 3 个月移动平均 `AVG() OVER (ORDER BY 月份 ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)`；客户前后两笔订单间隔 `LEAD(order_date) OVER (PARTITION BY customer_id ORDER BY order_date)`。

### 参考 SQL（窗口函数典型写法）
```sql
-- 12) 客户累计消费
SELECT customer_id, order_date, order_amount,
       SUM(order_amount) OVER (PARTITION BY customer_id ORDER BY order_date) AS 累计消费
FROM fact_order
WHERE status='已完成'
ORDER BY customer_id, order_date;

-- 14) 月度环比
WITH m AS (
  SELECT DATE_FORMAT(order_date,'%Y-%m') ym, SUM(order_amount) 月销售额
  FROM fact_order WHERE status='已完成'
  GROUP BY DATE_FORMAT(order_date,'%Y-%m')
)
SELECT ym, 月销售额,
       LAG(月销售额) OVER (ORDER BY ym) 上月销售额,
       ROUND((月销售额-LAG(月销售额) OVER (ORDER BY ym))/LAG(月销售额) OVER (ORDER BY ym)*100,1) 环比pct
FROM m ORDER BY ym;

-- 15) 客户分档
WITH cust AS (
  SELECT customer_id, SUM(order_amount) 累计
  FROM fact_order WHERE status='已完成'
  GROUP BY customer_id
)
SELECT customer_id, 累计, NTILE(4) OVER (ORDER BY 累计 DESC) 档位
FROM cust;
```

---

## 三、Power BI 学习任务（10 条）
1. **获取数据**：Power BI Desktop → 获取数据 → MySQL 数据库，连 `study_powerbi_demodata`（需 64 位 MySQL Connector/ODBC）。
2. **建关系**：在"模型"视图把 4 个维度连到事实表（fact_order_item 为明细事实，fact_order 为订单头桥接）。
3. **建度量值**：总销售额 `SUM(fact_order[order_amount])`、总利润、订单数 `COUNTROWS(fact_order)`、客单价 `DIVIDE([总销售额],[订单数])`。
4. **筛选有效销售**：新建度量 `[有效销售额] = CALCULATE([总销售额], fact_order[status]="已完成")`。
5. **矩阵**：行=地区(省)，列=品类，值=有效销售额。
6. **切片器**：年份 / 品类，联动所有图表。
7. **折线图**：月度销售趋势（用 dim_date 做轴）。
8. **时间智能**：YTD `TOTALYTD([有效销售额], dim_date[date_key])`、同比 `SAMEPERIODLASTYEAR`。
9. **TOP N 条形图**：销售额 TOP10 商品（"筛选器"里选 TOP N）。
10. **客户分层矩阵**：按 tier 看各等级销售额与人数占比。

---

## 四、窗口函数语法速查
```sql
函数() OVER (
  PARTITION BY 分组列          -- 类似 GROUP BY，但不聚合行
  ORDER BY 排序列              -- 决定累计/排名顺序
  ROWS BETWEEN 2 PRECEDING AND CURRENT ROW  -- 移动窗口(可选)
)
```
常用：ROW_NUMBER（不并列）、RANK（并列跳号）、DENSE_RANK（并列不跳号）、SUM/AVG（累计/移动）、LAG/LEAD（取前/后行）、NTILE(n)（均分 n 档）。
