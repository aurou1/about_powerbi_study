# -*- coding: utf-8 -*-
"""
生成 Power BI + SQL 学习用 MySQL 演示库
库名: study_powerbi_demodata  (电商订单星型模型, 约 1.4 万行)
环境: MySQL 8.0 / utf8mb4 / InnoDB
依赖: pymysql  (pip install pymysql)

运行: python generate_powerbi_demo.py
连接信息改下面的 DB_CONFIG 即可。
"""
import pymysql
import random
import calendar
from datetime import date

# ============ 连接配置（按你给的信息）============
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "root",
    "charset": "utf8mb4",
}
DB_NAME = "study_powerbi_demodata"

random.seed(20260903)  # 固定随机种子，保证可复现

# ============ 数据池 ============
REGIONS = [
    ("广东", "华南"), ("江苏", "华东"), ("浙江", "华东"), ("上海", "华东"),
    ("北京", "华北"), ("山东", "华东"), ("四川", "西南"), ("湖北", "华中"),
    ("辽宁", "东北"), ("陕西", "西北"),
]
REGION_WEIGHTS = [12, 10, 10, 11, 8, 9, 7, 6, 5, 5]  # 华东/华南订单更多

CATEGORIES = {
    "数码": {"brands": ["极光", "云米", "星河"], "margin": 0.12, "price": (199, 3999)},
    "家居": {"brands": ["木语", "暖居", "简一"], "margin": 0.35, "price": (49, 1299)},
    "服饰": {"brands": ["风行", "素白", "墨痕"], "margin": 0.45, "price": (59, 899)},
    "食品": {"brands": ["田园", "鲜踪", "谷舍"], "margin": 0.30, "price": (9, 299)},
    "美妆": {"brands": ["花漾", "肌研", "琉光"], "margin": 0.55, "price": (39, 699)},
}
PRODUCT_NAMES = {
    "数码": ["无线蓝牙耳机", "智能手表", "蓝牙音箱", "移动电源", "机械键盘", "电竞鼠标", "降噪头戴", "智能手环"],
    "家居": ["北欧台灯", "收纳箱", "加湿器", "香薰机", "陶瓷餐具", "懒人沙发", "记忆棉枕", "羊毛毯"],
    "服饰": ["纯棉T恤", "牛仔裤", "连帽卫衣", "风衣", "运动短裤", "针织衫", "羽绒服", "帆布鞋"],
    "食品": ["坚果礼盒", "挂耳咖啡", "手工饼干", "果干混合", "燕麦片", "黑巧克力", "椴树蜂蜜", "麻辣零食"],
    "美妆": ["保湿面霜", "烟酰胺精华", "丝绒口红", "气垫BB", "氨基酸卸妆水", "补水面膜", "淡香水", "防晒乳"],
}
SURNAMES = list("王李张刘陈杨黄赵周吴徐孙马朱胡郭何高林郑谢罗梁宋唐许韩冯邓曹彭曾")
GIVEN = list("伟芳娜秀英敏静丽强磊军洋勇艳杰娟涛明超霞平刚桂兰鑫宇浩晨悦诗涵梓睿欣妍博文")
CITIES = {
    "广东": ["广州", "深圳", "东莞", "佛山"], "江苏": ["南京", "苏州", "无锡"],
    "浙江": ["杭州", "宁波", "温州"], "上海": ["上海"], "北京": ["北京"],
    "山东": ["济南", "青岛"], "四川": ["成都", "绵阳"], "湖北": ["武汉", "宜昌"],
    "辽宁": ["沈阳", "大连"], "陕西": ["西安", "咸阳"],
}
STATUS_POOL = ["已完成", "已完成", "已完成", "已完成", "已取消", "退款"]
PAYMENT_POOL = ["微信", "支付宝", "银行卡"]
TIERS = ["普通", "银卡", "金卡", "钻石"]
TIER_WEIGHTS = [50, 30, 15, 5]
# 每个等级客户生成的订单数（钻石最多，制造消费分层）
TIER_ORDER_COUNT = {"钻石": 25, "金卡": 12, "银卡": 6, "普通": 4}
# 折扣率随等级提高
TIER_DISCOUNT = {"钻石": 0.20, "金卡": 0.15, "银卡": 0.08, "普通": 0.02}
# 月份季节性权重（6月618、11/12双11双12更高）
MONTH_W = [8, 7, 8, 8, 9, 14, 8, 8, 9, 9, 16, 15]

# ============ 工具函数 ============
def rand_date_in_range(years=(2023, 2024, 2025)):
    year = random.choice(years)
    month = random.choices(range(1, 13), weights=MONTH_W)[0]
    last = calendar.monthrange(year, month)[1]
    return date(year, month, random.randint(1, last))

def rand_name():
    return random.choice(SURNAMES) + "".join(random.choice(GIVEN) for _ in range(random.randint(1, 2)))

# ============ 主流程 ============
def main():
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()

    print(">> 重建数据库 ...")
    cur.execute(f"DROP DATABASE IF EXISTS `{DB_NAME}`")
    cur.execute(f"CREATE DATABASE `{DB_NAME}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci")
    cur.execute(f"USE `{DB_NAME}`")

    print(">> 建表 ...")
    cur.execute("""
    CREATE TABLE dim_region (
      region_id INT PRIMARY KEY AUTO_INCREMENT,
      province_name VARCHAR(20) NOT NULL,
      zone VARCHAR(10) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    cur.execute("""
    CREATE TABLE dim_product (
      product_id INT PRIMARY KEY,
      product_name VARCHAR(50) NOT NULL,
      category VARCHAR(20) NOT NULL,
      brand VARCHAR(20) NOT NULL,
      cost_price DECIMAL(10,2) NOT NULL,
      list_price DECIMAL(10,2) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    cur.execute("""
    CREATE TABLE dim_customer (
      customer_id INT PRIMARY KEY,
      customer_name VARCHAR(30) NOT NULL,
      gender CHAR(1) NOT NULL,
      city VARCHAR(20) NOT NULL,
      region_id INT NOT NULL,
      register_date DATE NOT NULL,
      tier VARCHAR(10) NOT NULL,
      KEY idx_region (region_id),
      CONSTRAINT fk_cust_region FOREIGN KEY (region_id) REFERENCES dim_region(region_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    cur.execute("""
    CREATE TABLE dim_date (
      date_key DATE PRIMARY KEY,
      year INT NOT NULL,
      quarter INT NOT NULL,
      month INT NOT NULL,
      month_name VARCHAR(10) NOT NULL,
      week_of_year INT NOT NULL,
      day_of_week INT NOT NULL,
      weekday_name VARCHAR(10) NOT NULL,
      is_weekend TINYINT NOT NULL,
      is_holiday TINYINT NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    cur.execute("""
    CREATE TABLE fact_order (
      order_id INT PRIMARY KEY,
      customer_id INT NOT NULL,
      region_id INT NOT NULL,
      order_date DATE NOT NULL,
      status VARCHAR(10) NOT NULL,
      payment_method VARCHAR(10) NOT NULL,
      order_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
      order_profit DECIMAL(12,2) NOT NULL DEFAULT 0,
      KEY idx_cust (customer_id),
      KEY idx_region (region_id),
      KEY idx_date (order_date),
      CONSTRAINT fk_ord_cust FOREIGN KEY (customer_id) REFERENCES dim_customer(customer_id),
      CONSTRAINT fk_ord_region FOREIGN KEY (region_id) REFERENCES dim_region(region_id),
      CONSTRAINT fk_ord_date FOREIGN KEY (order_date) REFERENCES dim_date(date_key)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    cur.execute("""
    CREATE TABLE fact_order_item (
      order_item_id INT PRIMARY KEY,
      order_id INT NOT NULL,
      product_id INT NOT NULL,
      quantity INT NOT NULL,
      unit_price DECIMAL(10,2) NOT NULL,
      unit_cost DECIMAL(10,2) NOT NULL,
      discount_rate DECIMAL(5,2) NOT NULL,
      line_amount DECIMAL(12,2) NOT NULL,
      line_profit DECIMAL(12,2) NOT NULL,
      KEY idx_ord (order_id),
      KEY idx_prod (product_id),
      CONSTRAINT fk_item_ord FOREIGN KEY (order_id) REFERENCES fact_order(order_id),
      CONSTRAINT fk_item_prod FOREIGN KEY (product_id) REFERENCES dim_product(product_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # ---- dim_region ----
    cur.executemany("INSERT INTO dim_region (province_name, zone) VALUES (%s,%s)", REGIONS)
    region_ids = list(range(1, len(REGIONS) + 1))

    # ---- dim_date (2023-01-01 ~ 2025-12-31) ----
    d = date(2023, 1, 1)
    end = date(2025, 12, 31)
    date_rows = []
    while d <= end:
        q = (d.month - 1) // 3 + 1
        woy = d.isocalendar()[1]
        dow = d.weekday() + 1  # 1=Mon
        wkname = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][d.weekday()]
        is_holiday = 1 if (d.month, d.day) in {(1, 1), (5, 1), (10, 1)} else 0
        date_rows.append((d, d.year, q, d.month, f"{d.year}年{d.month}月", woy, dow, wkname,
                          1 if d.weekday() >= 5 else 0, is_holiday))
        d += __import__("datetime").timedelta(days=1)
    cur.executemany(
        "INSERT INTO dim_date VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", date_rows)
    print(f"   dim_date: {len(date_rows)} 行")

    # ---- dim_product (200) ----
    products = []
    for pid in range(1, 201):
        cat = random.choice(list(CATEGORIES))
        info = CATEGORIES[cat]
        brand = random.choice(info["brands"])
        pname = random.choice(PRODUCT_NAMES[cat])
        cost = round(random.uniform(*info["price"]), 2)
        price = round(cost / (1 - info["margin"]), 2)  # 反推吊牌价使毛利率=margin
        products.append((pid, f"{brand}{pname}", cat, brand, cost, price))
    cur.executemany(
        "INSERT INTO dim_product VALUES (%s,%s,%s,%s,%s,%s)", products)
    prod_by_id = {p[0]: p for p in products}
    print(f"   dim_product: {len(products)} 行")

    # ---- dim_customer (500) ----
    customers = []
    cust_region = {}
    cid = 1
    for _ in range(500):
        ridx = random.choices(range(len(REGIONS)), weights=REGION_WEIGHTS)[0]
        rid = region_ids[ridx]
        prov = REGIONS[ridx][0]
        tier = random.choices(TIERS, weights=TIER_WEIGHTS)[0]
        customers.append((cid, rand_name(), random.choice(["男", "女"]),
                          random.choice(CITIES[prov]), rid,
                          rand_date_in_range((2022, 2023)), tier))
        cust_region[cid] = (rid, tier)
        cid += 1
    cur.executemany(
        "INSERT INTO dim_customer VALUES (%s,%s,%s,%s,%s,%s,%s)", customers)
    print(f"   dim_customer: {len(customers)} 行")

    # ---- fact_order + fact_order_item ----
    orders = []
    items = []
    order_id = 1
    item_id = 1
    order_sum = {}  # order_id -> (amount, profit)
    for c in customers:
        cid = c[0]
        rid, tier = cust_region[cid]
        n_orders = TIER_ORDER_COUNT[tier]
        disc = TIER_DISCOUNT[tier]
        for _ in range(n_orders):
            odate = rand_date_in_range()
            odate = max(odate, c[5])  # 下单不早于注册
            status = random.choice(STATUS_POOL)
            pay = random.choice(PAYMENT_POOL)
            orders.append((order_id, cid, rid, odate, status, pay, 0, 0))
            amt = 0.0
            prof = 0.0
            n_items = random.choices([1, 2, 3, 4, 5], weights=[30, 30, 20, 12, 8])[0]
            for _ in range(n_items):
                pid = random.randint(1, 200)
                p = prod_by_id[pid]
                qty = random.choices([1, 2, 3], weights=[70, 22, 8])[0]
                # 食品/低单价更易多买
                if p[2] == "食品":
                    qty = random.choices([1, 2, 3, 4], weights=[40, 30, 20, 10])[0]
                line_disc = round(max(0.0, disc + random.uniform(-0.03, 0.03)), 2)
                uprice = p[5]
                ucost = p[4]
                line_amt = round(qty * uprice * (1 - line_disc), 2)
                line_prof = round(line_amt - qty * ucost, 2)
                items.append((item_id, order_id, pid, qty, uprice, ucost, line_disc, line_amt, line_prof))
                amt += line_amt
                prof += line_prof
                item_id += 1
            # 表头金额恒等于明细汇总（保证自洽）；状态差异用 status 字段体现，
            # 算"有效销售额"时在 SQL / Power BI 里加 WHERE status='已完成' 即可。
            order_sum[order_id] = (round(amt, 2), round(prof, 2))
            order_id += 1

    print(f"   生成 fact_order: {len(orders)} 行, fact_order_item: {len(items)} 行")

    # 回填 order 头金额
    orders_final = []
    for o in orders:
        oid = o[0]
        a, p = order_sum.get(oid, (0, 0))
        orders_final.append((o[0], o[1], o[2], o[3], o[4], o[5], a, p))

    cur.executemany("INSERT INTO fact_order VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", orders_final)
    # 分批插明细，避免单包过大
    batch = 2000
    for i in range(0, len(items), batch):
        cur.executemany(
            "INSERT INTO fact_order_item VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            items[i:i + batch])
    conn.commit()

    # ---- 校验行数 ----
    print(">> 校验 ...")
    for t in ["dim_region", "dim_product", "dim_customer", "dim_date", "fact_order", "fact_order_item"]:
        cur.execute(f"SELECT COUNT(*) FROM `{t}`")
        print(f"   {t}: {cur.fetchone()[0]} 行")

    cur.close()
    conn.close()
    print(">> 完成。数据库", DB_NAME, "已生成。")


if __name__ == "__main__":
    main()
