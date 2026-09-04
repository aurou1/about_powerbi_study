# ch12 pandas 数据分析入门

> 前面 11 章打好了 Python 底子，从这一章开始进入**数据科学实战**——pandas。它和你已经学的 SQL 是「同一件事的两种写法」：SQL 在数据库里 `SELECT ... GROUP BY`，pandas 在内存里 `df.groupby()`。FDE 日常就是把客户数据拉进 pandas，清洗、聚合、出结论。本章所有基础示例都用本地小数据，**不依赖数据库**；连真实库在 ch13。

---

## 学习目标

- 理解 `Series`（一列）和 `DataFrame`（表格）
- 掌握筛选、排序、`groupby` 聚合、`merge` 多表关联
- 会处理缺失值（`fillna` / `dropna`）、字符串列、日期列
- 知道 `apply` vs **向量化**的性能差距（这是新手最大性能坑）

---

## 0. 准备：中文对齐显示

```python
import pandas as pd
pd.set_option("display.unicode.east_asian_width", True)   # 中文对齐
print("pandas", pd.__version__)
```

> pandas 版本会随环境变（本机 3.0.5）。**输出格式可能有细微差别，但数字一定一致**。

---

## 1. `Series`：带标签的一维数组（一列）

```python
s = pd.Series([1200, 3400, 800], index=["数码", "食品", "家居"], name="销售额")
print(s)
print("索引:", s.index.tolist(), "| 值:", s.values.tolist(), "| dtype:", s.dtype)
print("布尔筛选:\n", s[s > 1000])          # 只留 >1000 的
print("describe:\n", s.describe().round(2))
```

**预期输出：**

```
数码    1200
食品    3400
家居     800
Name: 销售额, dtype: int64
索引: ['数码', '食品', '家居'] | 值: [1200, 3400, 800] | dtype: int64
布尔筛选:
 数码    1200
食品    3400
Name: 销售额, dtype: int64
describe:
 count     3.0
mean    1800.0
std     1400.0
min      800.0
25%     1000.0
50%     1200.0
75%     2300.0
max     3400.0
Name: 销售额, dtype: float64
```

> `Series` = 值 + 索引（标签）+ 名字。布尔筛选 `s[s > 1000]` 是 pandas 最高频操作之一。`describe()` 一键出统计（计数/均值/标准差/分位）。

---

## 2. `DataFrame`：二维表格（多列）

```python
df = pd.DataFrame({
    "订单号": ["O001", "O002", "O003", "O004"],
    "品类": ["数码", "食品", "数码", "美妆"],
    "数量": [2, 5, 1, 3],
    "单价": [1200.0, 68.0, 3400.0, 199.0],
})
df["金额"] = df["数量"] * df["单价"]          # 新增一列（向量化计算，整列同时算）
print(df)
print("shape:", df.shape, "| columns:", df.columns.tolist())
print("dtypes:\n", df.dtypes)
print("info 内存:", df.memory_usage(deep=True).sum(), "字节")
print("describe 数值:\n", df[["数量", "单价", "金额"]].describe().round(2))
```

**预期输出：**

```
   订单号  品类  数量    单价    金额
0   O001  数码     2  1200.0  2400.0
1   O002  食品     5    68.0   340.0
2   O003  数码     1  3400.0  3400.0
3   O004  美妆     3   199.0   597.0
shape: (4, 5) | columns: ['订单号', '品类', '数量', '单价', '金额']
dtypes:
 订单号        str
品类          str
数量        int64
单价      float64
金额      float64
dtype: object
info 内存: 720 字节
describe 数值:
        数量     单价     金额
count  4.00     4.00     4.00
mean   2.75  1216.75  1684.25
std    1.71  1540.81  1465.74
min    1.00    68.00   340.00
25%    1.75   166.25   532.75
50%    2.50   699.50  1498.50
75%    3.50  1750.00  2650.00
max    5.00  3400.00  3400.00
```

> - `df["金额"] = df["数量"] * df["单价"]` 是**向量化**：整列一次性算完，不用写循环。
> - `shape` 是 `(行, 列)`；`dtypes` 看每列类型（`str` / `int64` / `float64`）。

---

## 3. 取数：loc / iloc / 条件筛选

```python
print("loc:", df.loc[0, "品类"], "| iloc:", df.iloc[0, 1])     # 按标签 vs 按位置
print("条件筛选:\n", df[df["金额"] > 500][["订单号", "金额"]])
print("多条件:\n", df[(df["品类"] == "数码") & (df["数量"] >= 2)])   # & 且，每个条件加 ()
print("isin:\n", df[df["品类"].isin(["数码", "美妆"])]["订单号"].tolist())
print("query:\n", df.query("金额 > 500 and 数量 >= 2")[["订单号"]].values.ravel().tolist())
```

**预期输出：**

```
loc: 数码 | iloc: 数码
条件筛选:
   订单号    金额
0   O001  2400.0
2   O003  3400.0
3   O004   597.0
多条件:
   订单号  品类  数量    单价    金额
0   O001  数码     2  1200.0  2400.0
2   O003  数码     1  3400.0  3400.0
isin:
 ['O001', 'O003', 'O004']
query:
 ['O001', 'O004']
```

> - `loc[行标签, 列名]` vs `iloc[行号, 列号]`——**新手最容易混，记住 loc 按名字、iloc 按数字**
> - 多条件用 `&`（且）`|`（或），**每个条件必须套括号**（运算符优先级坑）
> - `query("SQL风格字符串")` 写起来像 SQL，适合临时探索

---

## 4. `groupby`：分组聚合（等价于 SQL GROUP BY）

```python
g = df.groupby("品类").agg(订单数=("订单号", "count"), 数量=("数量", "sum"), 金额=("金额", "sum"))
print("groupby:\n", g)
print("sort_values:\n", g.sort_values("金额", ascending=False))
print("分组累计:\n", df.groupby("品类")["金额"].sum().sort_values(ascending=False))
print("transform 占比:\n", df.assign(占比=(df["金额"] / df["金额"].sum() * 100).round(2)))
```

**预期输出：**

```
groupby:
       订单数  数量    金额  毛利率
品类
数码       2     3  5800.0     0
美妆       1     3   597.0     0
食品       1     5   340.0     0
sort_values:
       订单数  数量    金额  毛利率
品类
数码       2     3  5800.0     0
美妆       1     3   597.0     0
食品       1     5   340.0     0
分组累计:
 品类
数码    5800.0
美妆     597.0
食品     340.0
Name: 金额, dtype: float64
transform 占比:
   订单号  品类  数量    单价    金额   占比
0   O001  数码     2  1200.0  2400.0  35.62
1   O002  食品     5    68.0   340.0   5.05
2   O003  数码     1  3400.0  3400.0  50.47
3   O004  美妆     3   199.0   597.0   8.86
```

> `groupby("品类").agg(...)` 就是 SQL 的 `GROUP BY 品类`。`transform` 能「在不聚合的前提下给每行算占比」，是 pandas 比 SQL 灵活的地方。

---

## 5. `merge`：多表关联（等价于 SQL JOIN）

```python
left = pd.DataFrame({"code": ["A", "B", "C"], "name": ["球", "镜", "拍"]})
right = pd.DataFrame({"code": ["B", "C", "D"], "price": [10, 20, 30]})

print("merge inner:\n", left.merge(right, on="code", how="inner"))
print("left:\n", left.merge(right, on="code", how="left"))
print("outer:\n", left.merge(right, on="code", how="outer"))
print("indicator:\n", left.merge(right, on="code", how="outer", indicator=True))
```

**预期输出：**

```
merge inner:
   code name  price
0    B   镜     10
1    C   拍     20
left:
   code name  price
0    A   球    NaN
1    B   镜   10.0
2    C   拍   20.0
outer:
   code name  price
0    A   球    NaN
1    B   镜   10.0
2    C   拍   20.0
3    D  NaN   30.0
indicator:
   code name  price      _merge
0    A   球    NaN   left_only
1    B   镜   10.0        both
2    C   拍   20.0        both
3    D  NaN   30.0  right_only
```

> `how="inner/left/outer"` 对应 SQL 的 `INNER/LEFT/FULL JOIN`。`indicator=True` 会加一列 `_merge` 标明每行来自哪边——**排查「数据对不上」的神器**。

---

## 6. 缺失值处理

```python
nan_df = pd.DataFrame({"a": [1, None, 3], "b": [None, 2, 3]})
print("缺失值:", nan_df.isna().sum().to_dict())
print("fillna:\n", nan_df.fillna(0))
print("dropna:\n", nan_df.dropna())
print("ffill:\n", nan_df.ffill())            # 用上一个有效值填充
```

**预期输出：**

```
缺失值: {'a': 1, 'b': 1}
fillna:
      a    b
0  1.0  0.0
1  0.0  2.0
2  3.0  3.0
dropna:
      a    b
2  3.0  3.0
ffill:
      a    b
0  1.0  NaN
1  1.0  2.0
2  3.0  3.0
```

> 真实数据永远有空值。`fillna`（填）、`dropna`（删）、`ffill`（向前填）三选一，看业务能不能容忍。

---

## 7. 字符串列与日期列

```python
s2 = pd.Series([" ST-BD-42 ", "YG-01", " ST-BD-60"])
print("字符串方法:", s2.str.strip().str.upper().tolist())
print("contains:", s2.str.contains("BD").tolist())
print("split:", s2.str.strip().str.split("-").tolist())

idx = pd.date_range("2026-01-01", periods=5, freq="D")
ts = pd.Series([10, 20, 30, 40, 50], index=idx)
print("resample 周:\n", ts.resample("W").sum())
print("rolling(3):\n", ts.rolling(3).mean().round(2).tolist())
print("cumsum:", ts.cumsum().tolist())
print("pct_change:", ts.pct_change().round(3).tolist())
```

**预期输出：**

```
字符串方法: ['ST-BD-42', 'YG-01', 'ST-BD-60']
contains: [True, False, True]
split: [['ST', 'BD', '42'], ['YG', '01'], ['ST', 'BD', '60']]
resample 周:
 2026-01-04    100
 2026-01-11     50
Freq: W-SUN, dtype: int64
rolling(3):
 [nan, nan, 20.0, 30.0, 40.0]
cumsum: [10, 30, 60, 100, 150]
pct_change: [nan, 1.0, 0.5, 0.333, 0.25]
shift(1): [nan, 10.0, 20.0, 30.0, 40.0]
```

> - `str.xxx` 是对整列字符串批量操作（清洗料号、提取后缀必备）
> - 日期列用 `resample`（重采样到周/月）、`rolling`（滚动平均，算趋势）、`pct_change`（环比）、`cumsum`（累计）——和 ch13 月度趋势一一对应

---

## 8. ⚠️ 性能天坑：`apply` vs 向量化

```python
import time
big = pd.DataFrame({"x": range(200000)})

t0 = time.perf_counter(); _ = big["x"].apply(lambda v: v * 2); t_apply = time.perf_counter() - t0
t0 = time.perf_counter(); _ = big["x"] * 2; t_vec = time.perf_counter() - t0
print(f"apply  {t_apply:.4f}s")
print(f"向量化 {t_vec:.4f}s  → 快 {t_apply/max(t_vec,1e-9):.0f} 倍")
```

**预期输出（机器相关，倍率稳定）：**

```
apply  0.0685s
向量化 0.0008s  → 快 84 倍
```

> **铁律：能向量化就别用 `apply`**。`apply(lambda)` 是逐行 Python 循环，慢几十上百倍。先看有没有列级运算（`df["x"] * 2`、`df["a"] + df["b"]`），没有再考虑 `apply`，最后才考虑 `iterrows`。

---

## 小结

| 操作 | pandas | 等价 SQL |
|---|---|---|
| 一列 | `Series` | 单列 |
| 表格 | `DataFrame` | 表 |
| 筛选 | `df[条件]` / `query` | `WHERE` |
| 分组聚合 | `groupby().agg()` | `GROUP BY` |
| 多表关联 | `merge(how=)` | `JOIN` |
| 排序 | `sort_values` | `ORDER BY` |
| 缺失值 | `fillna`/`dropna` | `COALESCE`/`WHERE 非空` |
| 重采样 | `resample` | 时间分组 |

> 看到这行（`df.groupby(...).agg(...)`）就想到 SQL 的 `GROUP BY ...`——**pandas 是内存版 SQL，思路完全互通**。下一章连真实 MySQL 库，跑出和 SQL 教程一致的数字。

---

## 练习

### 练习 1：建 DataFrame 并新增列（考：向量化）
**题目**：建 `df`（姓名、语文、数学），新增「总分」列 = 语文+数学，打印。
<details><summary>答案与解析</summary>

```python
import pandas as pd
df = pd.DataFrame({"姓名": ["甲","乙"], "语文": [88,92], "数学": [95,87]})
df["总分"] = df["语文"] + df["数学"]
print(df)
#    姓名  语文  数学  总分
# 0   甲   88   95  183
# 1   乙   92   87  179
```
**解析**：新增列直接用列级运算，向量化一次性算完。
</details>

### 练习 2：条件筛选（考：布尔索引）
**题目**：从 `df` 中选出「数学 > 90」的行，只显示姓名和数学。
<details><summary>答案与解析</summary>

```python
print(df[df["数学"] > 90][["姓名","数学"]])
#    姓名  数学
# 0   甲   95
```
</details>

### 练习 3：groupby（考：分组聚合）
**题目**：`df` 按「姓名首字」没必要，请按给定 `sales` 表（品类、金额）算各品类金额合计与笔数。
<details><summary>答案与解析</summary>

```python
sales = pd.DataFrame({"品类":["数码","数码","食品"], "金额":[1200,3400,340]})
print(sales.groupby("品类").agg(笔数=("金额","count"), 合计=("金额","sum")))
#      笔数    合计
# 品类
# 数码    2  4600
# 食品    1   340
```
</details>

### 练习 4：merge（考：关联）
**题目**：`a`（id, name）、`b`（id, score），做 inner join 取 name 和 score。
<details><summary>答案与解析</summary>

```python
a = pd.DataFrame({"id":[1,2], "name":["甲","乙"]})
b = pd.DataFrame({"id":[1,3], "score":[88,90]})
print(a.merge(b, on="id", how="inner"))
#    id name  score
# 0   1   甲     88
```
**解析**：inner 只保留两边都有的 id=1。
</details>

### 练习 5：为什么别用 apply（考：性能意识）
**题目**：对 20 万行 `df["x"]`，分别用 `apply(lambda v: v*2)` 和 `df["x"]*2` 计算，哪个快？为什么？
<details><summary>答案与解析</summary>

```python
big = pd.DataFrame({"x": range(200000)})
%timeit big["x"].apply(lambda v: v*2)     # 慢
%timeit big["x"] * 2                        # 快几十倍
```
**解析**：`apply` 是逐行 Python 循环；向量化是 C 层批量运算。能用列运算就别用 `apply`。
</details>

---

## 下一步

pandas 基础会了，现在连上你学 SQL 时建的 `study_powerbi_demodata` 库，用 pandas 跑出**和 SQL 教程完全一致的数字**——这就是「同一份数据，两种武器」的实战。

→ [ch13 连接 MySQL 实战](./ch13_连接MySQL实战.md)
