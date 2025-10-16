# 旅游产品行程管理 - 简化版

## ✅ 简化设计

根据用户需求，行程管理功能已简化为：

### 📋 字段设计

| 字段 | 类型 | 说明 | 必填 |
|------|------|------|------|
| `day_number` | INT | 第几天（1, 2, 3...） | ✅ |
| `day_title` | TEXT | 行程安排 | ✅ |

**不再需要**：
- ❌ 日期（date）
- ❌ 上午/下午/晚上活动分离
- ❌ 用餐、住宿、交通单独字段

## 📊 数据库表结构

```sql
CREATE TABLE product_itinerary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL COMMENT '产品ID',
    day_number INT NOT NULL COMMENT '第几天',
    day_title TEXT NOT NULL COMMENT '行程安排',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (product_id) REFERENCES travelproducts(id) ON DELETE CASCADE,
    INDEX idx_product_day (product_id, day_number)
);
```

## 🎨 UI展示

### 行程列表表格
| 天数 | 行程安排 | 操作 |
|------|----------|------|
| **第1天** | 上午：参观鱼尾狮公园<br>下午：游览圣淘沙岛<br>晚上：夜游滨海湾 | 编辑 / 删除 |
| **第2天** | 全天：环球影城游玩 | 编辑 / 删除 |

### 编辑表单
```
┌─────────────────────────────────┐
│ 第几天 *                        │
│ [ 1                          ]  │
├─────────────────────────────────┤
│ 行程安排 *                      │
│ ┌───────────────────────────┐  │
│ │ 上午：参观鱼尾狮公园       │  │
│ │ 下午：游览圣淘沙岛        │  │
│ │ 晚上：夜游滨海湾          │  │
│ │                            │  │
│ └───────────────────────────┘  │
└─────────────────────────────────┘
   [取消]  [保存]
```

## 🔧 使用示例

### 示例1：单日行程
```
第1天：
上午：参观鱼尾狮公园
下午：游览圣淘沙岛
晚上：夜游滨海湾
```

### 示例2：简洁描述
```
第2天：
全天环球影城游玩，包含所有项目通票
```

### 示例3：详细行程
```
第3天：
08:00 - 酒店早餐
09:00 - 前往新加坡动物园
12:00 - 午餐（自理）
14:00 - 河川生态园
18:00 - 返回酒店
19:00 - 晚餐（克拉码头）
```

## 📝 数据录入指南

### ✅ 推荐格式
- 使用换行分隔不同时间段
- 可以包含时间（08:00）
- 可以包含用餐、住宿、交通信息
- 自由格式，灵活描述

### ✅ 示例
```
早餐后退房
09:00 乘车前往机场
11:30 航班起飞 SQ123
15:00 抵达目的地
入住四季酒店
```

## 🚀 执行步骤

### 1. 执行数据库迁移
```sql
-- 文件：migrations/create_product_itinerary_table.sql
```

### 2. 重启Flask服务器
```bash
# 重启应用以加载新模型
```

### 3. 访问产品编辑页面
```
http://127.0.0.1:5000/tour/products/<product_id>/edit
```

## 🎯 功能优势

| 优势 | 说明 |
|------|------|
| ✅ **简洁** | 只有2个必填字段，快速录入 |
| ✅ **灵活** | 自由描述格式，适应不同需求 |
| ✅ **直观** | 一目了然，方便查看和编辑 |
| ✅ **易维护** | 表结构简单，减少冗余字段 |

## 📂 文件清单

### 已修改文件
1. `App_new/templates/business/tour/products/product_form.html`
   - 简化行程表格（3列）
   - 简化模态框表单（2个字段）
   - 精简JavaScript代码

2. `App_new/business/tour/routes/tour_products.py`
   - 简化API路由字段处理
   - 只处理 `day_number` 和 `day_title`

3. `App_new/business/tour/models/Packagemodels.py`
   - 简化 `ProductItinerary` 模型
   - 只保留核心字段

4. `migrations/create_product_itinerary_table.sql`
   - 简化表结构
   - 只创建核心字段

---

**更新时间**: 2025-10-16  
**版本**: v2.0 简化版

