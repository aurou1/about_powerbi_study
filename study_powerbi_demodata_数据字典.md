# study_powerbi_demodata 数据字典

> 用途：Power BI + SQL 高级查询（多表 JOIN / 窗口函数 / CTE）学习用演示库
> 模型：电商订单星型模型（4 维度表 + 2 事实表）
> 环境：MySQL 8.0 / utf8mb4 / InnoDB
> 规模：6 张表，共 **15,780** 行（维度 1,806 + 事实 11,974）
> 生成脚本：`generate_powerbi_demo.py`（种子固定 `20260903`，可复现）

---

## 一、表清单与行数

| 表名 | 类型 | 中文名 | 行数 | 说明 |
|---|---|---|---:|---|
| `dim_region` | 维度 | 地区维度 | 10 | 省 / 大区 |
| `dim_product` | 维度 | 商品维度 | 200 | 商品 / 品类 / 品牌 / 成本毛利 |
| `dim_customer` | 维度 | 客户维度 | 500 | 客户 / 等级 / 注册信息 |
| `dim_date` | 维度 | 日期维度 | 1,096 | 2023-01-01 ~ 2025-12-31 |
| `fact_order` | 事实 | 订单事实（头） | 3,529 | 一单一行 |
| `fact_order_item` | 事实 | 订单明细事实 | 8,445 | 一单一品一行 |

---

## 二、ER 关系（星型模型）

```
                 dim_date(date_key)
                      ▲
                      │ fact_order.order_date
                      │
 dim_region(region_id)◀──────┐
      ▲                      │
      │ dim_customer.region_id│ fact_order.region_id
      │                      │
 dim_customer(customer_id)   │
      ▲                      │
      │ fact_order.customer_id
      │
 fact_order(order_id) ──▶ fact_order_item(order_id)
      ▲                       │
      │                       │ fact_order_item.product_id
      │                       ▼
      │                dim_product(product_id)
```

**外键约束**

| 子表.字段 | 引用父表.字段 | 说明 |
|---|---|---|
| `dim_customer.region_id` | `dim_region.region_id` | 客户所属省/大区 |
| `fact_order.customer_id` | `dim_customer.customer_id` | 订单归属客户 |
| `fact_order.region_id` | `dim_region.region_id` | 订单收货省/大区 |
| `fact_order.order_date` | `dim_date.date_key` | 下单日期（连日期维度） |
| `fact_order_item.order_id` | `fact_order.order_id` | 明细所属订单 |
| `fact_order_item.product_id` | `dim_product.product_id` | 明细商品 |

---

## 三、字段明细

### 3.1 dim_region（地区维度）

| 字段 | 类型 | 空 | 键 | 默认 | 中文含义 | 示例 |
|---|---|---|---|---|---|---|
| `region_id` | INT | 否 | PK, 自增 | — | 地区 ID | 1 |
| `province_name` | VARCHAR(20) | 否 | | — | 省份 | 广东 |
| `zone` | VARCHAR(10) | 否 | | — | 大区 | 华南 |

取值：province = 广东/江苏/浙江/上海/北京/山东/四川/湖北/辽宁/陕西；zone = 华南/华东/华北/西南/华中/东北/西北。
> 设计意图：华东 / 华南订单权重更高（见 `REGION_WEIGHTS`），方便练「地区销售额差异」。

### 3.2 dim_product（商品维度）

| 字段 | 类型 | 空 | 键 | 默认 | 中文含义 | 示例 |
|---|---|---|---|---|---|---|
| `product_id` | INT | 否 | PK | — | 商品 ID | 1 |
| `product_name` | VARCHAR(50) | 否 | | — | 商品名（品牌+品类词） | 鲜踪手工饼干 |
| `category` | VARCHAR(20) | 否 | | — | 品类 | 食品 |
| `brand` | VARCHAR(20) | 否 | | — | 品牌 | 鲜踪 |
| `cost_price` | DECIMAL(10,2) | 否 | | — | 成本价 | 297.58 |
| `list_price` | DECIMAL(10,2) | 否 | | — | 吊牌价 | 425.11 |

取值：category = 家居/数码/服饰/食品/美妆。
> 设计意图：各品类目标毛利率不同——**吊牌口径（无折扣）**：数码 12.00% < 食品 30.00% < 家居 35.00% < 服饰 45.00% < 美妆 55.00%。`list_price = cost_price / (1 - margin)`，用于练「品类毛利差异」。明细表的 `unit_price / unit_cost` 直接取自这里。
>
> ⚠️ **口径提醒（两套毛利率，别混用）**：上面是**吊牌口径**。实际成交因客户等级折扣（普通 2% / 银卡 8% / 金卡 15% / 钻石 20%，另有 ±0.03 随机抖动），**成交口径毛利率**会明显下降：
>
> | 品类 | 吊牌口径 | 成交口径（实跑） | 差额来自 |
> |---|---:|---:|---|
> | 数码 | 12.00% | **1.16%** | 客单价高，折扣吃掉大部分毛利 |
> | 食品 | 30.00% | **21.75%** | |
> | 家居 | 35.00% | **27.22%** | |
> | 服饰 | 45.00% | **38.00%** | |
> | 美妆 | 55.00% | **49.47%** | |
>
> **做分析一律用成交口径**（`line_profit / line_amount`）；吊牌口径只在讲定价逻辑时提。

### 3.3 dim_customer（客户维度）

| 字段 | 类型 | 空 | 键 | 默认 | 中文含义 | 示例 |
|---|---|---|---|---|---|---|
| `customer_id` | INT | 否 | PK | — | 客户 ID | 1 |
| `customer_name` | VARCHAR(30) | 否 | | — | 客户姓名 | 梁杰英 |
| `gender` | CHAR(1) | 否 | | — | 性别 | 女 |
| `city` | VARCHAR(20) | 否 | | — | 城市 | 宁波 |
| `region_id` | INT | 否 | FK(MUL) | — | 所属地区 ID | 3 |
| `register_date` | DATE | 否 | | — | 注册日期 | 2022-11-30 |
| `tier` | VARCHAR(10) | 否 | | — | 会员等级 | 普通 |

取值：gender ∈ {男, 女}；tier ∈ {普通, 银卡, 金卡, 钻石}（占比约 50% / 30% / 15% / 5%）。
> 设计意图：等级越高 → 订单越多（普通4 / 银卡6 / 金卡12 / 钻石25 单）、折扣越大（0.02 / 0.08 / 0.15 / 0.20），用于练「客户消费分层 / NTILE 分箱」。

### 3.4 dim_date（日期维度）

| 字段 | 类型 | 空 | 键 | 默认 | 中文含义 | 示例 |
|---|---|---|---|---|---|---|
| `date_key` | DATE | 否 | PK | — | 日期（主键） | 2025-10-16 |
| `year` | INT | 否 | | — | 年 | 2025 |
| `quarter` | INT | 否 | | — | 季度(1-4) | 4 |
| `month` | INT | 否 | | — | 月(1-12) | 10 |
| `month_name` | VARCHAR(10) | 否 | | — | 年月标签 | 2025年10月 |
| `week_of_year` | INT | 否 | | — | 年内周序 | 42 |
| `day_of_week` | INT | 否 | | — | 星期(1=周一…7=周日) | 4 |
| `weekday_name` | VARCHAR(10) | 否 | | — | 星期名 | 周四 |
| `is_weekend` | TINYINT | 否 | | — | 是否周末(0否/1是) | 0 |
| `is_holiday` | TINYINT | 否 | | — | 是否法定假日(0否/1是) | 0 |

> `is_holiday=1` 仅覆盖：元旦(1-1)、劳动节(5-1)、国庆(10-1)。范围 2023-01-01 ~ 2025-12-31（1,096 天）。用于 Power BI 时间智能（同比/累计/节假日对比）。

### 3.5 fact_order（订单事实-头）

| 字段 | 类型 | 空 | 键 | 默认 | 中文含义 | 示例 |
|---|---|---|---|---|---|---|
| `order_id` | INT | 否 | PK | — | 订单 ID | 1 |
| `customer_id` | INT | 否 | FK(MUL) | — | 客户 ID | 1 |
| `region_id` | INT | 否 | FK(MUL) | — | 地区 ID | 3 |
| `order_date` | DATE | 否 | FK(MUL) | — | 下单日期 | 2025-10-16 |
| `status` | VARCHAR(10) | 否 | | — | 订单状态 | 已完成 |
| `payment_method` | VARCHAR(10) | 否 | | — | 支付方式 | 支付宝 |
| `order_amount` | DECIMAL(12,2) | 否 | | 0.00 | 订单金额 | 1267.16 |
| `order_profit` | DECIMAL(12,2) | 否 | | 0.00 | 订单利润 | 570.22 |

取值：status ∈ {已完成×4, 已取消, 退款}（约 2/3 为已完成）；payment_method ∈ {微信, 支付宝, 银行卡}。
> 设计意图：月份季节性——6 月(618)、11 月(双11)、12 月(双12) 订单量显著高于其他月份（权重 14 / 16 / 15 vs 平时 7-9），用于练「时间趋势 / LAG-LEAD 环比」。

### 3.6 fact_order_item（订单明细事实）

| 字段 | 类型 | 空 | 键 | 默认 | 中文含义 | 示例 |
|---|---|---|---|---|---|---|
| `order_item_id` | INT | 否 | PK | — | 明细 ID | 1 |
| `order_id` | INT | 否 | FK(MUL) | — | 订单 ID | 1 |
| `product_id` | INT | 否 | FK(MUL) | — | 商品 ID | 104 |
| `quantity` | INT | 否 | | — | 数量 | 1 |
| `unit_price` | DECIMAL(10,2) | 否 | | — | 成交单价 | 1267.16 |
| `unit_cost` | DECIMAL(10,2) | 否 | | — | 单位成本 | 696.94 |
| `discount_rate` | DECIMAL(5,2) | 否 | | — | 行折扣率 | 0.00 |
| `line_amount` | DECIMAL(12,2) | 否 | | — | 行金额 | 1267.16 |
| `line_profit` | DECIMAL(12,2) | 否 | | — | 行利润 | 570.22 |

---

## 四、关键计算口径（务必遵守）

| 指标 | 公式 | 备注 |
|---|---|---|
| 行金额 `line_amount` | `quantity × unit_price × (1 - discount_rate)` | 成交单价已含品牌吊牌价 |
| 行利润 `line_profit` | `line_amount - quantity × unit_cost` | |
| 订单金额 `order_amount` | `SUM(line_amount)` 同 `order_id` | **表头恒等于明细汇总**（已校验 0 不一致） |
| 订单利润 `order_profit` | `SUM(line_profit)` 同 `order_id` | |
| 毛利率 | `order_profit / order_amount` | 可下钻到品类/地区 |
| **有效销售额** | `WHERE status = '已完成'` | 已取消/退款订单金额仍保留，但算「真实成交」须过滤状态 |
| 客单价 | `有效订单金额 / 有效订单数` | |

⚠️ **踩坑提醒**：`fact_order` 里「已取消 / 退款」的订单 `order_amount` 不为 0（金额照常记录，仅用 `status` 区分）。练习时若直接 `SUM(order_amount)`，会把作废订单也算进去——务必 `WHERE status='已完成'`（Power BI 用 `CALCULATE(SUM(...), 'fact_order'[status]="已完成")`）。

---

## 五、维度取值速查

| 维度 | 取值 | 业务权重 |
|---|---|---|
| `zone`（大区） | 东北 / 华东 / 华中 / 华北 / 华南 / 西北 / 西南 | 华东+华南权重最高 |
| `category`（品类） | 数码 / 食品 / 家居 / 服饰 / 美妆 | **成交口径**毛利率：数码 1.16% < 食品 21.75% < 家居 27.22% < 服饰 38.00% < 美妆 49.47%（吊牌口径 12% / 30% / 35% / 45% / 55%，差额来自折扣） |
| `tier`（等级） | 普通 / 银卡 / 金卡 / 钻石 | 订单数 4/6/12/25；折扣 0.02/0.08/0.15/0.20 |
| `status`（状态） | 已完成 / 已取消 / 退款 | 已完成约占 2/3 |
| `payment_method` | 微信 / 支付宝 / 银行卡 | 均匀分布 |
| `gender` | 男 / 女 | 均匀分布 |
| `is_weekend` | 0 工作日 / 1 周末 | — |
| `is_holiday` | 0 非法定 / 1 法定 | 仅元旦/五一/国庆 |

---

## 六、推荐练手路径

- **SQL 入门**：`fact_order` 连 `dim_customer` / `dim_region` / `dim_date` 做多表 JOIN + GROUP BY。
- **SQL 进阶**：CTE + 子查询算「各品类毛利率」「各地区 TOP 客户」。
- **窗口函数**：`SUM() OVER (PARTITION BY region_id ORDER BY order_date)` 累计、`RANK()/ROW_NUMBER()` 排名、`LAG()/LEAD()` 月度环比、`NTILE(4)` 客户分层。
- **Power BI**：导入 6 表 → 按上方 ER 建关系 → 建度量值（销售额/利润/客单价）→ 时间智能（YTD、同比）→ 地图/矩阵/TOP N 可视化。

> 配套练习见 `PowerBI_SQL学习练习清单.md`。
