# tour_itinerary 表集成方案

## 📋 现有 tour_itinerary 表结构

```sql
CREATE TABLE tour_itinerary (
    id INT PRIMARY KEY AUTO_INCREMENT,
    tour_id INT NOT NULL,                    -- 外键（待确定关联对象）
    day_title VARCHAR(200) NOT NULL,         -- 第几天标题
    date DATE NOT NULL,                      -- 日期
    content TEXT NOT NULL,                   -- 行程内容
    image1 VARCHAR(500),                     -- 图片1
    image2 VARCHAR(500),                     -- 图片2
    image3 VARCHAR(500),                     -- 图片3
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

---

## 🤔 关键问题：tour_id 应该关联哪个表？

### 方案对比

| 关联对象 | 优点 | 缺点 | 适用场景 |
|---------|------|------|---------|
| **tour_group** | ✅ 实际行程<br>✅ 可修改调整<br>✅ 符合实际业务 | ⚠️ 每个团都要重新录入 | **实际出团行程** |
| **travelproducts** | ✅ 可复用<br>✅ 作为模板 | ⚠️ 无法针对具体团调整 | **标准产品模板** |
| **tour_project** | ⚠️ 项目级行程 | ❌ 粒度太粗<br>❌ 一个项目可能有多个团 | 不推荐 |
| **tour_products** | ⚠️ PDF展示用 | ❌ 已有 itinerary 字段 | 不推荐 |

---

## ✅ 推荐方案：双表设计

### 方案设计理念

```
产品模板行程 (product_itinerary)
    ↓ 复制/继承
实际团队行程 (tour_itinerary)
```

### 1. **product_itinerary** (新建) - 产品模板行程

**用途**: 存储标准产品的默认行程模板

```sql
CREATE TABLE product_itinerary (
    id INT PRIMARY KEY AUTO_INCREMENT,
    
    -- ========== 关联产品 ==========
    product_id INT NOT NULL COMMENT '产品ID',
    FOREIGN KEY (product_id) REFERENCES travelproducts(id) ON DELETE CASCADE,
    
    -- ========== 天数信息 ==========
    day_number INT NOT NULL COMMENT '第几天（1,2,3...）',
    day_title VARCHAR(200) NOT NULL COMMENT '当天标题（如：抵达新加坡）',
    
    -- ========== 行程内容 ==========
    content TEXT NOT NULL COMMENT '详细行程内容',
    activities TEXT COMMENT '活动内容',
    meals VARCHAR(100) COMMENT '用餐安排（早/午/晚）',
    accommodation VARCHAR(200) COMMENT '住宿酒店',
    transportation VARCHAR(200) COMMENT '交通方式',
    
    -- ========== 可选信息 ==========
    tips TEXT COMMENT '温馨提示',
    optional_activities TEXT COMMENT '可选活动',
    
    -- ========== 图片 ==========
    image1 VARCHAR(500) COMMENT '图片1',
    image2 VARCHAR(500) COMMENT '图片2',
    image3 VARCHAR(500) COMMENT '图片3',
    
    -- ========== 排序 ==========
    display_order INT DEFAULT 0 COMMENT '显示顺序',
    
    -- ========== 时间戳 ==========
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- ========== 索引 ==========
    INDEX idx_product_day (product_id, day_number),
    INDEX idx_display_order (display_order),
    UNIQUE KEY unique_product_day (product_id, day_number)
);
```

**作用**:
- ✅ 产品模板的标准行程
- ✅ 可在创建团队时**复制**到 tour_itinerary
- ✅ 便于维护和更新产品行程

---

### 2. **tour_itinerary** (重构) - 实际团队行程

**用途**: 存储具体团队的实际行程（可修改）

```sql
CREATE TABLE tour_itinerary (
    id INT PRIMARY KEY AUTO_INCREMENT,
    
    -- ========== 关联团队（重要修改）==========
    tour_id INT NOT NULL COMMENT '团队ID',
    FOREIGN KEY (tour_id) REFERENCES tour_group(id) ON DELETE CASCADE,
    
    -- ========== 来源追溯（新增）==========
    source_template_id INT COMMENT '来源模板ID（如果从产品模板复制）',
    FOREIGN KEY (source_template_id) REFERENCES product_itinerary(id) ON DELETE SET NULL,
    
    -- ========== 天数信息（优化）==========
    day_number INT NOT NULL COMMENT '第几天',
    day_title VARCHAR(200) NOT NULL COMMENT '当天标题',
    
    -- ========== 日期（保留）==========
    date DATE NOT NULL COMMENT '实际日期',
    
    -- ========== 行程内容（保留）==========
    content TEXT NOT NULL COMMENT '详细行程内容',
    
    -- ========== 扩展字段（新增）==========
    activities TEXT COMMENT '活动内容',
    meals VARCHAR(100) COMMENT '用餐安排',
    accommodation VARCHAR(200) COMMENT '住宿酒店',
    transportation VARCHAR(200) COMMENT '交通方式',
    tips TEXT COMMENT '温馨提示',
    
    -- ========== 图片（保留）==========
    image1 VARCHAR(500) COMMENT '图片1',
    image2 VARCHAR(500) COMMENT '图片2',
    image3 VARCHAR(500) COMMENT '图片3',
    
    -- ========== 状态（新增）==========
    status ENUM('planned','confirmed','in_progress','completed') 
        DEFAULT 'planned' COMMENT '行程状态',
    
    -- ========== 实际执行情况（新增）==========
    actual_start_time TIME COMMENT '实际开始时间',
    actual_end_time TIME COMMENT '实际结束时间',
    notes TEXT COMMENT '执行备注',
    
    -- ========== 排序 ==========
    display_order INT DEFAULT 0 COMMENT '显示顺序',
    
    -- ========== 时间戳（保留）==========
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- ========== 索引 ==========
    INDEX idx_tour_day (tour_id, day_number),
    INDEX idx_date (date),
    INDEX idx_status (status),
    INDEX idx_display_order (display_order)
);
```

**重要修改**:
1. ✅ `tour_id` 明确关联到 `tour_group.id`
2. ✅ 新增 `source_template_id` 追溯来源
3. ✅ 新增 `day_number` 便于排序
4. ✅ 新增扩展字段（meals, accommodation等）
5. ✅ 新增状态管理

---

## 🔄 业务流程

### 创建产品模板时

```
1. 创建产品 (travelproducts)
2. 添加模板行程 (product_itinerary)
   - Day 1: 抵达新加坡
   - Day 2: 市区观光
   - Day 3: 圣淘沙
```

### 创建项目和团队时

```
1. 创建项目 (tour_project)
2. 选择产品模板 (base_product_id)
3. 创建团队 (tour_group)
4. 复制行程 (product_itinerary → tour_itinerary)
   - 自动填充 source_template_id
   - 根据出发日期计算每天的 date
   - 允许后续修改
```

### 实际执行时

```
1. 查看团队行程 (tour_itinerary)
2. 可以修改具体内容（不影响模板）
3. 记录实际执行情况
4. 更新状态（planned → confirmed → in_progress → completed）
```

---

## 📊 完整关系图

```
┌──────────────────┐
│ travelproducts   │ (产品模板)
└────────┬─────────┘
         │
         │ 1:N
         ▼
┌──────────────────┐
│product_itinerary │ (模板行程 - 可复用)
└──────────────────┘
         │
         │ 复制
         ▼
┌──────────────────┐
│  tour_project    │ (项目)
└────────┬─────────┘
         │
         │ 1:N
         ▼
┌──────────────────┐
│   tour_group     │ (团队)
└────────┬─────────┘
         │
         │ 1:N
         ▼
┌──────────────────┐
│ tour_itinerary   │ (实际行程 - 可修改)
└──────────────────┘
```

---

## 🔧 迁移脚本

### 步骤1：创建 product_itinerary 表

```sql
CREATE TABLE product_itinerary (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL COMMENT '产品ID',
    day_number INT NOT NULL COMMENT '第几天',
    day_title VARCHAR(200) NOT NULL COMMENT '当天标题',
    content TEXT NOT NULL COMMENT '详细行程内容',
    activities TEXT COMMENT '活动内容',
    meals VARCHAR(100) COMMENT '用餐安排',
    accommodation VARCHAR(200) COMMENT '住宿酒店',
    transportation VARCHAR(200) COMMENT '交通方式',
    tips TEXT COMMENT '温馨提示',
    optional_activities TEXT COMMENT '可选活动',
    image1 VARCHAR(500) COMMENT '图片1',
    image2 VARCHAR(500) COMMENT '图片2',
    image3 VARCHAR(500) COMMENT '图片3',
    display_order INT DEFAULT 0 COMMENT '显示顺序',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES travelproducts(id) ON DELETE CASCADE,
    INDEX idx_product_day (product_id, day_number),
    INDEX idx_display_order (display_order),
    UNIQUE KEY unique_product_day (product_id, day_number)
) COMMENT='产品模板行程表';
```

### 步骤2：增强 tour_itinerary 表

```sql
-- 备份原表
CREATE TABLE tour_itinerary_backup AS SELECT * FROM tour_itinerary;

-- 添加新字段
ALTER TABLE tour_itinerary
ADD COLUMN source_template_id INT COMMENT '来源模板ID',
ADD COLUMN day_number INT COMMENT '第几天',
ADD COLUMN activities TEXT COMMENT '活动内容',
ADD COLUMN meals VARCHAR(100) COMMENT '用餐安排',
ADD COLUMN accommodation VARCHAR(200) COMMENT '住宿酒店',
ADD COLUMN transportation VARCHAR(200) COMMENT '交通方式',
ADD COLUMN tips TEXT COMMENT '温馨提示',
ADD COLUMN status ENUM('planned','confirmed','in_progress','completed') 
    DEFAULT 'planned' COMMENT '行程状态',
ADD COLUMN actual_start_time TIME COMMENT '实际开始时间',
ADD COLUMN actual_end_time TIME COMMENT '实际结束时间',
ADD COLUMN notes TEXT COMMENT '执行备注',
ADD COLUMN display_order INT DEFAULT 0 COMMENT '显示顺序';

-- 添加外键约束
ALTER TABLE tour_itinerary
ADD CONSTRAINT fk_tour_itinerary_group 
    FOREIGN KEY (tour_id) REFERENCES tour_group(id) ON DELETE CASCADE,
ADD CONSTRAINT fk_tour_itinerary_template 
    FOREIGN KEY (source_template_id) REFERENCES product_itinerary(id) ON DELETE SET NULL;

-- 添加索引
CREATE INDEX idx_tour_day ON tour_itinerary(tour_id, day_number);
CREATE INDEX idx_date ON tour_itinerary(date);
CREATE INDEX idx_status ON tour_itinerary(status);
CREATE INDEX idx_display_order ON tour_itinerary(display_order);

-- 数据迁移：从 date 推算 day_number
UPDATE tour_itinerary t
JOIN tour_group g ON t.tour_id = g.id
SET t.day_number = DATEDIFF(t.date, g.departure_date) + 1
WHERE t.day_number IS NULL;
```

---

## 💡 使用场景示例

### 场景1：创建产品时录入标准行程

```python
# 创建产品
product = Product(
    product_name="新加坡3天2晚游",
    city_name="新加坡",
    duration_days=3
)
db.session.add(product)
db.session.commit()

# 添加标准行程
itinerary_day1 = ProductItinerary(
    product_id=product.id,
    day_number=1,
    day_title="抵达新加坡 - 滨海湾花园",
    content="抵达樟宜机场，专车接送至酒店...",
    meals="晚餐",
    accommodation="新加坡万豪酒店",
    image1="/images/gardens-by-bay.jpg"
)
db.session.add(itinerary_day1)
```

### 场景2：创建团队时复制行程

```python
# 创建团队
group = TourGroup(
    project_id=project.id,
    departure_date=date(2025, 12, 1),
    pax=20
)
db.session.add(group)
db.session.commit()

# 从产品模板复制行程
product_itineraries = ProductItinerary.query.filter_by(
    product_id=project.base_product_id
).order_by(ProductItinerary.day_number).all()

for template in product_itineraries:
    tour_itinerary = TourItinerary(
        tour_id=group.id,
        source_template_id=template.id,
        day_number=template.day_number,
        day_title=template.day_title,
        content=template.content,
        meals=template.meals,
        accommodation=template.accommodation,
        date=group.departure_date + timedelta(days=template.day_number - 1),
        image1=template.image1
    )
    db.session.add(tour_itinerary)

db.session.commit()
```

### 场景3：修改实际行程（不影响模板）

```python
# 团队导游可以修改实际行程
itinerary = TourItinerary.query.filter_by(
    tour_id=group.id, 
    day_number=2
).first()

itinerary.content = "因天气原因，改为室内活动..."
itinerary.status = 'in_progress'
itinerary.notes = "下雨，调整了行程"
db.session.commit()

# 原产品模板不受影响
```

---

## ✅ 方案总结

### tour_itinerary 应该这样管理：

1. **主要关联**: `tour_group` (团队表)
   - `tour_itinerary.tour_id` → `tour_group.id`

2. **次要关联**: `product_itinerary` (模板行程)
   - `tour_itinerary.source_template_id` → `product_itinerary.id`

3. **新建配套表**: `product_itinerary`
   - 关联 `travelproducts` (产品表)
   - 作为可复用的行程模板

### 优势

✅ **模板化**: 产品行程可复用  
✅ **灵活性**: 团队行程可独立修改  
✅ **可追溯**: 记录行程来源  
✅ **完整性**: 涵盖计划到执行全流程  
✅ **扩展性**: 支持状态管理、实际执行记录

### 数据流

```
产品模板行程 (product_itinerary)
    ↓ 复制
团队实际行程 (tour_itinerary)
    ↓ 执行
行程完成 (status: completed)
```

---

## 📝 下一步行动

1. ✅ 创建 `product_itinerary` 表
2. ✅ 增强 `tour_itinerary` 表
3. ✅ 更新 Python 模型
4. ✅ 实现复制功能（模板→实际）
5. ✅ 开发行程管理界面

---

## 🎯 核心答案

**tour_itinerary 应该关联 `tour_group` 表！**

- **关系**: `tour_itinerary.tour_id` → `tour_group.id` (1:N)
- **配合**: 新建 `product_itinerary` 关联 `travelproducts` 作为模板
- **流程**: 产品模板行程 → 复制 → 团队实际行程

