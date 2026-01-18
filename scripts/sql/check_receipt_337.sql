-- 检查收款 337 详情
SELECT id, receipt_number, header_id, invoice_id, ref_id, amount, status 
FROM project_receipts WHERE id = 337;

-- 检查收款 337 的分配记录
SELECT * FROM receipt_invoice_allocations WHERE receipt_id = 337;

-- 检查发票 10262 和 10241
SELECT id, invoice_number, header_id, amount, paid_amount, payment_status, ref_ids 
FROM project_invoices WHERE id IN (101, 80);
