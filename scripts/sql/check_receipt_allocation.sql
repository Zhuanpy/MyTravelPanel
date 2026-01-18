-- 检查项目1973的收款记录和分配
SELECT 
    r.id as receipt_id,
    r.receipt_no,
    r.amount,
    r.receipt_date,
    r.ref_id,
    r.invoice_id,
    ria.id as allocation_id,
    ria.invoice_id as alloc_invoice_id,
    ria.allocated_amount
FROM project_receipts r
LEFT JOIN receipt_invoice_allocations ria ON r.id = ria.receipt_id
WHERE r.project_id = 1973;

-- 检查项目1978的收款记录和分配
SELECT 
    r.id as receipt_id,
    r.receipt_no,
    r.amount,
    r.receipt_date,
    r.ref_id,
    r.invoice_id,
    ria.id as allocation_id,
    ria.invoice_id as alloc_invoice_id,
    ria.allocated_amount
FROM project_receipts r
LEFT JOIN receipt_invoice_allocations ria ON r.id = ria.receipt_id
WHERE r.project_id = 1978;

-- 检查项目1973的REF状态
SELECT id, ref_no, selling_price, payment_status FROM project_refs WHERE project_id = 1973;

-- 检查项目1978的REF状态
SELECT id, ref_no, selling_price, payment_status FROM project_refs WHERE project_id = 1978;
