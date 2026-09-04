# ch01 环境接入与 SELECT 基础 🔌

> 本章目标：连上 MySQL 里的 `study_powerbi_demodata`，**核对 6 张表的行数**，并写出你的第一条单表查询。
> 所有后续章节都建立在这一步之上。

---

## 一、本章学习目标

学完本章你应该能：

1. 用任意客户端连上 `study_powerbi_demodata`
2. 说出 SQL 在「数据分析交付」里扮演什么角色
3. 用 `SELECT` 取指定列、起别名、去重、限制行数
4. **导入数据后的第一件事 = 数行数**，确认 6 张表行数
5. 认识星型模型的 4 张维度表 + 2 张事实表

---

## 二、为什么要先花一章讲环境

这一章看起来是「连数据库」，但它是**交付现场最容易翻车的地方**。

在客户现场做实施（FDE 的日常）时，你面对的通常不是本机干净的 localhost，而是：

- 数据库在客户内网，你只拿到一个只读账号
- 客户 IT 说「库给你了，自己查」，但没告诉你有哪些表
- 你查出来的数字和业务对不上，却不知道是数据问题还是自己写错了
- 换台电脑，连接全部失败

所以本章要养成两个**终身受用的习惯**：

> **习惯 1：连上库的第一件事，永远是数行数、看表结构。**
> **习惯 2：任何数字，都要能用 SQL 独立算一遍来验证。**

SQL 不是「调数据的工具」，它是你和数据库之间的**唯一契约语言**——你写错一个词，数据库绝不会提醒你「你是不是想查别的」，它只会安静地返回一个错的数字。

---

## 三、概念：SQL 与星型模型

### 3.1 SQL 是什么

SQL（Structured Query Language）是用来「问数据库要数据」的语言。四条最基础的动词：

| 动词 | 干什么 | 本章学不学 |
|---|---|---|
| `SELECT` | 查（取数） | ✅ 本章 |
| `INSERT` | 增 | ch09 |
| `UPDATE` | 改 | ch09 |
| `DELETE` | 删 | ch09 |

> 90% 的数据分析工作，其实只需要把 `SELECT` 玩透。**改数据（增删改）反而要慎之又慎**——ch09 才讲，而且全程配事务。

### 3.2 我们的数据长什么样（星型模型）

本库是电商订单的「星型模型」：中间是事实表（发生了什么），四周是维度表（用来描述事实）。

```
            dim_date(日期)
                 ▲
dim_region(地区)◀──────┐
     ▲                 │
     │ dim_customer(客户)
     │                 │
fact_order(订单头) ──▶ fact_order_item(订单明细)
                      │
                      ▼
                 dim_product(商品)
```

| 表 | 类型 | 行数 | 一句话 |
|---|---|---:|---|
| `dim_region` | 维度 | 10 | 10 个省 / 大区 |
| `dim_product` | 维度 | 200 | 200 个商品，含品类、品牌、成本、吊牌价 |
| `dim_customer` | 维度 | 500 | 500 个客户，含等级、城市 |
| `dim_date` | 维度 | 1,096 | 2023-01-01 ~ 2025-12-31 每天一行 |
| `fact_order` | 事实 | 3,529 | 一单一行（订单头） |
| `fact_order_item` | 事实 | 8,445 | 一单一品一行（订单明细） |

**事实表 vs 维度表（必须分清）**：

- 事实表记「事件」（下单了、卖了多少），通常**又长又窄**，是分析的主角
- 维度表记「属性」（这商品属于哪个品类、这个客户是哪个等级），通常**又短又宽**，用来分组和筛选

---

## 四、实操：四步连上库并跑出第一行

### 4.1 第一步：连上数据库

打开你的客户端（命令行 / PyCharm Database / 小皮面板 SQL 工具），连：

| 字段 | 填什么 |
|---|---|
| 主机 | `localhost` 或 `127.0.0.1` |
| 端口 | `3306` |
| 用户 | `root` |
| 密码 | `root` |
| 数据库 | `study_powerbi_demodata` |

命令行验证：

```bash
mysql -uroot -proot -h127.0.0.1 study_powerbi_demodata --default-character-set=utf8mb4
```

能进来就成功。看到 `mysql>` 提示符后，所有 SQL 以分号 `;` 结尾。

> ⚠️ **踩坑提醒**：本机 MySQL 在小皮面板（phpStudy）里，**重启电脑后不会自动启动**。连不上先去小皮面板点「启动」，或手动跑 `mysqld.exe --console`。

### 4.2 第二步：看有哪些表

```sql
SHOW TABLES;
-- 预期：dim_customer / dim_date / dim_order / dim_order_item / dim_product / dim_region（6 张）
```

看某张表的结构（字段、类型、是否允许空）：

```sql
DESC dim_product;
-- 预期：product_id / product_name / category / brand / cost_price / list_price
```

### 4.3 第三步：你的第一条 SELECT

```sql
SELECT * FROM dim_product LIMIT 10;
```

- `SELECT *` = 取所有列
- `FROM dim_product` = 从哪张表
- `LIMIT 10` = 只取前 10 行（**新手必加，避免一次吐出 200 行刷屏**）

### 4.4 第四步：取指定列 + 起别名

```sql
SELECT
    product_name                 AS 商品名,
    category                     AS 品类,
    ROUND(list_price, 2)         AS 吊牌价
FROM dim_product
LIMIT 5;
```

- `AS` 给列起中文别名（仅显示用，不改库）
- `ROUND(数字, 2)` 保留 2 位小数

### 4.5 去重 DISTINCT

```sql
SELECT DISTINCT category FROM dim_product;
-- 预期：家居 / 数码 / 服饰 / 食品 / 美妆（5 个品类，200 行压缩成 5 行）
```

---

## 五、验证：数行数（你必须做的这一步）

连上库、会写 `SELECT` 了，但**你还没确认数据是对的**。现在数行数。

### 5.1 一次性数完 6 张表

```sql
SELECT 'dim_region'    AS 表,  COUNT(*) AS 行数 FROM dim_region
UNION ALL SELECT 'dim_product',  COUNT(*) FROM dim_product
UNION ALL SELECT 'dim_customer', COUNT(*) FROM dim_customer
UNION ALL SELECT 'dim_date',     COUNT(*) FROM dim_date
UNION ALL SELECT 'fact_order',   COUNT(*) FROM fact_order
UNION ALL SELECT 'fact_order_item', COUNT(*) FROM fact_order_item;
```

**预期结果（必须一字不差）**：

| 表 | 预期行数 |
|---|---:|
| dim_region | 10 |
| dim_product | 200 |
| dim_customer | 500 |
| dim_date | 1,096 |
| fact_order | 3,529 |
| fact_order_item | 8,445 |
| **合计** | **15,780** |

> **FDE 视角**：这一步叫「数据完整性校验」。在客户现场，我通常会把这 6 个数字截图发给客户确认，拿到一句"对，就是这个数"再开工。后面如果客户说"你这数字不对"，你可以立刻证明是口径问题而不是数据问题——保护自己。

### 5.2 顺手看一眼维度分布（预热 GROUP BY）

```sql
SELECT category, COUNT(*) AS 商品数
FROM dim_product
GROUP BY category
ORDER BY 商品数 DESC;
-- 预期：美妆 50 / 家居 39 / 食品 39 / 数码 38 / 服饰 34（合计 200）
```

再看客户等级分布：

```sql
SELECT tier, COUNT(*) AS 客户数
FROM dim_customer
GROUP BY tier
ORDER BY FIELD(tier, '普通','银卡','金卡','钻石');
-- 预期：普通 241 / 银卡 149 / 金卡 83 / 钻石 27（合计 500）
```

记住这两个分布，后面每章都要用。

---

## 六、FDE 现场场景：客户只给你一个只读账号

真实交付里，你很少能拿到 `root/root` 这么痛快的权限。几种情况和应对：

| 客户给你的 | 怎么做 | 代价 |
|---|---|---|
| 只读账号 | 直接连，和本章一样 | 最理想 |
| 只有内网机器能连库 | 在那台机器上操作，或配网关 | 需要装软件 |
| 只给了一张 Excel / CSV | 用 `LOAD DATA` 或客户端导入成临时表 | 无法自动刷新 |
| 只给了一个大宽表（没维度表） | 自己在查询里拆维度（ch03、ch05） | 要更多 SQL 功底 |
| 只让查视图，不给原表 | 连视图 | 视图性能可能很差 |

> **核心心法**：SQL 这头的难度，80% 取决于**源数据给你什么形态**。数据给得好，查询就是几行；数据给得烂，你一半时间在做清洗（这部分 Power BI 教程 ch03 讲 Power Query，可以对照看）。

---

## 七、本章小结

| 你学到了 | 关键动作 |
|---|---|
| SQL 四动词 | `SELECT` 查（本章）、`INSERT/UPDATE/DELETE` 改（ch09） |
| 星型模型 | 4 维度（短宽）+ 2 事实（长窄） |
| 连库 | `localhost:3306` / `root` / `root` / utf8mb4 |
| 第一习惯 | 连上先**数行数**：10/200/500/1096/3529/8445 = 15,780 |
| SELECT 基本功 | `*` 全列 / 指定列 / `AS` 别名 / `DISTINCT` 去重 / `LIMIT` 限行 |
| 维度分布 | 品类 美妆50>家居39=食品39>数码38>服饰34；等级 241/149/83/27 |

---

## 八、练习题

### 练习 1：验证数据可复现（考：固定随机种子）

**题目**：回到上层目录重跑建库脚本，再数一遍 6 张表行数，看是否变化。

<details>
<summary>Hint</summary>
脚本里有 `random.seed(20260903)`。固定种子意味着什么？
</details>

**答案与解析**：

行数**完全不变**，仍是 10/200/500/1096/3529/8445。

**解析**：`random.seed(20260903)` 固定了随机数种子。Python 的 `random` 是伪随机——同一个种子、同一段代码，产生的「随机」序列完全一样。所以每次重建都得到同一份数据。

**这对你很重要**：意味着本教程里所有数字（比如「广东有效销售额 1,078,152.70」）你在任何机器上都能复现，方便对拍验证。

**预期结果**：6 张表行数与首次导入完全一致。

---

### 练习 2：查商品维度（考：指定列 + 别名 + LIMIT）

**题目**：从 `dim_product` 取出「商品名、品类、品牌、吊牌价」四列，只看前 8 行，吊牌价保留 2 位小数。

```sql
SELECT product_name AS 商品名, category AS 品类, brand AS 品牌,
       ROUND(list_price,2) AS 吊牌价
FROM dim_product
LIMIT 8;
```

**预期结果**：返回 8 行，列名为中文别名，吊牌价为 2 位小数（如 425.11）。

**解析**：`SELECT 列 AS 别名` 只改显示不改库；`LIMIT 8` 防止刷屏。

---

### 练习 3：数省份与大区（考：DISTINCT + 维度认知）

**题目**：列出本库覆盖的所有「大区（zone）」有哪些，各有多少个省。

```sql
SELECT zone AS 大区, COUNT(*) AS 省份数
FROM dim_region
GROUP BY zone
ORDER BY 省份数 DESC;
```

**预期结果**：华东 4（江苏/浙江/上海/山东）、华南 1（广东）、华北 1（北京）、西南 1（四川）、华中 1（湖北）、东北 1（辽宁）、西北 1（陕西）。

**解析**：`dim_region` 共 10 行 10 省，按 `zone` 聚合。华东权重最高（4 省），方便后面练「地区销售额差异」。

---

### 练习 4：看订单状态分布（考：预热有效口径，为 ch03 做准备）

**题目**：`fact_order` 里 `status` 有几种值，各多少单？

```sql
SELECT status, COUNT(*) AS 订单数
FROM fact_order
GROUP BY status
ORDER BY 订单数 DESC;
```

**预期结果**：已完成 2,366 / 已取消 591 / 退款 572（合计 3,529）。

**解析**：**只有 67% 的订单是真实成交**（2,366 / 3,529）。剩下 33%（1,163 单）是作废的，但金额仍躺在表里。记住这个比例：以后凡是你算出「销售额 1,069 万」，就要立刻警觉——你大概率忘了过滤状态（ch03 详讲）。

---

### 练习 5：理解一对多（考：事实表明细行数）

**题目**：`fact_order_item` 比 `fact_order` 多那么多行，说明什么？随便找一个 `order_id`，看它在明细表里出现几行。

```sql
SELECT order_id, COUNT(*) AS 明细行数
FROM fact_order_item
WHERE order_id = 2
GROUP BY order_id;
```

**预期结果**：`order_id = 2` 出现 **2 行**（一个订单买了 2 个商品）。

**解析**：这就是「一对多」——一个订单（`fact_order` 一行）可以包含多个商品（`fact_order_item` 多行）。这个关系，是 ch04 做 JOIN 的核心，也是 ch04「JOIN 膨胀」陷阱的根源。

---

## 下一步

数据已经安全连上了，6 张表也数清楚了。但 `SELECT *` 只会把整张表倒给你——下一章学怎么**精准过滤、排序、分页**，只取你要的那部分。

→ [ch02 过滤、排序与分页](./ch02_过滤排序与分页.md)
