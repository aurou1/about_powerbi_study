# Power BI + SQL 学习库

电商订单星型模型演示库，用来练习 **Power BI 建模 / DAX** 与 **SQL 高级查询**（多表 JOIN、窗口函数、CTE）。

数据由脚本自动生成，约 **1.6 万行**，埋好了可用于练习的真实差异：地区销售额差异、品类毛利率差异、客户等级消费分层、月度季节性（618 / 双11 / 双12 冲高）。

---

## 📁 文件清单

| 文件 | 说明 |
|---|---|
| `generate_powerbi_demo.py` | 一键建库脚本（pymysql 直连 MySQL，建库建表 + 造数据，随机种子固定可复现） |
| `study_powerbi_demodata_数据字典.md` | 6 张表字段 / 外键关系 / 计算口径字典 |
| `PowerBI_SQL学习练习清单.md` | SQL 15 题梯度练习 + Power BI 10 项任务 + 窗口函数速查 |
| `study_powerbi_demodata_DAX度量值清单.md` | 24 个 DAX 度量值 + EVALUATE 查询 + 与 SQL 对照表 |

---

## 🛠 环境要求

- Python 3.8+：`pip install pymysql`
- MySQL 8.0（需支持窗口函数），字符集 utf8mb4
- Power BI Desktop（连接 MySQL 需装 **64 位 MySQL Connector/ODBC**）

---

## 🚀 三步上手

### 1. 建库（生成演示数据）
编辑 `generate_powerbi_demo.py` 顶部 `DB_CONFIG`（host / user / password），然后运行：

```bash
python generate_powerbi_demo.py
```

会在 MySQL 里生成数据库 `study_powerbi_demodata`，含 6 张表（dim_region / dim_product / dim_customer / dim_date / fact_order / fact_order_item）。

### 2. Power BI 导入
1. 获取数据 → 数据库 → **MySQL 数据库** → 填 `host / 端口 / 用户 / 密码` → 选库 `study_powerbi_demodata`
2. 勾选 6 张表加载
3. 按数据字典的 ER 关系建**关系**（维度表 → 事实表）
4. 选中 `dim_date` → 建模 → **标记为日期表**
5. 把 `study_powerbi_demodata_DAX度量值清单.md` 里的度量值贴进「新建度量值」

### 3. 开始练
- SQL 侧：照 `PowerBI_SQL学习练习清单.md` 从 JOIN → CTE → 窗口函数梯度写
- DAX 侧：照 `study_powerbi_demodata_DAX度量值清单.md` 建度量值、用 `EVALUATE` 验证
- **建议先 SQL 跑出数字，再用 DAX 复现对拍**，理解筛选上下文最快

---

## ⚠️ 两个关键口径（坑）

1. **有效销售必须过滤 `status = '已完成'`** —— 已取消 / 退款订单金额仍保留在表里，不过滤会虚高。
2. **金额只从 `fact_order_item` 取** —— 别同时把 `fact_order.order_amount` 也求和，否则会翻倍（两张表都已含订单金额）。

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
