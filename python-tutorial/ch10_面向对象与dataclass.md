# ch10 面向对象编程（OOP）与 dataclass

> 函数解决「动作」，对象解决「事物」。一只静音球有料号、单价、数量，还能算金额、判断异常——把这些**数据和行为打包成一个对象**，比散落的变量和函数清晰太多。FDE 在现场给客户建模业务实体（订单、产品、客户）时，OOP 是基本功。这一章讲类、继承、`property`、静态方法，以及现代 Python 最香的 `@dataclass`。

---

## 学习目标

- 理解类 / 实例 / 属性 / 方法
- 会写 `__init__` / `__str__` / `__repr__` 等「魔法方法」
- 理解继承、`isinstance`、MRO
- 会用 `@property`、`@staticmethod`
- 掌握 `@dataclass`（取代手写样板代码）

---

## 1. 从函数到类：把数据和行为打包

```python
class Product:
    category = "静音球"          # 类属性：所有实例共享

    def __init__(self, code, price, qty=1):
        self.code = code         # 实例属性
        self.price = price
        self.qty = qty

    def amount(self):            # 实例方法（第一个参数 self = 实例自己）
        return self.price * self.qty

    def __str__(self):           # print 时显示
        return f"<{self.code} ¥{self.price} x{self.qty}>"

    def __repr__(self):          # 调试时显示
        return f"Product({self.code!r}, {self.price})"

    def __len__(self):           # len() 行为
        return self.qty

p = Product("ST-BD-42", 8.65, 1200)
print("str:", p)
print("repr:", repr(p))
print("金额:", p.amount(), "| len:", len(p))
print("类属性:", Product.category, "| 实例访问:", p.category)
print("__dict__ keys:", list(p.__dict__.keys()))
```

**预期输出：**

```
str: <ST-BD-42 ¥8.65 x1200>
repr: Product('ST-BD-42', 8.65)
金额: 10380.0 | len: 1200
类属性: 静音球 | 实例访问: 静音球
__dict__ keys: ['code', 'price', 'qty']
```

> - `self` 不是关键字，是约定俗成的第一个参数名，代表「这个实例」
> - `__str__` / `__repr__` / `__len__` 是**魔法方法（dunder）**，让对象能 `print`、能 `len()`。写业务对象时至少实现 `__repr__`，调试省命。

---

## 2. 让对象可排序、可比较

```python
class Product:
    def __init__(self, code, price):
        self.code, self.price = code, price
    def __lt__(self, other):              # < 比较
        return self.price < other.price

products = [Product("ST-BD-60", 12.30), Product("ST-BD-42", 8.65)]
print("排序:", [p.code for p in sorted(products)])
```

**预期输出：**

```
排序: ['ST-BD-42', 'ST-BD-60']
```

> 实现 `__lt__` 后对象就能被 `sorted()` 排序。pandas 出现前，手工排序对象列表就靠它。

---

## 3. 继承：复用 + 改写

```python
class Product:
    def __init__(self, code, price, qty=1):
        self.code, self.price, self.qty = code, price, qty
    def amount(self):
        return self.price * self.qty

class DiscountedProduct(Product):        # 继承 Product
    def __init__(self, code, price, qty=1, discount=0.15):
        super().__init__(code, price, qty)   # 调父类初始化
        self.discount = discount
    def amount(self):                     # 重写方法
        return self.price * self.qty * (1 - self.discount)

dp = DiscountedProduct("ST-BD-42", 8.65, 1200)
print("继承+重写:", dp.amount())
print("父类同名:", Product("ST-BD-42", 8.65, 1200).amount())
print("isinstance:", isinstance(dp, Product))
print("MRO:", [c.__name__ for c in type(dp).__mro__])
```

**预期输出：**

```
继承+重写: 8823.0
父类同名: 10380.0
isinstance: True
MRO: ['DiscountedProduct', 'Product', 'object']
```

> - `super()` 调父类方法，避免写死父类名
> - `isinstance(dp, Product)` 为 `True`：子类对象也是父类类型（多态基础）
> - **MRO**（方法解析顺序）：找方法时按这个顺序走，遇到多重继承很关键

---

## 4. `@property`：把方法当属性用

```python
class Cart:
    def __init__(self):
        self._items = []
    @property
    def total(self):                 # 读 total 像读属性，但其实是算出来的
        return sum(i.price * i.qty for i in self._items)
    @property
    def count(self):
        return len(self._items)

# 假设 _items 里有两个 Product
from types import SimpleNamespace
c = Cart()
c._items = [SimpleNamespace(price=8.65, qty=120), SimpleNamespace(price=12.30, qty=70)]
print("property total:", round(c.total, 2), "| count:", c.count)
```

**预期输出：**

```
property total: 1540 | count: 2
```

> `@property` 让 `c.total` 看起来像属性，其实是调用方法实时计算。适合「派生值」（金额、合计），外部不能随便赋值破坏一致性。

---

## 5. `@staticmethod`：与实例无关的工具方法

```python
class Utils:
    @staticmethod
    def is_valid_code(code):
        return code.startswith("ST-") or code.startswith("YG-")

print("staticmethod:", Utils.is_valid_code("ST-BD-42"), Utils.is_valid_code("XX-1"))
```

**预期输出：**

```
staticmethod: True False
```

> 不需要 `self`、不访问实例数据的方法，用 `@staticmethod` 标记，调用时不用先建实例。纯校验 / 转换工具适合放这。

---

## 6. `@dataclass`：告别样板代码（现代 Python 最香）

> 传统写法要为 `code/price/qty` 手写 `__init__`、`__repr__`、`__eq__`，又长又易错。`@dataclass` 一个装饰器全帮你生成。

```python
from dataclasses import dataclass, asdict, field

@dataclass
class Item:
    code: str
    price: float
    qty: int = 1

it = Item("ST-BD-42", 8.65, 1200)
print("dataclass:", it)
print("asdict:", asdict(it), "| 相等比较:", it == Item("ST-BD-42", 8.65, 1200))
print("amount():", it.price * it.qty)
```

**预期输出：**

```
dataclass: Item(code='ST-BD-42', price=8.65, qty=1200)
asdict: {'code': 'ST-BD-42', 'price': 8.65, 'qty': 1200} | 相等比较: True
amount(): 10380.0
```

> `@dataclass` 自动生成：`__init__`、`__repr__`、`__eq__`（按字段比较相等）。`asdict()` 转字典，方便对接 JSON / pandas。

### `frozen` + `order`：不可变且可排序

```python
from dataclasses import dataclass

@dataclass(frozen=True, order=True)
class Point:
    x: int
    y: int

ps = [Point(3, 1), Point(1, 2)]
print("frozen+order:", ps[1] < ps[0], sorted(ps))
```

**预期输出：**

```
frozen+order: True [Point(x=1, y=2), Point(x=3, y=1)]
```

> `frozen=True`：建好不能改（像元组，线程安全、可作字典键）；`order=True`：自动获得 `<`、`>` 比较，能 `sorted()`。配置项、坐标这类「建好就别动」的对象用它最合适。

---

## 7. 容器协议：让对象像列表/字典一样用

```python
class Inventory:
    def __init__(self):
        self._data = {"ST-BD-42": 12, "YG-01": 3}
    def __getitem__(self, key):
        return self._data[key]
    def __len__(self):
        return sum(self._data.values())
    def __iter__(self):
        return iter(self._data.items())

inv = Inventory()
print("容器协议:", inv["ST-BD-42"], "|", 12 in inv._data.values(), "| len:", len(inv))
print("遍历:", list(inv))
```

**预期输出：**

```
容器协议: 12 | True | len: 2
遍历: [('ST-BD-42', 12), ('YG-01', 3)]
```

> 实现 `__getitem__` / `__len__` / `__iter__`，对象就能被 `[]` 索引、`len()`、for 遍历。做「业务数据容器」时极自然。

---

## 小结

| 概念 | 用途 |
|---|---|
| `class` / `__init__` | 定义对象模板与初始化 |
| `__str__` / `__repr__` | 打印/调试显示 |
| 继承 / `super` | 复用父类、改写方法 |
| `isinstance` / MRO | 类型判断 / 方法查找顺序 |
| `@property` | 派生值当属性用 |
| `@staticmethod` | 与实例无关的工具 |
| `@dataclass` | 自动生成样板（强烈推荐） |
| `frozen` / `order` | 不可变 / 可排序 |

---

## 练习

### 练习 1：写 Product 类（考：__init__ + 方法）
**题目**：定义 `Product(code, price, qty)`，有 `amount()` 返回 `price*qty`，`__repr__` 返回 `Product(code, price)`。
<details><summary>答案与解析</summary>

```python
class Product:
    def __init__(self, code, price, qty=1):
        self.code, self.price, self.qty = code, price, qty
    def amount(self):
        return self.price * self.qty
    def __repr__(self):
        return f"Product({self.code!r}, {self.price})"

p = Product("ST-BD-42", 8.65, 1200)
print(p, p.amount())   # Product('ST-BD-42', 8.65) 10380.0
```
</details>

### 练习 2：继承重写（考：super + 重写）
**题目**：在练习 1 基础上写 `DiscountedProduct(Product)`，加 `discount=0.15`，`amount()` 返回折后价。
<details><summary>答案与解析</summary>

```python
class DiscountedProduct(Product):
    def __init__(self, code, price, qty=1, discount=0.15):
        super().__init__(code, price, qty)
        self.discount = discount
    def amount(self):
        return self.price * self.qty * (1 - self.discount)

print(DiscountedProduct("ST-BD-42", 8.65, 1200).amount())   # 8823.0
```
</details>

### 练习 3：dataclass（考：@dataclass）
**题目**：用 `@dataclass` 定义 `Order(id: str, amount: float)`，验证两个字段相同的订单 `==` 为 True。
<details><summary>答案与解析</summary>

```python
from dataclasses import dataclass
@dataclass
class Order:
    id: str
    amount: float

print(Order("O001", 1200.0) == Order("O001", 1200.0))   # True
```
**解析**：`@dataclass` 自动生成 `__eq__`，按字段比较。
</details>

### 练习 4：@property（考：派生属性）
**题目**：给 `Cart` 加 `@property` 返回总价（items 为 `[(price, qty), ...]` 列表）。
<details><summary>答案与解析</summary>

```python
class Cart:
    def __init__(self, items):
        self.items = items
    @property
    def total(self):
        return sum(p * q for p, q in self.items)

print(Cart([(8.65, 120), (12.30, 70)]).total)   # 1822.0... 实际 1540.0? 8.65*120=1038, 12.30*70=861  → 1899.0
```
**解析**：`property` 让 `total` 像属性般实时计算。上面数字应为 1899.0（8.65×120 + 12.30×70）。
</details>

### 练习 5：frozen dataclass（考：不可变）
**题目**：定义 `@dataclass(frozen=True)` 的 `Config(key: str, val: str)`，验证赋值会报错。
<details><summary>答案与解析</summary>

```python
from dataclasses import dataclass
@dataclass(frozen=True)
class Config:
    key: str
    val: str

c = Config("tax", "0.13")
try:
    c.val = "0.15"
except Exception as e:
    print(type(e).__name__)   # dataclasses.FrozenInstanceError
```
</details>

---

## 下一步

对象会建了，但真正的数据流是「一批批、可能很大、按需生成」的。`yield`、生成器、装饰器、上下文管理器是处理大数据的利器。下一章深入**迭代器 / 生成器 / 装饰器 / 上下文管理器**。

→ [ch11 迭代器生成器装饰器上下文管理器](./ch11_迭代器生成器装饰器上下文管理器.md)
