-- ============================================
-- 清空项目数据脚本（MySQL）
-- 用于导入 Athina 数据前清理现有数据
--
-- 警告：此操作不可逆！请先备份数据！
-- ============================================

-- 先禁用外键检查（避免删除顺序问题）
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================
-- 第一步：删除关联表/子表数据
-- ============================================

-- 收款-发票分配记录
TRUNCATE TABLE receipt_invoice_allocations;

-- 发票明细
TRUNCATE TABLE invoice_items;

-- 预付款使用记录
TRUNCATE TABLE prepayment_usages;

-- REF 订单项
TRUNCATE TABLE ref_order_items;

-- 项目邮件
TRUNCATE TABLE project_emails;

-- ============================================
-- 第二步：删除业务表数据
-- ============================================

-- EO（Exchange Order）
TRUNCATE TABLE project_eos;

-- 收款记录
TRUNCATE TABLE project_receipts;

-- 发票
TRUNCATE TABLE project_invoices;

-- 供应商付款
TRUNCATE TABLE supplier_payments;

-- 预付款
TRUNCATE TABLE supplier_prepayments;

-- 付款凭证
TRUNCATE TABLE payment_vouchers;

-- REF
TRUNCATE TABLE project_refs;

-- 项目成员
TRUNCATE TABLE project_members;

-- ============================================
-- 第三步：删除主表数据
-- ============================================

-- 项目主表
TRUNCATE TABLE project_headers;

-- ============================================
-- 可选：清空 Athina 导入的原始数据
-- 如果需要重新从 Athina 数据库导入，取消下面的注释
-- ============================================

-- TRUNCATE TABLE athina_booking_details;
-- TRUNCATE TABLE athina_booking_headers;

-- ============================================
-- 重新启用外键检查
-- ============================================
SET FOREIGN_KEY_CHECKS = 1;

-- 验证清空结果
SELECT 'project_headers' as table_name, COUNT(*) as count FROM project_headers
UNION ALL SELECT 'project_refs', COUNT(*) FROM project_refs
UNION ALL SELECT 'project_members', COUNT(*) FROM project_members
UNION ALL SELECT 'project_eos', COUNT(*) FROM project_eos
UNION ALL SELECT 'project_invoices', COUNT(*) FROM project_invoices
UNION ALL SELECT 'project_receipts', COUNT(*) FROM project_receipts
UNION ALL SELECT 'supplier_payments', COUNT(*) FROM supplier_payments;
