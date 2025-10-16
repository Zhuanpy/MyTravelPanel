# 旅游产品管理系统优化方案

## 📊 当前模型分析

### 现有表结构

#### 1. `travelproducts` (Product)
**用途**：产品模板库/基础产品信息
**核心字段**：
- 基本信息：city_name, company_name, product_name, product_type, duration_days
- 人数限制：min_pax, max_pax
- 价格信息：base_price, child_price, infant_price, single_room_supplement
- 描述信息：product_description, highlights, included_services, excluded_services
- 联系信息：contact_person, contact_phone, contact_email
- 状态：product_status (active/inactive/draft)

**关联表**：
- `product_itinerary` - 产品行程详情（已定义但可能未使用）
- `product_price_variant` - 价格变体（已定义但可能未使用）

**问题**：
- ❌ `company_name` 是文本，没有关联到供应商/代理表
- ❌ 缺少图片字段
- ❌ 没有国家字段

---

#### 2. `tour_products` (TourProduct)
**用途**：展示模板/PDF生成用
**核心字段**：
- title, country, city
- itinerary (文本)
- included, not_included (文本)
- price, duration

**问题**：
- ❌ 与 `travelproducts` 功能重叠
- ❌ 没有外键关联到 `travelproducts`
- ❌ 缺少详细字段

---

#### 3. `tour_project` (TourProject)
**用途**：旅游项目/订单管理
**核心字段**：
- project_name, project_hid, project_status
- contact_person, contact_info
- budget, folder_name

**关联**：
- → `tour_group` (1对多)

---

#### 4. `tour_group` (TourGroup)
**用途**：团队管理（实际出团）
**核心字段**：
- title, departure_date, return_date, pax
- agency, operator (旅行社、地接社)
- hotel_info, transport, meals, attractions
- group_code, group_status

**关联**：
- ← `tour_project` (多对1)
- → `tour_itinerary` (1对多)

---

#### 5. `tour_itinerary`
**用途**：每日行程详情
**核心字段**：
- day_title, date, content
- image1, image2, image3

**关联**：
- ← `tour_group` (多对1，通过 tour_id)

---

## 🎯 优化方案

### 方案一：基于代理的产品库架构（推荐）

#### 核心概念
- **供应商/代理** → 提供多个 **产品模板** → 基于模板创建 **项目** → 项目包含多个 **团队** → 团队有 **行程安排**

#### 优化后的表结构

##### 1. `travel_products` (产品模板库) - 优化 `travelproducts`
```python
class TravelProduct(db.Model):
    """旅游产品模板库（供应商提供的标准产品）"""
    __tablename__ = 'travel_products'
    
    # 基础信息
    id = db.Column(db.Integer, primary_key=True)
    product_code = db.Column(db.String(50), unique=True, comment='产品编号')
    product_name = db.Column(db.String(200), nullable=False, comment='产品名称')
    
    # 供应商关联
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.supplier_id'), nullable=False)
    supplier = db.relationship('Supplier', backref='tour_products')
    
    # 地理信息
    country = db.Column(db.String(100), nullable=False, comment='国家')
    city = db.Column(db.String(100), nullable=False, comment='城市')
    departure_city = db.Column(db.String(100), comment='出发城市')
    
    # 产品属性
    product_type = db.Column(db.String(50), comment='产品类型：跟团游/自由行/定制游/当地游')
    duration_days = db.Column(db.Integer, nullable=False, comment='行程天数')
    duration_nights = db.Column(db.Integer, comment='住宿晚数')
    
    # 人数限制
    min_pax = db.Column(db.Integer, default=1, comment='最少成团人数')
    max_pax = db.Column(db.Integer, comment='最大成团人数')
    
    # 价格信息（参考价）
    base_price = db.Column(db.Float, comment='基础价格（成人）')
    child_price = db.Column(db.Float, comment='儿童价格')
    infant_price = db.Column(db.Float, comment='婴儿价格')
    single_room_supplement = db.Column(db.Float, comment='单房差')
    currency = db.Column(db.String(10), default='SGD')
    
    # 描述信息
    product_description = db.Column(db.Text, comment='产品描述')
    highlights = db.Column(db.Text, comment='产品亮点')
    included_services = db.Column(db.Text, comment='包含服务')
    excluded_services = db.Column(db.Text, comment='不包含服务')
    important_notes = db.Column(db.Text, comment='重要提示')
    
    # 适用条件
    suitable_season = db.Column(db.String(200), comment='适合季节')
    difficulty_level = db.Column(db.String(50), comment='难度等级：简单/中等/困难')
    tags = db.Column(db.Text, comment='标签（JSON格式）：蜜月/亲子/豪华/经济')
    
    # 图片
    cover_image = db.Column(db.String(500), comment='封面图')
    gallery_images = db.Column(db.Text, comment='图片库（JSON数组）')
    
    # 状态管理
    product_status = db.Column(db.String(50), default='active', comment='产品状态：active/inactive/draft')
    is_featured = db.Column(db.Boolean, default=False, comment='是否精选')
    valid_from = db.Column(db.Date, comment='有效开始日期')
    valid_until = db.Column(db.Date, comment='有效结束日期')
    
    # 版本管理（可选）
    version = db.Column(db.Integer, default=1, comment='版本号')
    parent_product_id = db.Column(db.Integer, db.ForeignKey('travel_products.id'), nullable=True, comment='父产品ID（用于版本追踪）')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(100), comment='创建人')
    
    # 关联
    # → product_itineraries (1对多)
    # → product_price_variants (1对多)
    # → tour_projects (通过 base_product_id)
```

##### 2. `product_itineraries` (产品行程模板)
```python
class ProductItinerary(db.Model):
    """产品行程模板（标准行程安排）"""
    __tablename__ = 'product_itineraries'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('travel_products.id'), nullable=False)
    day_number = db.Column(db.Integer, nullable=False, comment='第几天')
    day_title = db.Column(db.String(200), nullable=False, comment='日期标题')
    
    # 详细行程
    morning_activity = db.Column(db.Text, comment='上午活动')
    afternoon_activity = db.Column(db.Text, comment='下午活动')
    evening_activity = db.Column(db.Text, comment='晚上活动')
    full_day_content = db.Column(db.Text, comment='全天行程描述')
    
    # 服务安排
    meals = db.Column(db.String(200), comment='用餐安排：早/午/晚')
    accommodation = db.Column(db.String(200), comment='住宿安排')
    transport = db.Column(db.String(200), comment='交通安排')
    
    # 景点和亮点
    attractions = db.Column(db.Text, comment='景点列表（JSON数组）')
    highlights = db.Column(db.Text, comment='当日亮点')
    
    # 图片
    images = db.Column(db.Text, comment='图片列表（JSON数组）')
    
    # 备注
    notes = db.Column(db.Text, comment='注意事项')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    product = db.relationship('TravelProduct', backref=db.backref('itineraries', lazy='dynamic', order_by='ProductItinerary.day_number'))
```

##### 3. `product_price_variants` (价格变体)
```python
class ProductPriceVariant(db.Model):
    """产品价格变体（不同时段、不同人数的价格）"""
    __tablename__ = 'product_price_variants'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('travel_products.id'), nullable=False)
    
    variant_name = db.Column(db.String(100), comment='变体名称：旺季/淡季/节假日')
    start_date = db.Column(db.Date, comment='开始日期')
    end_date = db.Column(db.Date, comment='结束日期')
    
    # 人数范围
    min_pax = db.Column(db.Integer, comment='最少人数')
    max_pax = db.Column(db.Integer, comment='最多人数')
    
    # 价格
    adult_price = db.Column(db.Float, nullable=False, comment='成人价格')
    child_price = db.Column(db.Float, comment='儿童价格')
    infant_price = db.Column(db.Float, comment='婴儿价格')
    single_room_supplement = db.Column(db.Float, comment='单房差')
    currency = db.Column(db.String(10), default='SGD')
    
    is_active = db.Column(db.Boolean, default=True, comment='是否激活')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    product = db.relationship('TravelProduct', backref=db.backref('price_variants', lazy='dynamic'))
```

##### 4. `tour_project` (旅游项目) - 保持，小调整
```python
class TourProject(db.Model):
    """旅游项目/订单"""
    __tablename__ = 'tour_project'
    
    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(200), nullable=False)
    project_hid = db.Column(db.String(100), unique=True)
    
    # 关联基础产品（可选）
    base_product_id = db.Column(db.Integer, db.ForeignKey('travel_products.id'), nullable=True, comment='基于哪个产品模板')
    base_product = db.relationship('TravelProduct', backref='derived_projects')
    
    # 项目信息
    project_type = db.Column(db.String(50), comment='项目类型')
    project_status = db.Column(db.String(50), nullable=False, comment='处理中/待出行/已完成/忽略单')
    
    # 客户信息
    contact_person = db.Column(db.String(100), nullable=False)
    contact_info = db.Column(db.String(100), nullable=False)
    
    # 财务
    budget = db.Column(db.Float, comment='项目预算')
    currency = db.Column(db.String(10), default='SGD')
    
    # 其他
    folder_name = db.Column(db.String(100))
    remarks = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(100))
    
    # 关联
    # → tour_group (1对多)
```

##### 5. `tour_group` (团队) - 保持不变
```python
class TourGroup(db.Model):
    """实际出团团队"""
    __tablename__ = 'tour_group'
    
    # 保持现有字段
    # 关联
    # ← tour_project (多对1)
    # → tour_itinerary (1对多)
```

##### 6. `tour_itinerary` (团队行程) - 保持不变
```python
class TourItinerary(db.Model):
    """团队每日行程（实际执行行程）"""
    __tablename__ = 'tour_itinerary'
    
    # 保持现有字段
    # 关联
    # ← tour_group (多对1，通过 tour_id)
```

---

## 🗑️ 建议删除/合并的表

### `tour_product_data` ❌ 删除
**原因**：
1. 功能与 `travelproducts` 重叠
2. 如果需要不同代理的产品，应该用 `supplier_id` 区分，而不是单独的表

---

## 📋 数据流程图

```
供应商 (Supplier)
    │
    ├─→ 旅游产品模板 (TravelProduct)
    │       ├─→ 产品行程模板 (ProductItinerary)
    │       └─→ 产品价格变体 (ProductPriceVariant)
    │
    └─→ 旅游项目 (TourProject) ─基于─→ 旅游产品模板
            │
            └─→ 团队 (TourGroup)
                    └─→ 团队行程 (TourItinerary)
```

---

## 🔧 需要的模型修改

### 1. 修改 `travelproducts` → `travel_products`
```sql
-- 添加字段
ALTER TABLE travelproducts ADD COLUMN supplier_id INT COMMENT '供应商ID';
ALTER TABLE travelproducts ADD COLUMN country VARCHAR(100) COMMENT '国家';
ALTER TABLE travelproducts ADD COLUMN product_code VARCHAR(50) UNIQUE COMMENT '产品编号';
ALTER TABLE travelproducts ADD COLUMN cover_image VARCHAR(500) COMMENT '封面图';
ALTER TABLE travelproducts ADD COLUMN gallery_images TEXT COMMENT '图片库JSON';
ALTER TABLE travelproducts ADD COLUMN tags TEXT COMMENT '标签JSON';
ALTER TABLE travelproducts ADD COLUMN is_featured BOOLEAN DEFAULT FALSE COMMENT '是否精选';
ALTER TABLE travelproducts ADD COLUMN version INT DEFAULT 1 COMMENT '版本号';
ALTER TABLE travelproducts ADD COLUMN parent_product_id INT COMMENT '父产品ID';
ALTER TABLE travelproducts ADD COLUMN valid_from DATE COMMENT '有效开始日期';
ALTER TABLE travelproducts ADD COLUMN created_by VARCHAR(100) COMMENT '创建人';

-- 添加外键
ALTER TABLE travelproducts ADD CONSTRAINT fk_supplier 
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id);

-- 重命名表（可选）
RENAME TABLE travelproducts TO travel_products;
```

### 2. 激活并完善 `product_itinerary`
- 已定义，需要确保使用

### 3. 激活并完善 `product_price_variant`
- 已定义，需要确保使用

### 4. 修改 `tour_project` 添加产品关联
```sql
ALTER TABLE tour_project ADD COLUMN base_product_id INT COMMENT '基于哪个产品模板';
ALTER TABLE tour_project ADD COLUMN currency VARCHAR(10) DEFAULT 'SGD' COMMENT '货币';
ALTER TABLE tour_project ADD COLUMN created_by VARCHAR(100) COMMENT '创建人';

ALTER TABLE tour_project ADD CONSTRAINT fk_base_product 
    FOREIGN KEY (base_product_id) REFERENCES travel_products(id);
```

### 5. 删除 `tour_products` 或重新定位
**选项A**: 删除（功能由 `travel_products` 替代）
**选项B**: 重新定位为"展示模板"
```sql
-- 如果保留，添加关联
ALTER TABLE tour_products ADD COLUMN source_product_id INT COMMENT '来源产品ID';
ALTER TABLE tour_products ADD CONSTRAINT fk_source_product 
    FOREIGN KEY (source_product_id) REFERENCES travel_products(id);
```

---

## 🎨 新的添加产品页面设计

### 页面结构

#### 步骤 1：基本信息
- 选择供应商（下拉框，关联 `suppliers` 表）
- 产品编号（自动生成或手动输入）
- 产品名称
- 国家/城市（级联下拉）
- 产品类型（跟团游/自由行/定制游/当地游）
- 行程天数/晚数

#### 步骤 2：详细信息
- 出发城市
- 人数限制（最少/最多）
- 适合季节
- 难度等级
- 标签（多选：蜜月、亲子、豪华、经济等）

#### 步骤 3：价格设置
- 基础价格（成人）
- 儿童价格
- 婴儿价格
- 单房差
- 货币单位

#### 步骤 4：描述内容
- 产品描述（富文本）
- 产品亮点（列表）
- 包含服务（列表）
- 不包含服务（列表）
- 重要提示

#### 步骤 5：行程安排
- 动态添加每日行程
- 每天包含：
  - 日期标题
  - 上午/下午/晚上活动
  - 用餐安排
  - 住宿安排
  - 交通安排
  - 景点列表
  - 图片上传（每天最多3张）

#### 步骤 6：图片管理
- 上传封面图
- 上传多张图片到图片库
- 图片预览和排序

---

## 🛠️ 路由设计

### 产品管理路由 (`/tour/products/`)

```python
# 产品列表
GET  /tour/products/                       # 产品列表（可按供应商、国家、城市筛选）
GET  /tour/products/<int:id>              # 产品详情

# 产品管理
GET  /tour/products/add                    # 添加产品表单
POST /tour/products/add                    # 提交新产品
GET  /tour/products/<int:id>/edit         # 编辑产品表单
POST /tour/products/<int:id>/edit         # 更新产品
POST /tour/products/<int:id>/delete       # 删除产品

# 行程管理（产品行程模板）
GET  /tour/products/<int:id>/itineraries              # 查看产品行程
POST /tour/products/<int:id>/itineraries/add          # 添加行程天数
POST /tour/products/<int:id>/itineraries/<int:day_id>/edit  # 编辑某天行程
POST /tour/products/<int:id>/itineraries/<int:day_id>/delete # 删除某天行程

# 价格管理
GET  /tour/products/<int:id>/prices                   # 查看价格变体
POST /tour/products/<int:id>/prices/add               # 添加价格变体
POST /tour/products/<int:id>/prices/<int:variant_id>/edit # 编辑价格
POST /tour/products/<int:id>/prices/<int:variant_id>/delete # 删除价格

# 从产品创建项目
POST /tour/products/<int:id>/create_project           # 基于产品创建新项目
```

### 项目管理路由 (`/tour/projects/`) - 保持现有
```python
# 已有的路由保持不变
GET  /tour/projects/manage
GET  /tour/projects/detail/<int:project_id>
POST /tour/projects/edit/<int:project_id>
# ...
```

---

## 📝 模板文件建议

### 产品管理模板
```
App_new/templates/business/tour/products/
├── product_list.html          # 产品列表（按供应商分组）
├── product_detail.html        # 产品详情（展示所有信息）
├── product_form.html          # 产品表单（添加/编辑）
├── product_itinerary_form.html # 行程编辑表单
└── product_price_form.html    # 价格编辑表单
```

### 项目管理模板（现有）
```
App_new/templates/business/tour/package/TourProjects/
├── tour_project_list.html     # 保留
├── tour_project_detail.html   # 保留
└── tour_project_edit.html     # 保留
```

---

## 🎯 实施步骤建议

### Phase 1: 数据库优化 ✅
1. 为 `travelproducts` 添加 `supplier_id`, `country`, `cover_image`, `gallery_images` 等字段
2. 确保 `product_itinerary` 表存在且字段完整
3. 确保 `product_price_variant` 表存在且字段完整
4. 为 `tour_project` 添加 `base_product_id` 关联字段

### Phase 2: 模型代码优化 ✅
1. 更新 `Product` 模型（Packagemodels.py）
2. 确认 `ProductItinerary` 和 `ProductPriceVariant` 关联正确
3. 更新 `TourProject` 模型添加产品关联

### Phase 3: 产品管理功能 ✅
1. 创建产品列表页面（支持按供应商筛选）
2. 创建产品详情页面
3. 创建产品添加/编辑表单（多步骤或单页）
4. 添加行程管理功能
5. 添加价格管理功能

### Phase 4: 项目创建流程优化 ✅
1. 支持从产品模板创建项目
2. 自动复制行程安排
3. 自动应用价格

---

## 💡 推荐的业务流程

### 产品录入流程
1. **选择供应商** → 选择合作的地接社/旅行社
2. **填写基本信息** → 产品名称、国家、城市、天数等
3. **设置价格** → 基础价格 + 可选的价格变体（旺季/淡季）
4. **编排行程** → 逐天添加行程内容
5. **上传图片** → 封面图 + 行程图片
6. **保存为模板** → 状态设为 active

### 项目创建流程
1. **选择产品模板** → 从产品库选择
2. **创建项目** → 自动复制产品信息
3. **调整细节** → 根据客户需求调整
4. **创建团队** → 设置出发日期、人数等
5. **确认行程** → 基于模板微调
6. **生成确认书** → 打印/发送给客户

---

## 🔍 关键设计决策

### Q1: `tour_products` 表如何处理？
**建议**: 删除或重新定位为"展示模板生成器"
- 如果用于生成PDF/网站展示，可以保留并添加 `source_product_id` 关联到 `travel_products`
- 如果功能重叠，建议删除

### Q2: 代理如何管理？
**建议**: 使用现有的 `suppliers` 表
- 在 `suppliers` 表中，`supplier_type` 可以是 `tour_operator` / `travel_agency` / `local_operator`
- 一个供应商可以有多个旅游产品

### Q3: 行程和图片如何存储？
**建议**:
- **行程**: 使用 `product_itinerary` 表（产品模板）和 `tour_itinerary` 表（实际团队）
- **图片**: 
  - 产品封面：`cover_image` 字段
  - 产品图片库：`gallery_images` JSON 数组
  - 每日行程图片：`tour_itinerary.image1/2/3` 或 JSON 数组

### Q4: 价格如何管理？
**建议**:
- **基础价格**: 存储在 `travel_products` 表中
- **价格变体**: 使用 `product_price_variant` 表（旺季/淡季/人数优惠）
- **实际报价**: 在 `tour_project` 或 `tour_group` 中记录最终价格

---

## 📱 UI/UX 建议

### 产品列表页面
- 按供应商分组显示
- 卡片式展示（封面图 + 标题 + 价格 + 天数）
- 筛选：供应商、国家、城市、产品类型、状态
- 搜索：产品名称、标签

### 产品详情页面
- 顶部：封面图 + 基本信息
- 中部：行程详情（时间轴展示）
- 底部：价格表 + 包含/不包含服务
- 操作按钮：编辑、复制、创建项目、删除

### 产品添加/编辑表单
- 使用分步表单（Tab切换）或单页长表单
- 行程部分支持动态添加/删除/排序
- 图片上传支持拖拽和预览
- 自动保存草稿

---

## 🚀 下一步行动

您希望我：
1. ✅ **立即开始实施** - 按照上述方案修改模型、创建迁移脚本、重构页面？
2. ✅ **先迁移数据** - 如果 `tour_product_data` 有数据，先迁移到 `travelproducts`？
3. ✅ **调整方案** - 对上述方案有任何调整建议？

请告诉我您的决定，我会立即开始执行！

