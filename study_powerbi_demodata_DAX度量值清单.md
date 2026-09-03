# study_powerbi_demodata — DAX 度量值与查询清单

> 配套：`study_powerbi_demodata_数据字典.md`、`PowerBI_SQL学习练习清单.md`  
> 模型：电商订单星型模型（dim\_* 维度 + fact_order / fact_order_item 事实）  
> 用法：度量值贴进 Power BI「建模 → 新建度量值」；`EVALUATE` 段可在 DAX Studio / 表格工具里直接跑（验证度量值用）

---

## 〇、模型前置（必做）

1. **建关系**（与数据字典 ER 一致）：
   - `dim_customer[customer_id]` → `fact_order[customer_id]`
   - `dim_region[region_id]` → `fact_order[region_id]`（及 `dim_customer[region_id]`）
   - `dim_date[date_key]` → `fact_order[order_date]`
   - `fact_order[order_id]` → `fact_order_item[order_id]`（**一头筛选多端，默认方向即可**）
   - `dim_product[product_id]` → `fact_order_item[product_id]`
2. **标记日期表**：选中 `dim_date` → 建模 → 标记为日期表（时间智能函数才生效）。
3. **金额口径**：`fact_order_item[line_amount]` 是最细粒度；`fact_order[order_amount]` 已等于其汇总。两个都能用，下面统一用 `fact_order_item` 写法（可与商品维度正确相乘）。
4. **有效销售**：已取消/退款订单金额仍保留，算真实成交务必 `CALCULATE(..., 'fact_order'[status]="已完成")`。

---

## 一、基础度量值（先建这些）

```dax
-- 1. 销售额（含作废订单，演示用）
总销售额 = SUM('fact_order_item'[line_amount])

-- 2. 有效销售额（仅已完成，正式分析用这个）
有效销售额 = 
CALCULATE(
    SUM('fact_order_item'[line_amount]),
    'fact_order'[status] = "已完成"
)

-- 3. 总利润（有效）
有效利润 = 
CALCULATE(
    SUM('fact_order_item'[line_profit]),
    'fact_order'[status] = "已完成"
)

-- 4. 销售数量
销售数量 = SUM('fact_order_item'[quantity])

-- 5. 客单价（有效订单）
客单价 = 
DIVIDE(
    [有效销售额],
    CALCULATE(DISTINCTCOUNT('fact_order'[order_id]), 'fact_order'[status]="已完成")
)

-- 6. 毛利率（安全除）
毛利率 = DIVIDE([有效利润], [有效销售额])

-- 7. 订单数
有效订单数 = 
CALCULATE(DISTINCTCOUNT('fact_order'[order_id]), 'fact_order'[status]="已完成")

-- 8. 平均每件利润
单件利润 = DIVIDE([有效利润], [销售数量])
```

> 为什么用 `DIVIDE` 而非 `/`：分母为 0 时 `DIVIDE` 返回空白而非报错，度量值更稳。

---

## 二、时间智能（先标记日期表）

```dax
-- 9. 年初至今销售额（YTD）
销售额YTD = 
CALCULATE([有效销售额], DATESYTD('dim_date'[date_key]))

-- 10. 月度累计（跨年归零）
销售额MTD = 
CALCULATE([有效销售额], DATESMTD('dim_date'[date_key]))

-- 11. 去年同期（YoY 基数）
销售额去年同期 = 
CALCULATE([有效销售额], SAMEPERIODLASTYEAR('dim_date'[date_key]))

-- 12. 同比增长率
销售额同比% = 
VAR 今年 = [有效销售额]
VAR 去年 = [销售额去年同期]
RETURN DIVIDE(今年 - 去年, 去年)

-- 13. 上月销售额（环比基数）
销售额上月 = 
CALCULATE([有效销售额], DATEADD('dim_date'[date_key], -1, MONTH))

-- 14. 环比增长率
销售额环比% = 
VAR 本月 = [有效销售额]
VAR 上月 = [销售额上月]
RETURN DIVIDE(本月 - 上月, 上月)

-- 15. 滚动 3 个月销售额（移动平均用原始值）
销售额滚动3月 = 
CALCULATE([有效销售额], DATESINPERIOD('dim_date'[date_key], MAX('dim_date'[date_key]), -3, MONTH))
```

> 时间智能依赖连续日期表。`dim_date` 已覆盖 2023-01-01~2025-12-31 无断档，可直接用。

---

## 三、排名 / 累计 / 占比（窗口函数思路的 DAX 版）

```dax
-- 16. 各地区销售额排名（在「矩阵」按 province_name 显示时生效）
地区销售排名 = 
RANKX(
    ALL('dim_region'[province_name]),
    [有效销售额],
    , DESC, DENSE
)

-- 17. 各地区销售额占全网比
地区销售占比 = 
DIVIDE(
    [有效销售额],
    CALCULATE([有效销售额], ALL('dim_region'))
)

-- 18. 各品类毛利率排名
品类利润排名 = 
RANKX(
    ALL('dim_product'[category]),
    [有效利润],
    , DESC, DENSE
)

-- 19. 销售额 running total（按日期累计，需放在按 date 排序的视觉对象）
销售额累计 = 
CALCULATE(
    [有效销售额],
    FILTER(
        ALL('dim_date'[date_key]),
        'dim_date'[date_key] <= MAX('dim_date'[date_key])
    )
)

-- 20. 客户累计消费排名（RFM 前置）
客户消费额 = 
CALCULATE([有效销售额], ALLEXCEPT('fact_order', 'fact_order'[customer_id]))
```

---

## 四、TOP N 与客户分层

```dax
-- 21. TOP 10 客户销售额表（建表用）
TOP10客户 = 
TOPN(
    10,
    SUMMARIZE('fact_order', 'dim_customer'[customer_name], "销售额", [有效销售额]),
    [有效销售额], DESC
)

-- 22. 钻石客户销售额（切片器替代写法）
钻石客户销售额 = 
CALCULATE([有效销售额], 'dim_customer'[tier] = "钻石")

-- 23. 会员等级销售占比（按 tier）
等级销售占比 = 
DIVIDE(
    [有效销售额],
    CALCULATE([有效销售额], ALL('dim_customer'[tier]))
)

-- 24. 高客单客户筛选（客单价 > 全网上四分位，用 RANKX 近似）
高价值客户 = 
VAR 阈值 = PERCENTILEX.INC(
    VALUES('fact_order'[customer_id]),
    [有效销售额], 0.75
)
RETURN IF([有效销售额] >= 阈值, 1, 0)
```

---

## 五、DAX 查询（EVALUATE，可直接跑验证）

```dax
-- Q1. 各省份有效销售额 + 排名（验证度量值 2/16）
EVALUATE
SUMMARIZECOLUMNS(
    'dim_region'[province_name],
    "有效销售额", [有效销售额],
    "地区排名", [地区销售排名]
)
ORDER BY [有效销售额] DESC

-- Q2. 各品类毛利率（验证度量值 3/6）
EVALUATE
SUMMARIZECOLUMNS(
    'dim_product'[category],
    "有效销售额", [有效销售额],
    "有效利润", [有效利润],
    "毛利率", [毛利率]
)
ORDER BY [毛利率] DESC

-- Q3. 2024 年月度销售趋势（验证时间智能）
EVALUATE
FILTER(
    SUMMARIZECOLUMNS(
        'dim_date'[year], 'dim_date'[month], 'dim_date'[month_name],
        "有效销售额", [有效销售额]
    ),
    'dim_date'[year] = 2024
)
ORDER BY 'dim_date'[month]

-- Q4. 各会员等级销售占比
EVALUATE
SUMMARIZECOLUMNS(
    'dim_customer'[tier],
    "有效销售额", [有效销售额],
    "等级占比", [等级销售占比]
)
ORDER BY [有效销售额] DESC
```

---

## 六、常见坑

| 现象         | 原因 / 解决                                                                        |
| ---------- | ------------------------------------------------------------------------------ |
| 时间智能返回空白   | `dim_date` 没标记为日期表，或关系方向反了                                                     |
| 销售额翻倍      | 把 `fact_order` 和 `fact_order_item` 同时按订单粒度求和（两表都算了一遍）。金额只从 `fact_order_item` 取 |
| 已取消订单混进来   | 没加 `status="已完成"` 过滤                                                           |
| RANKX 全是 1 | 没用 `ALL(维度列)` 指定排名范围                                                           |
| 环比首月报错     | 首月无上月数据，`DIVIDE` 已兜底返回空白                                                       |
| 占比合计≠100%  | 用了 `ALL` 但被切片器截断了，检查筛选上下文                                                      |

---

## 七、与 SQL 练习对照（同一问题两种写法）

| 学习目标    | SQL（窗口函数）                                                  | DAX（度量值）                     |
| ------- | ---------------------------------------------------------- | ---------------------------- |
| 各地区销售排名 | `RANK() OVER (PARTITION BY ... ORDER BY SUM(amount) DESC)` | `RANKX(ALL(省份), [有效销售额])`    |
| 月度累计    | `SUM() OVER (ORDER BY month ROWS UNBOUNDED PRECEDING)`     | `销售额累计`（CALCULATE+FILTER）    |
| 同比      | `LAG(SUM(amount),12) OVER (...)`                           | `SAMEPERIODLASTYEAR`         |
| 品类毛利率   | `SUM(profit)/SUM(amount) GROUP BY category`                | `DIVIDE([有效利润],[有效销售额])` 按品类 |
| TOP N   | `ROW_NUMBER()` + 子查询                                       | `TOPN(10, SUMMARIZE(...))`   |

> 练法建议：先在 SQL 里用窗口函数得出结果（看数字对不对），再在 Power BI 里用 DAX 复现，两边对拍，理解最快。

