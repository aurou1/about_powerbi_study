# Power BI + SQL 学习库

电商订单星型模型演示库，用来练习 **Power BI 建模 / DAX** 与 **SQL 高级查询**（多表 JOIN、窗口函数、CTE）。

数据由脚本自动生成，共 **13,780 行**（维度 1,806 + 事实 11,974），埋好了可用于练习的真实差异：地区销售额差异、品类毛利率差异、客户等级消费分层、月度季节性（618 / 双11 / 双12 冲高）。

---

## 📁 文件清单

### 参考资料层（速查 / 清单，不含讲解）

| 文件 | 说明 |
|---|---|
| `generate_powerbi_demo.py` | 一键建库脚本（pymysql 直连 MySQL，建库建表 + 造数据，随机种���固定可复现） |
| `study_powerbi_demodata_数据字典.md` | 6 张表字段 / 外键关系 / 计算口径字典 |
| `PowerBI_SQL学习练习清单.md` | SQL 15 题梯度练习 + Power BI 10 项任务 + 窗口函数速查 |
| `study_powerbi_demodata_DAX度量值清单.md` | 24 个 DAX 度量值 + EVALUATE 查询 + 与 SQL 对照表 |

### 教程层（讲原理与操作，含完整练习答案解析）

| 目录 | 说明 |
|---|---|
| `powerbi-tutorial/` | **Power BI 零基础 → 进阶高手**，12 章，每章含示例 + 练习题（答案 + 解析 + 预期数字）。入口见 `powerbi-tutorial/README.md` |
| `sql-tutorial/` | **SQL 零基础 → 进阶高手**，15 章（12 章查询分析：单表查询 → 过滤排序 → 聚合分组 → 多表 JOIN → 子查询/CTE → 窗口函数 → NULL 与执行顺序 → 数据操作 → 索引/EXPLAIN → 存储过程/触发器 → 事务/递归 CTE/综合实战；+3 章工程管理：建表 DDL/约束/范式、视图与函数、账号权限与备份恢复），全部用同一套数据、数字实跑验证，含 B+树/连接算法/隔离级别 MVCC 等原理深挖。入口见 `sql-tutorial/README.md` |
| `python-tutorial/` | **Python 零基础 → 精通**，14 章（环境/数据类型/字符串/列表字典/流程控制/函数/异常文件/模块/OOP/迭代器生成器 → pandas/连 MySQL/可视化导出/工程化），示例输出全部经本机 Python 3.13 + MySQL 实跑，ch13 数字与 SQL 教程逐项对拍。入口见 `python-tutorial/README.md` |
| `dsa-tutorial/` | **数据结构与算法 从 0 基础到精通**，14 章（复杂度/数组字符串/链表/栈队列/哈希/递归分治/排序/二分/树/堆/图/动态规划/贪心回溯/综合实战），全部用 Python 3.13 标准库、示例输出实跑验证，结尾专设「与 FDE 岗结合」对照表。入口见 `dsa-tutorial/README.md` |

> 参考资料层是「字典和题目」，教程层是「为什么 + 怎么做 + 什么时候用」。四条教程线：Power BI 把数据变成报表，SQL 把数据查出来算明白，Python 把数据自动化处理（读库/清洗/出图/导出），数据结构与算法给前面三者「为什么快、怎么选型」的判断力。通过相对路径互链，内容不重复。

---

## 🛠 环境要求

- Python 3.8+：`pip install pymysql`
- MySQL 8.0（需支持窗口函数），字符集 utf8mb4
- Power BI Desktop（连接 MySQL 需装 **64 位 MySQL Connector/ODBC**）
- 可选：DAX Studio（ch10 性能分析用）

---

## 🚀 三步上手

### 1. 建库（生成演示数据）
编辑 `generate_powerbi_demo.py` 顶部 `DB_CONFIG`（host / user / password），然后运行：

```bash
python generate_powerbi_demo.py
```

会在 MySQL 里生成数据库 `study_powerbi_demodata`，含 6 张表：

| 表 | 类型 | 行数 |
|---|---|---:|
| dim_region | 维度 | 10 |
| dim_product | 维度 | 200 |
| dim_customer | 维度 | 500 |
| dim_date | 维度 | 1,096 |
| fact_order | 事实 | 3,529 |
| fact_order_item | 事实 | 8,445 |

### 2. Power BI 导入
1. 获取数据 → 数据库 → **MySQL 数据库** → 填 `host / 端口 / 用户 / 密码` → 选库 `study_powerbi_demodata`
2. 勾选 6 张表加载
3. 按数据字典的 ER 关系建**关系**（维度表 → 事实表）
4. 选中 `dim_date` → 建模 → **标记为日期表**
5. 需要度量值时查 `study_powerbi_demodata_DAX度量值清单.md`

### 3. 开始练
- **系统学 Power BI** → 进 `powerbi-tutorial/`，从 ch01 顺着读
- **系统学 SQL** → 进 `sql-tutorial/`，从 ch01 顺着读（与 Power BI 教程同数据、可对拍）
- **系统学 Python** → 进 `python-tutorial/`，从 ch01 顺着读（ch13 数字与 SQL 教程对拍）
- **只想刷题** → 直接看 `PowerBI_SQL学习练习清单.md`
- **查字段 / 查口径** → 查 `study_powerbi_demodata_数据字典.md`
- **建议先 SQL 跑出数字，再用 DAX 复现对拍**，理解筛选上下文最快

---

## ⚠️ 两个关键口径（坑）

1. **有效销售必须过滤 `status = '已完成'`** —— 已取消（591 单）/ 退款（572 单）的金额仍留在表里，不过滤会把 719 万虚高成 1069 万。
2. **金额取哪张表要看场景**：
   - 写 **SQL** → 用 `fact_order.order_amount`（一单一行，简单直观）
   - 写 **DAX 度量值** → 用 `fact_order_item.line_amount`（最细粒度，能与商品维正确相乘）
   - ⚠️ 两者**不要同时求和**，否则金额翻倍。

---

## 📊 关键基准数字（用于对拍，全部实跑验证）

| 指标 | 数值 |
|---|---:|
| 总订单（含全部状态） | 3,529 单 / 10,689,549.70 元 |
| **有效订单（已完成）** | **2,366 单 / 7,195,492.73 元** |
| 有效利润 / 毛利率 | 1,706,864.78 元 / **23.72%** |
| 有效客单价 | 3,041.21 元 |
| 状态分布 | 已完成 2,366（67.0%）/ 已取消 591（16.7%）/ 退款 572（16.2%） |
| 省份第一 / 最后 | 广东 1,078,152.70 / 陕西 436,054.65 |
| 品类毛利率（成交口径） | 数码 1.16% < 食品 21.75% < 家居 27.22% < 服饰 38.00% < 美妆 49.47% |
| 客户等级人数 | 普通 241 / 银卡 149 / 金卡 83 / 钻石 27 |
| 月度峰值 | 12 月 537 单 > 11 月 473 > 6 月 413（618 / 双11 / 双12） |

---

## 📤 上传 GitHub（回家也能学）

```bash
git init
git add .
git commit -m "Power BI + SQL 学习库"
git remote add origin <你的仓库URL>
git push -u origin main
```

回家后 `git clone <仓库URL>` 即可。重新建库跑一遍脚本就有数据。

---

## 📄 许可

学习用途，随意使用 / 修改 / 分享，无限制。
