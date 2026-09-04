# Python 零基础 → 精通教程

一份写给「要用 Python 干活的人」的教程，共 14 章。和同目录的 `powerbi-tutorial/`、`sql-tutorial/` 是**一套数据、三种视角**：

- `sql-tutorial/` —— 用 SQL 把数据**查出来**
- `powerbi-tutorial/` —— 用 Power BI 把数据**做成报表**
- **本教程** —— 用 Python 把数据**自动化处理掉**：读库、清洗、计算、出图、导出 Excel、定时跑

配套数据库同样是 `study_powerbi_demodata`（电商订单星型模型，共 **13,780 行**）。ch12 之后的所有示例都连真实 MySQL，**跑出来的数字可以和 SQL 教程逐项对拍**——同一笔销售额，你用 SQL 算一遍、用 pandas 再算一遍，两个数字必须一模一样。

---

## 一、这份教程的定位

| 它是什么 | 它不是什么 |
|---|---|
| 讲**为什么这么写**、**什么时候用**、**跑出来对不对** | 不是语法速查表（那种东西一搜就有） |
| 每章有可复现的示例 + 带预期输出的练习 | 不是「打印 Hello World」就完事的入门书 |
| 全程用**制造业/业务语境**（静音球、料号、毛利率、订单） | 不是算法竞赛 / 造轮子教程 |
| 最终指向**可交付的自动化脚本** | 不是只讲语法不讲工程 |

**特别适合**：制造业 / 业务岗转数据分析、甲方 IT、需要给客户交付脚本与报表的实施顾问（FDE）。

**不适合**：想学爬虫破解、想做 Web 后端、想刷 LeetCode 的人。

---

## 二、环境前置（本机已全部就位）

| 项目 | 版本 | 说明 |
|---|---|---|
| Python | **3.13.14** | 隔离虚拟环境，不污染系统 Python |
| 虚拟环境 | `C:\Users\HC\.workbuddy\binaries\python\envs\default` | PyCharm 里把这个解释器挂上即可 |
| 编辑器 | **PyCharm** | 右键 Run、Python Console、断点调试 |
| pandas | 3.0.5 | ch12 起用。注意 3.0 里字符串列 dtype 显示为 `str` 而非 `object` |
| numpy | 2.5.1 | pandas 底层依赖 |
| matplotlib | 3.11.1 | ch14 出图 |
| PyMySQL | 1.2.0 | ch13 连 MySQL（**没装 SQLAlchemy，教程全程用原生 pymysql**） |
| openpyxl | 3.1.5 | 读写 .xlsx |
| requests | 2.34.2 | 调 HTTP 接口（FDE 现场最常用） |
| MySQL | 8.0.12 | `127.0.0.1:3306`，root/root，utf8mb4 |

> ⚠️ **本机 MySQL 不在 Windows 服务里**：装在小皮面板（phpStudy）下 `D:\XPMB\phpstudy_pro\Extensions\MySQL8.0.12\`。**电脑重启 / 隔夜后不会自动启动**，ch13 连不上时先手动启动：
> ```bash
> cd "/d/XPMB/phpstudy_pro/Extensions/MySQL8.0.12/bin"
> ./mysqld.exe --defaults-file="D:/XPMB/phpstudy_pro/Extensions/MySQL8.0.12/my.ini" --console
> ```

---

## 三、三步起步

```bash
# 1. 确认解释器与版本
C:/Users/HC/.workbuddy/binaries/python/envs/default/Scripts/python.exe -V
# → Python 3.13.14

# 2. 确认包齐全
C:/Users/HC/.workbuddy/binaries/python/envs/default/Scripts/python.exe -m pip list

# 3. 确认 MySQL 活着（ch13 才需要）
mysql -uroot -proot -e "SELECT COUNT(*) FROM study_powerbi_demodata.fact_order"
```

然后随便建个 `hello.py`，右键 Run，看到输出就算起步成功。→ [ch01](./ch01_环境搭建与运行方式.md)

---

## 四、章节地图

| 章 | 标题 | 学完能做什么 | 依赖 |
|---:|---|---|---|
| ch01 | 环境搭建与运行方式 | 装环境、跑脚本、装包、看懂报错 | — |
| ch02 | 变量与数据类型 | 存数、算数、躲开浮点陷阱 | ch01 |
| ch03 | 字符串与格式化 | 清洗料号、拼中文报表、f-string 全用法 | ch02 |
| ch04 | 列表与元组 | 批量存数据、切片、躲开引用陷阱 | ch02 |
| ch05 | 字典与集合 | 键值映射、分组计数、去重 | ch02 |
| ch06 | 流程控制与推导式 | 判断、循环、一行生成新列表 | ch02-05 |
| ch07 | 函数 | 封装复用、装饰器、递归 | ch02-06 |
| ch08 | 异常与文件读写 | 程序不崩、读写 txt/json/csv/Excel | ch04-07 |
| ch09 | 模块、包与标准库 | 拆文件、用 datetime/re/itertools 等轮子 | ch07-08 |
| ch10 | 面向对象与 dataclass | 建业务对象、继承、魔术方法 | ch07-09 |
| ch11 | 迭代器/生成器/装饰器/上下文 | 省内存、造计时器、优雅收尾 | ch07-10 |
| ch12 | pandas 数据分析入门 | 读表、筛选、groupby、merge、处理缺失 | ch04-09 |
| ch13 | 连接 MySQL 实战分析 | 用 pandas 读库，算出和 SQL 一致的数字 | ch12 |
| ch14 | 可视化、导出与工程化 | 出中文图表、导 Excel 多 sheet、logging/调试规范 | ch13 |

---

## 五、三条学习路径

**路径 A：速通（约 4 小时）** — 已会基础语法，只想补 pandas 和实战
`ch02 → ch06 → ch07 → ch12 → ch13 → ch14`

**路径 B：完整（约 20 小时）** — 从零开始，一篇不落
按 ch01 → ch14 顺序全读，每章做完 5 道练习题。

**路径 C：按目标反查**

| 你想解决的问题 | 看哪章 |
|---|---|
| 装环境 / 装包 / 脚本跑不起来 | ch01 |
| 金额算出来是 0.30000000000000004 | ch02 |
| 料号、中文文本要清洗 | ch03 |
| 一批数据要批量处理 | ch04、ch06 |
| 要按品类/省份分组统计 | ch05、ch12 |
| 代码复制粘贴一大堆、改一处要改 N 处 | ch07、ch09 |
| 程序一出错就崩、数据读不出来 | ch08 |
| 要读写 Excel / CSV / JSON | ch08、ch14 |
| 业务对象很多（产品/订单/客户） | ch10 |
| 数据太大内存爆了 | ch11 |
| 要用 Python 做和 SQL 一样的分析 | ch12、ch13 |
| 要出图、出 Excel 报表给老板 | ch14 |
| 脚本要长期跑、要交给别人维护 | ch14 |

---

## 六、与现有资料的分工（重要）

上层目录已有 5 份资料，本教程**不重复**它们，只讲原理与操作，需要细节时链过去。

| 资料 | 定位 | 什么时候查 |
|---|---|---|
| [`../study_powerbi_demodata_数据字典.md`](../study_powerbi_demodata_数据字典.md) | 字段、外键、计算口径字典 | ch13 忘了某个字段是什么意思 |
| [`../study_powerbi_demodata_DAX度量值清单.md`](../study_powerbi_demodata_DAX度量值清单.md) | 24 个 DAX 度量值 | 想用 DAX 复现同一指标三方对拍 |
| [`../PowerBI_SQL学习练习清单.md`](../PowerBI_SQL学习练习清单.md) | SQL 15 题 + 窗口函数速查 | 想用 SQL 先算出数字再和 pandas 对拍 |
| [`../sql-tutorial/`](../sql-tutorial/README.md) | SQL 教程 12 章 | ch13 数字对不上时，回 SQL 教程查口径 |
| [`../generate_powerbi_demo.py`](../generate_powerbi_demo.py) | 建库脚本 | 想重建数据、看数据是怎么造出来的 |

> 一句话：**SQL 负责「查」、pandas 负责「算」、Power BI 负责「看」，三者数字必须一致。**

---

## 七、八条统一口径（全教程一致，不许出现第二种说法）

| # | 口径 | 具体值 |
|---:|---|---|
| 1 | 解释器 | Python **3.13.14**，虚拟环境 `envs\default`，编辑器 **PyCharm** |
| 2 | 数据规模 | **13,780 行**（维度 1,806 + 事实 11,974）。⚠️ 上层两份教程写的 15,780 是加总笔误，已修正 |
| 3 | **有效销售** | 必须 `status == '已完成'`：2,366 单 / 销售额 **7,195,492.73** / 利润 **1,706,864.78** / 销量 8,626 |
| 4 | 三大比率 | 毛利率 **23.72%**、客单价 **3,041.21**、单件利润 197.87 |
| 5 | 品类毛利率（成交口径） | 数码 **1.16%** < 食品 **21.75%** < 家居 **27.22%** < 服饰 **38.00%** < 美妆 **49.47%** |
| 6 | 省份 TOP | 广东 **1,078,152.70** > 浙江 849,660.63 > 上海 816,614.17 > 江苏 800,322.96 > 北京 761,942.54 |
| 7 | 客户 TOP5 | 梁诗 70,022.89 / 唐宇伟 67,890.55 / 马晨博 66,012.90 / 吴涛 65,767.42 / 彭艳鑫 61,699.01（全为钻石） |
| 8 | 代码风格 | 中文变量名可用但**类名/函数名一律英文**；金额一律 `round(x, 2)`；注释用中文；`pandas` 简写 `pd`、`matplotlib.pyplot` 简写 `plt` |

**业务语境统一**：示例里的产品用公司的真实品类——静音球（料号如 `ST-BD-42`、`ST-BD-60`）、泳镜、球类；品类用演示库的数码/食品/家居/服饰/美妆。

---

## 八、关于练习题

每章末尾 **5 题**，全部附**完整答案代码 + 逐步解析 + 预期输出**。

用法建议：

1. 先自己写，在 PyCharm 里跑
2. 卡住再看 Hint
3. 跑出结果后和「预期输出」对拍
4. 对不上就按「解析」一步步查

> 输出对不上**不是失败**，是最有价值的学习时刻——通常意味着你对「可变对象引用」「浮点精度」或「分组口径」的理解还差一层。

---

## 九、常见故障速查

| 现象 | 原因 / 解决 |
|---|---|
| `'python' 不是内部或外部命令` | 没用虚拟环境的完整路径，或 PyCharm 解释器没指向 `envs\default` |
| `ModuleNotFoundError: No module named 'pandas'` | 包装在系统 Python 里了 → 用 `envs\default\Scripts\python.exe -m pip install pandas` |
| `pip install` 很慢 / 超时 | 加清华源：`pip install pandas -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| `UnicodeDecodeError: gbk codec` | 读中文文件没写 `encoding="utf-8"`（ch08） |
| 写出的 CSV 用 Excel 打开乱码 | 用 `encoding="utf-8-sig"`（ch08） |
| 中文图表显示成方块 | 没设字体：`plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]`（ch14） |
| 负号显示成方块 | 加 `plt.rcParams["axes.unicode_minus"] = False`（ch14） |
| `0.1 + 0.2 == 0.3` 是 False | 浮点精度问题，用 `math.isclose()` 或 `Decimal`（ch02） |
| 改了列表 a，b 也跟着变 | 同一个对象的两个名字，用 `b = a.copy()`（ch04） |
| `KeyError: 'xxx'` | 字典键不存在，用 `d.get('xxx', 默认值)`（ch05） |
| pandas 里 `SettingWithCopyWarning` | 链式赋值 → 用 `.loc[]` 或先 `.copy()`（ch12） |
| `Can't connect to MySQL server` | MySQL 没启动 → 开小皮面板或手动 `mysqld.exe --console`（ch13） |
| pandas 读库报 `UserWarning: pandas only supports SQLAlchemy` | 正常警告，pymysql 连接可用，忽略即可（ch13） |

---

## 十、更新记录

| 日期 | 内容 |
|---|---|
| 2026-09-04 | 初版：14 章全部完成，所有示例输出经本机 Python 3.13.14 + MySQL 实跑验证；ch13 数字与 SQL 教程逐项对拍通过 |

---

## 下一步

→ [ch01 环境搭建与运行方式](./ch01_环境搭建与运行方式.md)
