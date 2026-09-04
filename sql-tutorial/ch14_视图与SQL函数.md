# ch14 视图与 SQL 常用函数

> 学习目标：学会用**视图**把"天天要跑的复杂查询"封装成一张虚拟表，从此报表口径只维护一处；再系统过一遍 SQL **字符串 / 日期 / 数值 / 条件 / 正则**五类函数，知道"哪个场景用哪个"。
>
> 说明：视图建在独立练习库，跨库引用教学库，练完删除——**不污染 `study_powerbi_demodata`**。

---

## 一、为什么需要视图：把"口径"存下来

你每次跑「广东已完成订单销售额」都要写一遍：

```sql
SELECT ROUND(SUM(o.order_amount), 2)
FROM fact_order o
JOIN dim_region r ON o.region_id = r.region_id
WHERE r.province_name = '广东' AND o.status = '已完成';
```

> 问题：这段 SQL 复制到 5 张报表里 → 哪次口径改了（比如"广东要含海南"），得改 5 处，漏一处报表数字就打架。**视图 = 把这段 SQL 存成一个"命名查询"，以后直接 `FROM 视图名`。**

```
视图原理（虚拟表，不存数据）:

  你写:  SELECT ... FROM v_guangdong_sales
                      │
                      ▼
  MySQL 背后自动替换成:  SELECT ... FROM (你存的那段复杂 SELECT) AS v
                      │
                      ▼
  视图本身不占存储，每次查询都实时执行底层 SELECT
```

---

## 二、创建视图（跟着做）

```sql
USE study_sql_ddl_practice;        -- 练习库，见 ch13

-- 视图1：把「有效订单」口径封装（以后不用每次写 status='已完成'）
CREATE VIEW v_valid_order AS
SELECT order_id, customer_id, region_id, order_date,
       order_amount, order_profit
FROM study_powerbi_demodata.fact_order
WHERE status = '已完成';

-- 用起来：跟查表一模一样
SELECT COUNT(*) AS 单数, ROUND(SUM(order_amount), 2) AS 销售额
FROM v_valid_order;
```
**实跑结果（视图行数与金额 = 全库口径，和 ch01 一致）：**
```
单数   销售额
2366   7195492.73
```
> 视图查询和直接查底层表**结果完全一样**——因为视图就是"SQL 宏"。检验视图写没写对：`SELECT * FROM 视图 LIMIT 5` 扫一眼。

```sql
-- 视图2：JOIN 也可以封进视图（多表查询的"打包"）
CREATE VIEW v_guangdong_sales AS
SELECT o.order_id, o.order_date, o.order_amount
FROM study_powerbi_demodata.fact_order o
JOIN study_powerbi_demodata.dim_region r ON o.region_id = r.region_id
WHERE r.province_name = '广东' AND o.status = '已完成';

SELECT ROUND(SUM(order_amount), 2) FROM v_guangdong_sales;
-- 实跑: 1078152.70  （= 广东销售额，与全教程口径一致）
```

---

## 三、视图的管理：查看 / 改 / 删

```sql
SHOW CREATE VIEW v_valid_order;     -- 看视图底层 SQL（口径对没对）
CREATE OR REPLACE VIEW v_valid_order AS ...;   -- 口径改了? 整体替换
DROP VIEW v_valid_order;            -- 删除（不影响底层表!）
DROP VIEW v1, v2, v3;               -- 一次删多个
```
> ⚠️ **删视图不删数据**——视图只是"壳"。真正要小心的是 `DROP TABLE`（ch13 讲过不可恢复）。

### 视图能更新吗？

```
简单视图(单表、无聚合、无DISTINCT)  → 可以 UPDATE/INSERT（会改到底层表）
带 JOIN/聚合/GROUP BY 的视图        → 只读（改了没意义）

实务建议: 视图当"只读口径封装"用, 更新数据一律走底层表 UPDATE(ch09)
```

---

## 四、字符串函数：清洗文本的主力

| 函数 | 作用 | 例子 → 结果 |
|---|---|---|
| `CONCAT(a,b)` | 拼接 | `CONCAT('ST-','BD-','42')` → `ST-BD-42` |
| `UPPER/LOWER` | 大小写 | `UPPER('st-bd-42')` → `ST-BD-42` |
| `SUBSTRING(s,n,len)` | 截取 | `SUBSTRING('ST-BD-42',4,2)` → `BD` |
| `LEFT(s,n)/RIGHT(s,n)` | 左/右截 | `LEFT('广东省东莞市',3)` → `广东省` |
| `CHAR_LENGTH(s)` | 字符数 | `CHAR_LENGTH('静音球')` → `3` |
| `LENGTH(s)` | 字节数 | `LENGTH('静音球')` → `9`（UTF-8 中文 3 字节） |
| `REPLACE(s,a,b)` | 替换 | `REPLACE('包布静音球','静音球','加重静音球')` → `包布加重静音球` |
| `TRIM(s)` | 去首尾空格 | `TRIM('  ST-BD-42  ')` → `ST-BD-42` |
| `LPAD/RPAD` | 补位 | `LPAD('42',6,'0')` → `000042` |
| `LOCATE(a,s)` | 找位置 | `LOCATE('BD','ST-BD-42')` → `4` |

```sql
SELECT CONCAT('ST-','BD-','42');                    -- ST-BD-42
SELECT LENGTH('静音球'), CHAR_LENGTH('静音球');      -- 9  3  ← 中文按字节vs字符
SELECT LPAD('42', 6, '0');                          -- 000042
```
**实跑：**
```
ST-BD-42
9 3
000042
```
> 实战：**料号/编号对齐**（`LPAD` 补 0）、**脏数据清洗**（`TRIM` 去空格、`REPLACE` 换单位）、**导出前拼接**（`CONCAT`）。

---

## 五、日期函数：报表的"时间轴"

教学库 `dim_date` 已有年/季/月，但真实业务常要从日期列现算。

| 函数 | 作用 | 例子 → 结果 |
|---|---|---|
| `YEAR(d)/MONTH(d)/DAY(d)` | 取年/月/日 | `YEAR('2026-09-04')` → `2026` |
| `QUARTER(d)` | 取季度 | `QUARTER('2026-09-04')` → `3` |
| `DATE_FORMAT(d,'%Y-%m')` | 格式化 | `DATE_FORMAT('2026-09-04','%Y年%m月')` → `2026年09月` |
| `DATEDIFF(d1,d2)` | 相差天数 | `DATEDIFF('2026-09-04','2026-01-01')` → `246` |
| `DATE_ADD/SUB(d, INTERVAL n 单位)` | 加减 | `DATE_ADD('2026-09-04', INTERVAL 1 MONTH)` → `2026-10-04` |
| `NOW()` | 当前时间 | `NOW()` → `2026-09-04 ...` |

**真实业务：按"年月"汇总 2024 年销售额**（用函数现算，不依赖 dim_date）：

```sql
SELECT CONCAT(YEAR(order_date), 'Q', QUARTER(order_date)) AS 季度,
       ROUND(SUM(order_amount), 2) AS 销售额
FROM study_powerbi_demodata.fact_order
WHERE status = '已完成' AND YEAR(order_date) = 2024
GROUP BY 季度
ORDER BY 季度;
```
**实跑：**
```
季度    销售额
2024Q1  566234.31
2024Q2  652962.64
2024Q3  507749.88
2024Q4  808163.12
```
> 四季度合计 2,535,109.95 = 2024 全年销售额（和 SQL ch07/Power BI 对得上 ✅）。**写报表习惯：时间维度一律用日期函数现算或连 dim_date，别硬编码 '2024-01' 这类字符串。**

---

## 六、数值函数与条件逻辑：算得干净、分得出档

### 数值

```sql
SELECT ROUND(7.195492, 2), ROUND(7.5), FLOOR(7.9), CEIL(7.1), MOD(10, 3), ABS(-5);
-- 实跑: 7.20  8  7  8  1  5
```
| 函数 | 作用 |
|---|---|
| `ROUND(x, n)` | 四舍五入到 n 位小数（金额报表最常用） |
| `FLOOR/CEIL` | 向下/向上取整 |
| `MOD(a,b)` | 取余（`MOD(id,2)=0` 判偶数、分表） |
| `ABS` | 绝对值 |

### 条件三兄弟：CASE / IF / IFNULL

```
CASE WHEN 条件 THEN 值 [WHEN ...] [ELSE] END   ★最强大, 万能分档
IF(条件, 真值, 假值)         单条件二选一
IFNULL(x, 默认值)            只有"是否为空"一种判断
COALESCE(x, y, z, ...)       多个候选取第一个非空
```

**真实分档：把 2,366 张有效订单按金额分成大/中/小单**（CASE 是报表高频）：

```sql
SELECT CASE WHEN order_amount >= 3000 THEN '大单(>=3000)'
            WHEN order_amount >= 1500 THEN '中单(1500-2999)'
            ELSE '小单(<1500)' END AS 分档,
       COUNT(*) AS 单数,
       ROUND(SUM(order_amount), 2) AS 销售额
FROM study_powerbi_demodata.fact_order
WHERE status = '已完成'
GROUP BY 分档
ORDER BY 单数 DESC;
```
**实跑（真实数字）：**
```
分档            单数   销售额
大单(>=3000)    925    5059319.71
小单(<1500)     752    618158.87
中单(1500-2999) 689    1518014.15
```
> 单数合计 925+752+689 = **2,366**、金额合计 = **7,195,492.73**——和全库口径严丝合缝。CASE 分档后**还能继续 GROUP BY / 排序**，这是 IF 做不到的。

```sql
-- IF 示例（单条件）:
SELECT order_id, IF(order_amount >= 3000, '大单', '普通') AS 标记
FROM study_powerbi_demodata.fact_order WHERE status='已完成' LIMIT 3;
-- IFNULL/COALESCE（防 NULL 把计算结果变 NULL，配合 ch08 三值逻辑）:
SELECT IFNULL(NULL, '空');          -- 空
SELECT COALESCE(NULL, NULL, '兜底'); -- 兜底
```

---

## 七、模糊匹配：LIKE vs 正则 REGEXP

```
LIKE    % 任意多字符、_ 单个字符；慢速、只能简单前后缀匹配
REGEXP  真正的正则: ^开头 $结尾 [字符类] |或 .任意 *重复 ?可选 (分组)

规则对照:
  以"花"开头      LIKE '花%'        REGEXP '^花'
  以"州"结尾      LIKE '%州'        REGEXP '州$'
  含"香薰"        LIKE '%香薰%'     REGEXP '香薰'
  含数字          (LIKE 做不到)     REGEXP '[0-9]'
  以 肌或花 开头   (LIKE 难)         REGEXP '^(肌|花)'
```

**教学库真实匹配（dim_product 是快消品，名称纯中文）：**

```sql
SELECT COUNT(*) FROM dim_product WHERE product_name LIKE '%香薰%';
-- 实跑: 7 （7 款香薰机）

SELECT COUNT(*) FROM dim_product WHERE product_name REGEXP '[a-zA-Z0-9]';
-- 实跑: 15 （15 款名称含英文/数字, 如 "BB"）
-- 反过来说: 185 款是纯中文名

SELECT COUNT(*) FROM dim_product WHERE brand REGEXP '^花';
-- 实跑: 13 （花漾品牌下 13 个 SKU）
```
> 正则坑（ch08 的亲戚）：**`REGEXP` 匹配是"部分匹配"**——`'香薰'` 等价于 LIKE `'%香薰%'`。要"整串完全匹配"得手动加 `^` 和 `$`：`REGEXP '^香薰$'`。数据量大时 REGEXP 不走索引（和 `LIKE '%xx%'` 一样全表扫），生产大表慎用，小表随便。

---

## 八、小结

1. **视图 = 命名的 SQL 宏**：不存数据、实时执行，把"口径"存一处，报表统一 `FROM 视图`
2. 视图管理：`CREATE / CREATE OR REPLACE / SHOW CREATE / DROP VIEW`；删视图不删数据
3. 简单单表视图可更新，带 JOIN/聚合的只读；实务上视图只当只读口径封装
4. 字符串函数：`CONCAT` 拼接、`TRIM/REPLACE` 清洗、`LPAD` 补位、`CHAR_LENGTH` 数中文字符
5. 日期函数：`YEAR/MONTH/QUARTER` 取时间、`DATE_FORMAT` 格式化、`DATEDIFF` 算间隔、`DATE_ADD` 平移
6. 条件三兄弟：**CASE 分档（可 GROUP BY）、IF 二选一、IFNULL/COALESCE 防空**
7. 模糊匹配：LIKE 简单够用；真正则用 `REGEXP`（记住它=部分匹配，整串要加 `^$`）

---

## 九、练习 5 题

### 练习 1：清洗"脏"客户名

city 列可能有空格（如 `' 广州 '`）、大小写不敏感问题。写 SQL 把 city 清成无首尾空格，并统计清洗后有多少个不同城市。

**答案：**
```sql
SELECT COUNT(DISTINCT TRIM(city)) AS 城市数 FROM study_powerbi_demodata.dim_customer;
-- 实跑: 22
```
**解析**：`TRIM(city)` 去掉首尾空格再 `DISTINCT`。如果直接 `COUNT(DISTINCT city)`，`'广州'` 和 `' 广州'` 会被算成两个城市（本例数据较干净所以同为 22）。**ETL 清洗的第一动作永远是 TRIM**。

### 练习 2：把日期格式化成"2024年1月"

从 `fact_order` 取数，输出 `订单月份`（形如 `2024年1月`）和当月销售额，只要 2024 年已完成订单，按月排序。

**答案：**
```sql
SELECT DATE_FORMAT(order_date, '%Y-%m') AS 月份,      -- ⚠️ 用 %Y-%m 别用 %Y年%m月
       ROUND(SUM(order_amount), 2) AS 销售额
FROM study_powerbi_demodata.fact_order
WHERE status = '已完成' AND YEAR(order_date) = 2024
GROUP BY 月份
ORDER BY 月份;       -- '%Y-%m' 格式下字符串排序=时间排序，月份不乱
-- 实跑: 12 行，合计 2,535,109.95（=2024 全年销售额，口径一致 ✅）
-- 1月 238217.59 / 2月 176572.22 / 3月 151444.50 ...
```
**解析**：`%Y`=四位年、`%m`=两位月。**坑**：若格式化成 `'2024年%c月'`（无前导零）再 `ORDER BY 月份`，字符串排序会把 10/11/12 月排到 1 月前面（`'10'<'9'`）——实跑验证顺序错乱。所以**时间维度格式化首选 `%Y-%m` 这种"数值友好"格式**，排序天然正确；要显示成中文再做一层替换。月份先 GROUP BY 再排序即可。

### 练习 3：CASE 给客户分档

按累计消费给客户分三档（>=5000 大客户 / >=2000 中客户 / 其他），统计每档人数。

**答案：**
```sql
SELECT CASE WHEN 累计 >= 5000 THEN '大客户'
            WHEN 累计 >= 2000 THEN '中客户'
            ELSE '小客户' END AS 分档,
       COUNT(*) AS 人数
FROM (
    SELECT customer_id, SUM(order_amount) AS 累计
    FROM study_powerbi_demodata.fact_order
    WHERE status = '已完成'
    GROUP BY customer_id
) t
GROUP BY 分档;
```
**解析**：先子查询算出每客户累计，外层再 CASE 分档并 GROUP BY。**CASE 只能在 SELECT 层面对"已算出的列"分档**，所以要先聚合出累计、再分档（子查询/CTE 是标准写法，呼应 ch05）。

**实跑：**
```
分档    人数
大客户   420
中客户    65
小客户    13
```
> 合计 420+65+13 = **498**（有效下单客户数，与 ch05「2 客户无成交」对应：500 客户 - 2 = 498 ✅）。注意这是**下单客户**分档，不是注册客户分档——若按 `dim_customer` 全量 500 人分档，另有 2 人累计为 0 会落进"小客户"。

### 练习 4：用函数找出"注册满 2 年"的客户

`dim_customer` 有 `register_date`。找出注册日期距今天超过 730 天的客户数。

**答案：**
```sql
SELECT COUNT(*) FROM study_powerbi_demodata.dim_customer
WHERE DATEDIFF(CURDATE(), register_date) > 730;
```
**解析**：`DATEDIFF(CURDATE(), register_date)` 算注册到今天的天数。或等价的 `register_date < DATE_SUB(CURDATE(), INTERVAL 730 DAY)`。**注意**：对 `register_date` 列做函数（如 `YEAR(register_date)=2024`）会让该列索引失效（ch10 会讲），所以能直接比列就别套函数。

**实跑：** `500`（全部客户注册都超过 730 天——演示库注册日期跨度设计所致；真实业务里这题用于筛"老客户"）。

### 练习 5：写一个"有效订单"视图并验证口径

把「状态=已完成」的有效订单封装成视图，再基于视图算一次全库销售额，验证 = 7,195,492.73。

**答案：**
```sql
USE study_sql_ddl_practice;
CREATE VIEW v_valid_order AS
SELECT order_id, customer_id, order_date, order_amount, order_profit
FROM study_powerbi_demodata.fact_order
WHERE status = '已完成';

SELECT COUNT(*) AS 单数, ROUND(SUM(order_amount),2) AS 销售额
FROM v_valid_order;
-- 实跑: 2366   7195492.73  ✅

DROP VIEW v_valid_order;    -- 练习完删除，不留垃圾
```
**解析**：视图把「有效订单」口径固化——以后任何报表 `FROM v_valid_order` 就自动带上了 `status='已完成'`，不会再犯"忘了过滤、金额虚高到 1069 万"的错。**这就是视图最大的价值：把容易忘的口径变成默认。**

---

## 十、下一步

视图和函数让你"写得干净"，但真正的生产问题是：**这个查询能不能在大数据量下跑得动**？下一章是性能核心——索引与 EXPLAIN，先看懂 B+ 树为什么让查找 O(log n)，再看执行计划怎么暴露慢查询。

→ [ch15 权限与备份恢复](./ch15_权限与备份恢复.md)
