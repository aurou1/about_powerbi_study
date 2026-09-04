# ch13 自己建表：DDL、数据类型、约束与范式

> 学习目标：前面 12 章一直在"用别人建好的表"查数据。这一章角色反转——**从零建一张表**：选对数据类型、用主键/外键/唯一约束守住数据质量、用 `ALTER` 平滑改表，最后理解**三范式**和它怎么演化成你熟悉的星型模型。
>
> 本章全程在一个**独立的练习库 `study_sql_ddl_practice`** 里操作，绝不碰教学库 `study_powerbi_demodata`；练完一条命令删库，不留垃圾。

---

## 一、CREATE TABLE：一条语句建一张表

先看你每天都在查的 `dim_customer` 当年是怎么建出来的（真实 DDL，直接 `SHOW CREATE TABLE` 可见）：

```sql
CREATE TABLE dim_customer (
  customer_id   INT         NOT NULL,            -- 客户ID：整型，必填
  customer_name VARCHAR(30) NOT NULL,            -- 姓名：最长30字符，必填
  gender        CHAR(1)     NOT NULL,            -- 性别：定长1字符
  city          VARCHAR(20) NOT NULL,            -- 城市
  region_id     INT         NOT NULL,            -- 所属大区（外键→dim_region）
  register_date DATE        NOT NULL,            -- 注册日期
  tier          VARCHAR(10) NOT NULL,            -- 客户等级
  PRIMARY KEY (customer_id)                      -- 主键：唯一标识一行
);
```
语法骨架（背下来）：

```sql
CREATE TABLE 表名 (
  列名1  数据类型    [NOT NULL] [DEFAULT 默认值] [UNIQUE] [AUTO_INCREMENT],
  列名2  数据类型    ...,
  ...,
  PRIMARY KEY (列),          -- 表级：主键
  UNIQUE KEY 名 (列),        -- 表级：唯一
  CONSTRAINT 约束名 FOREIGN KEY (列) REFERENCES 父表(父列)  -- 表级：外键
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

> **引擎与字符集必须写对**：`ENGINE=InnoDB`（支持事务/外键）、`CHARSET=utf8mb4`（中文不乱码）——这也是教学库所有表的统一配置。

---

## 二、数据类型怎么选（配选择图）

```
数值 ──┬─ 整数     TINYINT(-128~127)/SMALLINT/INT/BIGINT
        │             常用 INT；省空间用 TINYINT/SMALLINT
        └─ 小数     DECIMAL(10,2) 精确小数 ★金额必须用它
                   FLOAT/DOUBLE 有误差 → 禁止用于金额

字符串 ─┬─ 定长     CHAR(n)    长度固定(省空间但浪费)
         └─ 变长     VARCHAR(n) 长度可变 ★绝大多数用这个
日期   ── DATE(年月日)/DATETIME(年月日时分秒)/TIMESTAMP
布尔   ── 一般用 TINYINT(1) 存 0/1（dim_date.is_weekend 就是这么存的）
```
```
金额为什么必须 DECIMAL 而不是 FLOAT？（Python ch02 讲过的浮点误差，SQL 同理）
SELECT 0.1 + 0.2;            → 0.30000000000000004 (FLOAT 族)
SELECT CAST(0.1 AS DECIMAL(10,2)) + CAST(0.2 AS DECIMAL(10,2));
                             → 0.30            (精确)
```
> 选类型三问：**① 它是整数还是小数？② 小数涉及钱吗（涉及→DECIMAL）？③ 最长会有多长（定 VARCHAR 长度）？**

---

## 三、建一张自己的表（跟着做）

进练习库，建一张「客户 + 订单」迷你表：

```sql
CREATE DATABASE study_sql_ddl_practice CHARACTER SET utf8mb4;   -- 建库
USE study_sql_ddl_practice;                                      -- 切过去

CREATE TABLE customer (
  customer_id   INT AUTO_INCREMENT PRIMARY KEY,   -- 自增主键：不用手动填
  customer_no   VARCHAR(20) NOT NULL UNIQUE,      -- 客户编号：不许重复
  customer_name VARCHAR(30) NOT NULL,
  tier          VARCHAR(10) NOT NULL DEFAULT '普通',  -- 不填默认"普通"
  credit        DECIMAL(10,2) NOT NULL DEFAULT 0.00, -- 信用额度
  age           TINYINT UNSIGNED NULL              -- 年龄：允许空
) ENGINE=InnoDB;
```

`SHOW CREATE TABLE customer;` 会返回（实跑）：
```
CREATE TABLE `customer` (
  `customer_id` int(11) NOT NULL AUTO_INCREMENT,
  `customer_no` varchar(20) NOT NULL,
  ...
  PRIMARY KEY (`customer_id`),
  UNIQUE KEY `customer_no` (`customer_no`)
) ENGINE=InnoDB ...
```
注意 `CHECK (credit >= 0)` 之类的检查约束**没有出现在建表结果里**——这正是本机 MySQL 8.0.12 的坑，见下文「约束实测」。

---

## 四、约束：数据库自己守门的四种规则

| 约束 | 作用 | 违反时 |
|---|---|---|
| `PRIMARY KEY` | 唯一 + 非空，一行的身份 | 重复主键报 1062 |
| `UNIQUE` | 列值不许重复 | 重复值报 **1062** |
| `NOT NULL` | 不许为空 | 空值报 1048 |
| `FOREIGN KEY` | 引用的父行必须存在 | 不存在报 **1452** |
| `DEFAULT` | 不填时用默认值 | —（不是约束，是兜底） |
| `CHECK` | 值域校验 ⚠️ 见下 | **8.0.12 不生效！** |

### 实跑验证（全部在练习库真跑过）

```sql
INSERT INTO customer(customer_no, customer_name, tier, credit, age)
VALUES ('C001', '梁诗', '钻石', 5000.00, 30);       -- ✅ 影响 1 行

-- ① UNIQUE 冲突
INSERT INTO customer(customer_no, customer_name) VALUES ('C001', '重复号');
-- ❌ ERROR 1062: Duplicate entry 'C001' for key 'customer.customer_no'

-- ② CHECK 约束：信用额度为负
INSERT INTO customer(customer_no, customer_name, credit) VALUES ('C002', '负数信用', -1);
-- ⚠️ 8.0.12 实测: 插入成功! 负数 -1.00 真的进了库!
```
```
实测结论（重要，别被老教程骗了）:
  MySQL 8.0.12 会"解析"CHECK 但不"强制"——因为 CHECK 真正生效是 8.0.16 起。
  8.0.12 上写 CHECK 约束 = 白写!
  教训: 低版本 MySQL 别指望 CHECK 兜底, 数据校验要在应用层做
```
```sql
-- ③ 外键：引用的父行必须存在
CREATE TABLE cust_order (
  order_id    INT AUTO_INCREMENT PRIMARY KEY,
  customer_id INT NOT NULL,
  order_date  DATE NOT NULL,
  amount      DECIMAL(12,2) NOT NULL DEFAULT 0,
  CONSTRAINT fk_co_cust FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
) ENGINE=InnoDB;

INSERT INTO cust_order(customer_id, order_date, amount) VALUES (1, '2026-09-01', 99.00);  -- ✅
INSERT INTO cust_order(customer_id, order_date, amount) VALUES (999, '2026-09-01', 1.00);
-- ❌ ERROR 1452: Cannot add or update a child row:
--    a foreign key constraint fails ... (customer_id=999 不存在)
```
> 外键是星型模型的骨架：`fact_order_item.product_id` 必须存在于 `dim_product`——数据字典里那 6 张表的外键就是这么保证「明细永远找得到维度」的。

### 删数据时外键怎么拦（本库真实演示）

```
在 dim_product 里删一个被 fact_order_item 引用的商品:
DELETE FROM dim_product WHERE product_id = 1;
→ ERROR 1451: Cannot delete or update a parent row: a foreign key
  key constraint fails (fact_order_item 里还有这个商品)
```
> 外键保护了**引用完整性**：不让维度表删掉"还有订单在引用"的行。想删只能先清明细或改外键策略（`ON DELETE CASCADE`，见 ch12 提到的事务与级联）。

---

## 五、ALTER TABLE：给表"做手术"

改表结构不影响数据，但要小心锁表（大表 ALTER 会阻塞写入）：

```sql
-- 加一列
ALTER TABLE customer ADD COLUMN phone VARCHAR(20) NULL;
-- 改列类型/默认值
ALTER TABLE customer MODIFY COLUMN tier VARCHAR(10) NOT NULL DEFAULT '黄金';
-- 加索引（ch10 细讲）
ALTER TABLE customer ADD INDEX idx_name (customer_name);
-- 删列 / 删表 / 清空表
ALTER TABLE customer DROP COLUMN phone;
DROP TABLE customer;             -- 连结构带数据删除（不可恢复!）
TRUNCATE TABLE cust_order;       -- 只清数据、保留结构（更快, 但不可按事务回滚）
```

**实跑验证 DEFAULT 兜底**：
```sql
ALTER TABLE customer MODIFY COLUMN tier VARCHAR(10) NOT NULL DEFAULT '黄金';
INSERT INTO customer(customer_no, customer_name) VALUES ('C003', '默认档');
SELECT customer_no, tier FROM customer WHERE customer_no='C003';
-- 结果: ('C003', '黄金')   ← 没填 tier, 自动用了新默认值
```

> ⚠️ 生产环境改表三连问：**① 会锁多久？② 有备份吗？③ 能回滚吗？** 大表加列用 `pt-osc`/`gh-ost` 在线工具或业务低峰做，是 DBA 的日常。

---

## 六、三范式：为什么表要"拆开"（配图）

你天天 JOIN 的星型模型，其实是"拆表"拆出来的。三范式就是拆表的规则：

```
第一范式 1NF：每格只存一个值（原子性）
  ❌ 订单表里一格存 "静音球,泳镜,篮球"        ← 违反 1NF, 没法按商品统计
  ✅ 拆成 订单表 + 订单明细表(一行一个商品)    ← fact_order / fact_order_item

第二范式 2NF：1NF + 非主键列完全依赖主键（不依赖主键的一部分）
  ❌ 订单明细表里存 "客户名"                  ← 客户名只跟订单头有关, 与(商品)无关
  ✅ 客户名挪到 客户表/订单头表, 明细只留 order_id

第三范式 3NF：2NF + 非主键列不依赖其他非主键列（消除传递依赖）
  ❌ 订单表里存 "客户所在大区名"              ← 大区名经由 客户→大区, 是传递依赖
  ✅ 订单表只存 region_id, 大区名在 dim_region
```

```
三范式 → 你熟悉的星型模型（一张图看懂）：

             维度表(被拆出来的"字典")
             dim_region(大区)
                ▲ region_id
  事实表        │
  fact_order ───┼──▶ dim_customer(客户)     ← 只存 customer_id, 不存客户名
  (订单)        │
                ├──▶ dim_product(商品)       ← 只存 product_id, 不存品名价
                │
                └──▶ dim_date(日期)          ← 只存 date, 不存"是否节假日"

  事实表只留"外键 + 度量值(数量/金额)"
  维度的详细信息全部外键关联去查 = 3NF 的产物
```
> 一句话：**范式 = "每个事实只存一次，别的地方用外键引用"**。好处：改客户名只改一处（dim_customer），所有订单自动看到新名字；坏处：查询要 JOIN——这正是你前 12 章练的东西。

---

## 七、什么时候"故意"违反范式（反范式）

真实报表库常做反范式，**用空间/冗余换查询速度**：

```
反范式例子1：订单表冗余存 order_amount/order_profit
   明明可以从明细 SUM 出来, 为什么存?
   → 每次报表都要 SUM 几万行明细太慢, 直接读表头金额秒回
   → 教学库 fact_order.order_amount 就是冗余（口径5: 别和明细重复求和!）

反范式例子2：维度表里冗余"大区名"
   fact_order 存 region_id, 但报表高频按大区过滤
   → 有人会把 zone 冗余进订单表省一次 JOIN

风险: 冗余 = 不一致的风险(改了 dim_region 忘了改订单表里的冗余列)
规则: 写多读少的 OLTP 库守范式; 读多写少的数仓/报表库做反范式
```

---

## 八、小结

1. `CREATE TABLE` = 列定义 + 约束 + 引擎字符集；`ENGINE=InnoDB` + `utf8mb4` 是标配
2. 金额用 `DECIMAL`，禁用 FLOAT/DOUBLE；变长文本用 `VARCHAR`
3. 约束守门：PK 身份 / UNIQUE 去重(1062) / FK 引用完整(1452) / NOT NULL(1048)
4. ⚠️ **本机 MySQL 8.0.12 的 CHECK 不强制**（8.0.16 才生效），别依赖它
5. `ALTER TABLE` 加列/改默认值，生产要防锁表；`DROP/TRUNCATE` 不可恢复
6. 三范式：**1NF 每格一个值 → 2NF 完全依赖主键 → 3NF 消除传递依赖**
7. 星型模型 = 3NF 拆表的结果：事实表外键 + 维度表字典
8. 报表库常反范式（冗余表头金额）换速度，代价是不一致风险

---

## 九、练习 5 题

### 练习 1：判断数据类型是否合理

下面类型选择哪些错？① 金额用 FLOAT ② 手机号用 INT ③ 姓名用 VARCHAR(200) ④ 性别用 VARCHAR(10)

**答案：** ①②③④ 全错或欠妥。① 金额必须 DECIMAL（FLOAT 有误差）；② 手机号是"看起来像数字的文本"（有前导 0、不做运算）→ 用 VARCHAR(20)；③ 姓名一般 VARCHAR(30) 够，VARCHAR(200) 浪费；④ 性别定长 CHAR(1) 最省（男/女/未知）。**原则：按"它是什么"选类型，不按"它长得像什么"。**

### 练习 2：为下面的需求建表

商品表：料号(唯一,最长20)、品名、品类、成本价、吊牌价。写出 CREATE TABLE。

**答案：**
```sql
CREATE TABLE product (
  product_id   INT AUTO_INCREMENT PRIMARY KEY,
  product_no   VARCHAR(20) NOT NULL UNIQUE,     -- 料号唯一
  product_name VARCHAR(50) NOT NULL,
  category     VARCHAR(20) NOT NULL,
  cost_price   DECIMAL(10,2) NOT NULL,          -- 成本: 金额必须 DECIMAL
  list_price   DECIMAL(10,2) NOT NULL           -- 吊牌价
) ENGINE=InnoDB;
```
**解析**：与教学库 `dim_product` 结构一致——料号加 UNIQUE 防重复建档；两个价格用 DECIMAL(10,2)（最大 9,999,999.99，够泳镜/静音球单价用）。

### 练习 3：外键报错码判断

执行下面语句分别会报什么错误码？`INSERT INTO cust_order(customer_id,...) VALUES(999,...)` 和 `INSERT INTO customer(customer_no,...) VALUES('C001',...)`（C001 已存在）。

**答案：** 前者外键失败报 **1452**（父行不存在）；后者唯一键冲突报 **1062**（Duplicate entry）。两者都是 `IntegrityError` 家族，但码不同——**程序里捕获错误码可以分别提示"客户不存在"vs"编号重复"**，这比笼统提示"插入失败"专业得多。

### 练习 4：三范式判断

订单表里有这些列：order_id, customer_id, customer_name, product_id, quantity。违反哪条范式？怎么改？

**答案：** `customer_name` 违反 **2NF**——客户名只由 customer_id 决定，不依赖订单主键（且若同一客户下多单，名字要重复存，改一次名要改 N 行）。改法：订单表只留 customer_id，客户名放进 customer 表（`dim_customer` 正是这么设计的）。**判断口诀：能不能从"客户表 JOIN"得到？能 → 别冗余在订单表。**

### 练习 5：设计一张"订单明细"表

要记录：所属订单、商品、购买数量、成交单价、折扣、行金额、行利润。指出主键/外键/金额类型，并说明为什么不要存"商品名称"。

**答案：**
```sql
CREATE TABLE order_item (
  order_item_id INT AUTO_INCREMENT PRIMARY KEY,  -- 明细行自己的主键
  order_id      INT NOT NULL,                    -- 外键→订单
  product_id    INT NOT NULL,                    -- 外键→商品
  quantity      INT NOT NULL,
  unit_price    DECIMAL(10,2) NOT NULL,
  discount_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
  line_amount   DECIMAL(12,2) NOT NULL,
  line_profit   DECIMAL(12,2) NOT NULL,
  CONSTRAINT fk_item_order FOREIGN KEY (order_id)  REFERENCES fact_order(order_id),
  CONSTRAINT fk_item_prod  FOREIGN KEY (product_id) REFERENCES dim_product(product_id)
) ENGINE=InnoDB;
```
**解析**：与教学库 `fact_order_item` 几乎一致。不存商品名 = 遵守 2NF：品名在 `dim_product` 存一份，JOIN 取即可；否则商品改名/换价格时历史明细全乱。`line_amount/line_profit` 是反范式冗余（从 quantity×price 能算），但报表高频直接读——这就是"事实表存度量值"的数仓惯例。

---

## 十、下一步

表建好了、数据守住了，下一步把"经常要重复查的复杂 SELECT"**封装成视图**，并系统过一遍 SQL 的常用函数（字符串/日期/条件）——让查询从"能跑"变成"写得干净、算得巧"。

→ [ch14 视图与SQL函数](./ch14_视图与SQL函数.md)
