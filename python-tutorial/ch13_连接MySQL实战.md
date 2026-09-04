# ch13 连接 MySQL 实战：pandas × SQL 对拍

> 这一章把 pandas 接到你学 SQL 时建的 `study_powerbi_demodata` 库，用 Python 跑出**和 SQL 教程完全一致的数字**。你会亲眼看到：SQL 的 `GROUP BY` 和 pandas 的 `groupby` 是同一件事，结论完全相同。FDE 的真实工作就是这样——从客户数据库拉数，用 Python 自由分析。

---

## 0. ⚠️ 前置：先启动 MySQL

> 本机 MySQL 装在 **phpStudy** 里（`D:\XPMB\phpstudy_pro\Extensions\MySQL8.0.12\`），**不是 Windows 服务**，重启电脑后不会自动启动。连不上时先手动起：

```powershell
cd "D:\XPMB\phpstudy_pro\Extensions\MySQL8.0.12\bin"
.\mysqld.exe --defaults-file="D:\XPMB\phpstudy_pro\Extensions\MySQL8.0.12\my.ini" --console
```

> 等出现 `ready for connections ... port: 3306` 就可以跑了。连接参数：**`127.0.0.1:3306`，用户 `root`，密码 `root`，库 `study_powerbi_demodata`**。

---

## 1. 连接与读取整张表

```python
import pandas as pd
import pymysql

conn = pymysql.connect(
    host="127.0.0.1", port=3306, user="root", password="root",
    database="study_powerbi_demodata", charset="utf8mb4",
)
tables = pd.read_sql("SHOW TABLES", conn)
print("表:", [t for t in tables.iloc[:, 0]])

counts = {}
for t in tables.iloc[:, 0]:
    counts[t] = pd.read_sql(f"SELECT COUNT(*) c FROM `{t}`", conn).iloc[0, 0]
print("行数:", counts, "| 合计:", sum(counts.values()))
```

**预期输出：**

```
表: ['dim_customer', 'dim_date', 'dim_product', 'dim_region', 'fact_order', 'fact_order_item']
行数: {'dim_customer': 500, 'dim_date': 1096, 'dim_product': 200, 'dim_region': 10, 'fact_order': 3529, 'fact_order_item': 8445} | 合计: 13780
```

> 6 张表、合计 **13,780 行**。`pd.read_sql("SQL", conn)` 直接把查询结果变成 DataFrame——这就是 pandas 连数据库的标准入口。

---

## 2. 把多张表拉进内存并关联

```python
df_order  = pd.read_sql("SELECT * FROM fact_order", conn)
df_item   = pd.read_sql("SELECT * FROM fact_order_item", conn)
df_cust   = pd.read_sql("SELECT * FROM dim_customer", conn)
df_prod   = pd.read_sql("SELECT * FROM dim_product", conn)
df_region = pd.read_sql("SELECT * FROM dim_region", conn)

print("fact_order:", df_order.shape, "| 列:", df_order.columns.tolist())
print("fact_order 前3:\n", df_order.head(3))
print("status 分布:\n", df_order["status"].value_counts())
```

**预期输出：**

```
fact_order: (3529, 8) | 列: ['order_id', 'customer_id', 'region_id', 'order_date', 'status', 'payment_method', 'order_amount', 'order_profit']
status 分布:
 status
已完成    2366
已取消     591
退款       572
Name: count, dtype: int64
```

> `fact_order` 有 **3,529 单**，其中「已完成」2,366 单，其余 1,163 单是取消/退款——**这就是 SQL 教程反复强调的「有效销售必须 `status='已完成'`」**。

---

## 3. 合并 + 有效口径（与 SQL 教程对拍）

```python
merged = (df_item
    .merge(df_order[["order_id", "customer_id", "region_id", "status", "order_date"]],
           on="order_id", how="inner")
    .merge(df_prod[["product_id", "category"]], on="product_id", how="left")
    .merge(df_region[["region_id", "province_name"]], on="region_id", how="left")
    .merge(df_cust[["customer_id", "customer_name", "tier"]], on="customer_id", how="left"))

print("合并后行数:", len(merged))
eff = merged[merged["status"] == "已完成"]          # ← 有效口径，和 SQL 教程一致

print("有效销售额:", round(eff["line_amount"].sum(), 2))
print("有效利润:", round(eff["line_profit"].sum(), 2))
print("有效销量:", int(eff["quantity"].sum()))
print("有效订单数(DISTINCT):", eff["order_id"].nunique())
print("客单价:", round(eff["line_amount"].sum() / eff["order_id"].nunique(), 2))
print("毛利率:", round(eff["line_profit"].sum() / eff["line_amount"].sum() * 100, 2), "%")
```

**预期输出：**

```
合并后行数: 8445
有效销售额: 7195492.73
有效利润: 1706864.78
有效销量: 8626
有效订单数(DISTINCT): 2366
客单价: 3041.21
毛利率: 23.72 %
```

> **和 SQL 教程数字 100% 一致**：7,195,492.73 / 1,706,864.78 / 客单价 3,041.21 / 毛利率 23.72%。
> 这里用 `line_amount`（明细行金额）求和、用 `nunique()` 去重订单数——对应 SQL 教程「DAX 用 `line_amount`、SQL 用 `order_amount`」的口径分工。

---

## 4. 品类毛利率（成交口径）

```python
cat = (eff.groupby("category")
          .agg(销售额=("line_amount", "sum"), 利润=("line_profit", "sum"), 销量=("quantity", "sum"))
          .assign(毛利率=lambda d: (d["利润"] / d["销售额"] * 100).round(2),
                  销售额=lambda d: d["销售额"].round(2))
          .sort_values("毛利率"))
print(cat)
```

**预期输出：**

```
              销售额       利润  销量  毛利率
category
数码      2612383.09   30291.28  1484    1.16
食品       441341.24   95995.03  2229   21.75
家居      1408258.89  383334.76  1552   27.22
服饰      1351789.04  513684.38  1372   38.00
美妆      1381720.47  683559.33  1989   49.47
```

> 数码毛利率仅 1.16%（走量薄利），美妆 49.47%（高毛利）——和 SQL / Power BI 教程完全一致。

---

## 5. 省份 TOP5 与客户 TOP5

```python
prov = (eff.groupby("province_name")
           .agg(销售额=("line_amount", "sum"), 订单数=("order_id", "nunique"))
           .assign(销售额=lambda d: d["销售额"].round(2))
           .sort_values("销售额", ascending=False))
print("省份 TOP5:\n", prov.head(5))

cust = (eff.groupby(["customer_id", "customer_name", "tier"])
           .agg(消费额=("line_amount", "sum"), 订单数=("order_id", "nunique"))
           .reset_index().assign(消费额=lambda d: d["消费额"].round(2))
           .sort_values("消费额", ascending=False))
print("\n客户 TOP5:\n", cust.head(5).to_string(index=False))
```

**预期输出：**

```
省份 TOP5:
                   销售额  订单数
province_name
广东           1078152.70     352
浙江            849660.63     277
上海            816614.17     265
江苏            800322.96     255
北京            761942.54     267

客户 TOP5:
 customer_id customer_name tier   消费额  订单数
         119          梁诗 钻石 70022.89      18
          96        唐宇伟 钻石 67890.55      21
         225        马晨博 钻石 66012.90      19
         226          吴涛 钻石 65767.42      18
         439        彭艳鑫 钻石 61699.01      19
```

> 广东 107.8 万居首，梁诗 7 万居首（全钻石客户）——和 SQL 教程完全相同。

---

## 6. 客户等级分布 + 月度趋势 + 透视表

```python
valid = df_order[df_order["status"] == "已完成"]
tier = (df_cust
    .merge(valid.groupby("customer_id")["order_amount"].agg(["count", "mean"]),
           left_on="customer_id", right_index=True, how="left")
    .groupby("tier").agg(人数=("customer_id", "count")))
print("客户等级:\n", tier)

eff2 = eff.copy()
eff2["年月"] = pd.to_datetime(eff2["order_date"]).dt.to_period("M").astype(str)
mon = eff2.groupby("年月").agg(销售额=("line_amount", "sum"), 订单数=("order_id", "nunique"))
mon["销售额"] = mon["销售额"].round(2)
mon["环比%"] = (mon["销售额"].pct_change() * 100).round(2)
print("\n月度趋势(前6):\n", mon.head(6))
print("2024 全年:", round(mon.loc["2024-01":"2024-12", "销售额"].sum(), 2))
print("2025 全年:", round(mon.loc["2025-01":"2025-12", "销售额"].sum(), 2))

eff2["年"] = pd.to_datetime(eff2["order_date"]).dt.year
pt = eff2.pivot_table(index="category", columns="年", values="line_amount",
                      aggfunc="sum", margins=True, margins_name="合计").round(2)
print("\npivot_table 品类 x 年:\n", pt)
```

**预期输出：**

```
客户等级:
      人数
tier
普通   241
金卡    83
钻石    27
银卡   149

月度趋势(前6):
            销售额  订单数  环比%
年月
2023-01  124739.44      40    NaN
2023-02   75242.07      21 -39.68
2023-03   99328.64      33  32.01
2023-04  117552.47      43  18.35
2023-05  156405.58      49  33.05
2023-06  260133.29      87  66.32
2024 全年: 2535109.95
2025 全年: 2319981.19

pivot_table 品类 x 年:
年              2023        2024        2025        合计
category
家居       458751.19   500895.52   448612.18  1408258.89
数码       801526.32   953723.38   857133.39  2612383.09
服饰       469994.86   446719.75   435074.43  1351789.04
美妆       466829.31   475136.60   439754.56  1381720.47
食品       143299.91   158634.70   139406.63   441341.24
合计      2340401.59  2535109.95  2319981.19  7195492.73
```

> `pivot_table` 就是 SQL 的「交叉表」、`pct_change()` 算环比、`.loc["2024-01":"2024-12"]` 做时间切片——这些在 SQL 里要写窗口函数 / 子查询，pandas 一行搞定。

---

## 7. 窗口函数等价（pandas 版 TOP N + 累计占比）

```python
cust_rank = (eff.groupby("customer_name")["line_amount"].sum().round(2)
                .sort_values(ascending=False).reset_index())
cust_rank["排名"] = cust_rank["line_amount"].rank(ascending=False, method="min").astype(int)
cust_rank["累计占比%"] = (cust_rank["line_amount"].cumsum() / cust_rank["line_amount"].sum() * 100).round(2)
print("窗口函数等价(pandas):\n", cust_rank.head(5).to_string(index=False))
conn.close()
```

**预期输出：**

```
窗口函数等价(pandas):
customer_name  line_amount  排名  累计占比%
         梁诗     70022.89     1       0.97
       唐宇伟     67890.55     2       1.92
       马晨博     66012.90     3       2.83
         吴涛     65767.42     4       3.75
       彭艳鑫     61699.01     5       4.61
```

> `.rank()` = SQL 的 `RANK()`，`.cumsum()` = 窗口函数 `SUM() OVER (ORDER BY)`。pandas 和 SQL 窗口函数思路完全对应。

---

## 小结

- `pymysql.connect()` + `pd.read_sql()` 是 pandas 连 MySQL 的标准姿势
- 多表关联用 `merge(how=)`，等价于 SQL JOIN
- 有效口径 `status='已完成'` 和 SQL 教程一致，数字完全对拍
- `groupby` / `pivot_table` / `rank` / `cumsum` 是 SQL 聚合/窗口函数的内存版

---

## 练习

### 练习 1：连库查表（考：read_sql）
**题目**：连上库，打印 `dim_product` 的行数和前 3 行。
<details><summary>答案与解析</summary>

```python
import pandas as pd, pymysql
conn = pymysql.connect(host="127.0.0.1", port=3306, user="root", password="root",
                       database="study_powerbi_demodata", charset="utf8mb4")
df = pd.read_sql("SELECT * FROM dim_product", conn)
print(df.shape, df.head(3))
conn.close()
# (200, 列数)  |  前3行产品
```
</details>

### 练习 2：有效销售额（考：筛选 + 求和）
**题目**：从 `fact_order` 取「已完成」订单，求 `order_amount` 合计（应等于 7,195,492.73 附近）。
<details><summary>答案与解析</summary>

```python
df = pd.read_sql("SELECT * FROM fact_order", conn)
valid = df[df["status"] == "已完成"]
print(round(valid["order_amount"].sum(), 2))   # 7195492.73
```
**解析**：`status='已完成'` 是统一有效口径，SQL 教程也用它。
</details>

### 练习 3：省份 TOP3（考：groupby + nunique）
**题目**：合并明细与地区表，求有效订单「销售额」TOP3 的省份。
<details><summary>答案与解析</summary>

```python
# 见正文第5节，prov.head(3) 即 广东/浙江/上海
prov = (eff.groupby("province_name")["line_amount"].sum()
           .sort_values(ascending=False))
print(prov.head(3))
# 广东 1078152.70 / 浙江 849660.63 / 上海 816614.17
```
</details>

### 练习 4：环比（考：pct_change）
**题目**：算有效销售「按月销售额」的环比增长率（前两个月）。
<details><summary>答案与解析</summary>

```python
mon = eff2.groupby("年月")["line_amount"].sum()
print((mon.pct_change() * 100).round(2).head(3))
# 2023-01 NaN / 2023-02 -39.68 / 2023-03 32.01
```
</details>

### 练习 5：客户排名（考：rank + cumsum）
**题目**：按客户消费额排名，并算累计占比，取前 5。
<details><summary>答案与解析</summary>

```python
# 见正文第7节
cust_rank = (eff.groupby("customer_name")["line_amount"].sum()
                .sort_values(ascending=False).reset_index())
cust_rank["排名"] = cust_rank["line_amount"].rank(ascending=False, method="min").astype(int)
cust_rank["累计占比%"] = (cust_rank["line_amount"].cumsum()
                          / cust_rank["line_amount"].sum() * 100).round(2)
print(cust_rank.head(5))
```
</details>

---

## 下一步

数据拉出来、算完了，最后一步是**让人看懂**——画图 + 导出 Excel 报告。下一章用 matplotlib 出销售看板，用 `ExcelWriter` 导出多 sheet 报表。

→ [ch14 可视化导出与工程化](./ch14_可视化导出与工程化.md)
