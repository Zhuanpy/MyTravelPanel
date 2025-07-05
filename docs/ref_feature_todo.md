# Ref 业务类型创建功能 To-do List

1. 分析并整理所有业务类型及其字段需求（如机票、酒店、旅游团、签证等，每种类型需要哪些字段）
2. 设计"选择业务类型"页面，供用户选择要创建的ref类型
3. 为每种业务类型设计独立的创建表单模板（如 create_flight_ref.html、create_hotel_ref.html 等）
4. 在 App/routes/projects/BookingProject/ 目录下为每种类型创建对应的视图函数（如 create_flight_ref、create_hotel_ref 等）
5. 实现后端表单校验和数据保存逻辑，确保不同类型ref的数据能正确入库
6. 实现创建成功后跳转到ref详情页并展示新建内容
7. 测试所有类型的ref创建流程，确保各类型表单和保存逻辑无误

---

> 本文档用于跟踪和管理"ref 业务类型创建"相关开发任务，建议团队成员在每次推进后及时更新进度。 

# Ref 业务类型及字段需求

## 1. 机票（Flight）
- 编号（ref_number）
- 名称（name）
- 类型（ref_type=机票）
- 供应商（supplier）
- 金额（selling_price）
- 状态（status）
- 航班号、出发地、目的地、起飞时间、乘客信息等

## 2. 酒店（Hotel）
- 编号（ref_number）
- 名称（name）
- 类型（ref_type=酒店）
- 供应商（supplier）
- 金额（selling_price）
- 状态（status）
- 酒店名称、入住/退房日期、房型、客人信息等

## 3. 旅游团（Tour）
- ...（同上）

## 4. 签证（Visa）
- ...（同上）

## 5. 保险（Insurance）
- ...（同上）

## 6. 交通（Transport）
- ...（同上）

## 7. 其他（Other）
- ...（同上） 