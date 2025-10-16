# 产品价格系统说明

## 📊 双层价格体系

### 1️⃣ 基础价格（Product Base Price）

**位置**：产品主表单 → "基础价格信息"

**字段**：
- `base_price` - 基础价格（成人）
- `child_price` - 儿童价格
- `infant_price` - 婴儿价格
- `single_room_supplement` - 单房差
- `currency` - 货币单位

**用途**：
- ✅ **默认价格**：当没有匹配的价格变体时使用
- ✅ **快速报价**：初步预算、咨询阶段
- ✅ **兜底价格**：确保产品始终有价格可用

**适用场景**：
```
简单产品：固定价格，不分淡旺季
示例：机场接送、单程巴士票
```

---

### 2️⃣ 价格变体（Price Variants）

**位置**：产品编辑页面 → "价格变体管理（条件价格）"

**字段**：
- `variant_name` - 变体名称
- `start_date` / `end_date` - 日期范围
- `min_pax` / `max_pax` - 人数范围
- `adult_price` / `child_price` / `infant_price` / `single_room_supplement` - 价格
- `currency` - 货币
- `is_active` - 启用状态

**用途**：
- ✅ **条件价格**：根据日期、人数动态定价
- ✅ **精准报价**：正式订单、合同签订
- ✅ **灵活管理**：可随时启用/禁用

**适用场景**：
```
复杂产品：淡旺季价格、团队优惠
示例：
- 淡季（1-3月）2-10人：SGD 800
- 旺季（10-12月）2-10人：SGD 1200
- 大团优惠（11+人）：SGD 900
```

---

## 🔄 价格获取逻辑

### 优先级规则

```
1. 查找匹配的价格变体
   ├─ 日期匹配（start_date <= 查询日期 <= end_date）
   ├─ 人数匹配（min_pax <= 人数 <= max_pax）
   └─ 启用状态（is_active = true）
   
2. 如果找到匹配变体
   └─ 返回变体价格
   
3. 如果没有匹配变体
   └─ 返回基础价格（base_price）
```

### Python 伪代码

```python
def get_product_price(product_id, travel_date, pax_count):
    """
    获取产品价格
    
    Args:
        product_id: 产品ID
        travel_date: 出行日期
        pax_count: 人数
        
    Returns:
        {
            'adult_price': float,
            'child_price': float,
            'source': 'variant' | 'base'  # 价格来源
        }
    """
    # 1. 查找匹配的价格变体
    variant = ProductPriceVariant.query.filter(
        ProductPriceVariant.product_id == product_id,
        ProductPriceVariant.is_active == True,
        ProductPriceVariant.start_date <= travel_date,
        ProductPriceVariant.end_date >= travel_date,
        ProductPriceVariant.min_pax <= pax_count,
        or_(
            ProductPriceVariant.max_pax >= pax_count,
            ProductPriceVariant.max_pax == None
        )
    ).order_by(
        # 优先匹配最精确的变体
        ProductPriceVariant.start_date.desc()
    ).first()
    
    # 2. 如果找到变体，使用变体价格
    if variant:
        return {
            'adult_price': variant.adult_price,
            'child_price': variant.child_price,
            'infant_price': variant.infant_price,
            'single_room_supplement': variant.single_room_supplement,
            'currency': variant.currency,
            'source': 'variant',
            'variant_name': variant.variant_name
        }
    
    # 3. 否则使用基础价格
    product = Product.query.get(product_id)
    return {
        'adult_price': product.base_price,
        'child_price': product.child_price,
        'infant_price': product.infant_price,
        'single_room_supplement': product.single_room_supplement,
        'currency': product.currency,
        'source': 'base'
    }
```

---

## 💡 使用建议

### 场景1：固定价格产品

**只设置基础价格，不创建价格变体**

```
产品：机场接送
基础价格（成人）：SGD 50
儿童价格：SGD 30
```

✅ **优点**：简单、快速

---

### 场景2：季节性价格产品

**设置基础价格 + 创建季节价格变体**

```
产品：新加坡3日游
基础价格：SGD 1000（平季参考价）

价格变体：
1. 淡季价格（1-3月）：SGD 800
2. 旺季价格（10-12月）：SGD 1200
```

✅ **优点**：
- 基础价格作为兜底
- 变体处理特殊时段

---

### 场景3：复杂定价产品

**设置基础价格 + 创建多个变体**

```
产品：泰国5日游
基础价格：SGD 1200（2人成团价）

价格变体：
1. 淡季小团（1-3月，2-5人）：SGD 1000
2. 淡季大团（1-3月，6+人）：SGD 900
3. 旺季小团（10-12月，2-5人）：SGD 1400
4. 旺季大团（10-12月，6+人）：SGD 1300
```

✅ **优点**：
- 精准控制每种组合的价格
- 灵活应对市场变化

---

## ❓ 常见问题

### Q1: 基础价格可以不填吗？

**A**: 技术上可以（字段允许为空），但**不推荐**。

**理由**：
- ❌ 如果没有基础价格且没有匹配变体，产品将无价格可用
- ✅ 建议至少设置一个参考价格作为兜底

---

### Q2: 价格变体的日期可以留空吗？

**A**: 可以。

**含义**：
- `start_date` 留空 = 从任意早的日期开始
- `end_date` 留空 = 直到任意晚的日期结束
- 两者都留空 = 不限日期，只按人数区分

---

### Q3: 多个变体匹配时，使用哪个？

**A**: 使用**最新创建**或**开始日期最晚**的变体。

**建议**：
- 避免创建重叠的变体
- 使用明确的日期范围和人数范围

---

### Q4: 价格变体可以禁用吗？

**A**: 可以，设置 `is_active = false`。

**效果**：
- 禁用的变体不会被匹配
- 系统会跳过该变体，继续查找其他变体或使用基础价格

---

## 📈 未来扩展

### 可能的增强功能

1. **会员等级价格**
   - 添加 `member_level` 字段
   - 不同会员级别不同价格

2. **促销折扣**
   - 添加 `discount_type` (percentage / fixed)
   - 添加 `discount_value`

3. **动态定价算法**
   - 根据库存、预订率自动调整价格
   - AI 预测最优定价

4. **货币自动转换**
   - 根据实时汇率自动转换
   - 支持多币种显示

---

## ✅ 总结

| 特性 | 基础价格 | 价格变体 |
|------|---------|---------|
| **用途** | 默认价格 | 条件价格 |
| **复杂度** | 简单 | 复杂 |
| **灵活性** | 低 | 高 |
| **适用场景** | 固定价格产品 | 动态定价产品 |
| **必填** | 建议必填 | 可选 |
| **优先级** | 低（兜底） | 高（优先匹配） |

**核心原则**：
- ✅ 基础价格是**兜底保障**
- ✅ 价格变体是**精准工具**
- ✅ 两者配合使用，灵活应对各种场景

---

**创建时间**: 2025-10-16  
**版本**: v1.0  
**状态**: ✅ 已实施

