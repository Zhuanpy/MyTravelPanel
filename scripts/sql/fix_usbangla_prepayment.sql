-- =======================================================================
-- 修复 US-BANGLA AIRLINES LTD 预付账款使用记录
-- supplier_id = 227
-- 执行前请先运行查询部分确认数据
-- =======================================================================

-- -----------------------------------------------------------------------
-- 第1步：查询当前情况（只读查询，先执行确认数据）
-- -----------------------------------------------------------------------

-- 1.1 查看预付账款记录
SELECT
    id, prepayment_number, amount, balance_amount,
    amount - balance_amount AS used_amount,
    payment_date, status
FROM supplier_prepayments
WHERE supplier_id = 227
ORDER BY payment_date, id;

-- 1.2 查看当前使用记录
SELECT
    pu.id, pu.prepayment_id, sp.prepayment_number,
    pu.eo_id, eo.eo_number, pu.amount, pu.usage_date
FROM prepayment_usages pu
JOIN supplier_prepayments sp ON pu.prepayment_id = sp.id
LEFT JOIN project_eos eo ON pu.eo_id = eo.id
WHERE sp.supplier_id = 227
ORDER BY pu.usage_date, pu.id;

-- 1.3 查看该供应商的已付款EO（需要按时间FIFO分配）
SELECT
    eo.id, eo.eo_number,
    COALESCE(eo.pay_amount, ref.cost_price) AS amount,
    COALESCE(eo.paid_date, DATE(eo.created_at)) AS eo_date,
    ref.ref_number
FROM project_eos eo
JOIN project_refs ref ON eo.ref_id = ref.id
WHERE ref.supplier_id = 227
  AND eo.status = 'paid'
ORDER BY COALESCE(eo.paid_date, DATE(eo.created_at)), eo.id;

-- 1.4 统计汇总
SELECT
    '预付款充值总额' AS item,
    SUM(amount) AS total
FROM supplier_prepayments WHERE supplier_id = 227
UNION ALL
SELECT
    '已付款EO总额' AS item,
    SUM(COALESCE(eo.pay_amount, ref.cost_price)) AS total
FROM project_eos eo
JOIN project_refs ref ON eo.ref_id = ref.id
WHERE ref.supplier_id = 227 AND eo.status = 'paid';


-- -----------------------------------------------------------------------
-- 第2步：删除现有使用记录并重置余额（开启事务）
-- -----------------------------------------------------------------------

START TRANSACTION;

-- 2.1 备份当前使用记录（可选，用于回滚参考）
-- CREATE TEMPORARY TABLE temp_usage_backup AS
-- SELECT * FROM prepayment_usages WHERE prepayment_id IN (SELECT id FROM supplier_prepayments WHERE supplier_id = 227);

-- 2.2 删除现有使用记录
DELETE FROM prepayment_usages
WHERE prepayment_id IN (
    SELECT id FROM supplier_prepayments WHERE supplier_id = 227
);

-- 2.3 重置所有预付款余额为充值金额，状态为 confirmed
UPDATE supplier_prepayments
SET balance_amount = amount,
    status = 'confirmed',
    updated_at = NOW()
WHERE supplier_id = 227;

-- 确认重置结果
SELECT id, prepayment_number, amount, balance_amount, status
FROM supplier_prepayments WHERE supplier_id = 227 ORDER BY payment_date, id;

-- 如果确认无误，执行 COMMIT；否则执行 ROLLBACK
-- COMMIT;
-- ROLLBACK;


-- -----------------------------------------------------------------------
-- 第3步：按FIFO重新分配预付款使用记录
-- 需要在Python中执行或手动按以下逻辑插入
-- -----------------------------------------------------------------------

-- 以下SQL需要根据实际EO数据生成
-- 预付款按 payment_date 升序排列（FIFO）
-- EO按 paid_date/created_at 升序排列

-- 查询需要分配的EO列表（按时间排序）
SELECT
    eo.id AS eo_id,
    eo.ref_id,
    eo.eo_number,
    COALESCE(eo.pay_amount, ref.cost_price) AS amount,
    COALESCE(eo.paid_date, DATE(eo.created_at)) AS eo_date
FROM project_eos eo
JOIN project_refs ref ON eo.ref_id = ref.id
WHERE ref.supplier_id = 227
  AND eo.status = 'paid'
ORDER BY COALESCE(eo.paid_date, DATE(eo.created_at)), eo.id;

-- 查询预付款列表（按充值日期排序）
SELECT id, prepayment_number, amount, balance_amount, payment_date
FROM supplier_prepayments
WHERE supplier_id = 227
ORDER BY payment_date, id;


-- -----------------------------------------------------------------------
-- 第4步：执行存储过程进行FIFO分配
-- -----------------------------------------------------------------------

DELIMITER //

DROP PROCEDURE IF EXISTS fix_usbangla_prepayment_fifo//

CREATE PROCEDURE fix_usbangla_prepayment_fifo()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE v_eo_id INT;
    DECLARE v_ref_id INT;
    DECLARE v_eo_number VARCHAR(30);
    DECLARE v_eo_amount DECIMAL(12,2);
    DECLARE v_eo_date DATE;
    DECLARE v_prepayment_id INT;
    DECLARE v_prepayment_balance DECIMAL(12,2);
    DECLARE v_deduct_amount DECIMAL(12,2);
    DECLARE v_remaining DECIMAL(12,2);

    -- EO游标（按时间排序）
    DECLARE eo_cursor CURSOR FOR
        SELECT
            eo.id, eo.ref_id, eo.eo_number,
            COALESCE(eo.pay_amount, ref.cost_price),
            COALESCE(eo.paid_date, DATE(eo.created_at))
        FROM project_eos eo
        JOIN project_refs ref ON eo.ref_id = ref.id
        WHERE ref.supplier_id = 227
          AND eo.status = 'paid'
        ORDER BY COALESCE(eo.paid_date, DATE(eo.created_at)), eo.id;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    -- 处理每个EO
    OPEN eo_cursor;

    eo_loop: LOOP
        FETCH eo_cursor INTO v_eo_id, v_ref_id, v_eo_number, v_eo_amount, v_eo_date;
        IF done THEN
            LEAVE eo_loop;
        END IF;

        SET v_remaining = v_eo_amount;

        -- 为当前EO分配预付款（FIFO）
        WHILE v_remaining > 0 DO
            -- 找到第一个有余额的预付款
            SELECT id, balance_amount INTO v_prepayment_id, v_prepayment_balance
            FROM supplier_prepayments
            WHERE supplier_id = 227
              AND balance_amount > 0
            ORDER BY payment_date, id
            LIMIT 1;

            IF v_prepayment_id IS NULL THEN
                -- 没有可用预付款了，退出
                LEAVE eo_loop;
            END IF;

            -- 计算扣减金额
            SET v_deduct_amount = LEAST(v_remaining, v_prepayment_balance);

            -- 创建使用记录
            INSERT INTO prepayment_usages (
                prepayment_id, eo_id, ref_id, amount, usage_date,
                description, status, created_at, created_by
            ) VALUES (
                v_prepayment_id, v_eo_id, v_ref_id, v_deduct_amount, v_eo_date,
                CONCAT('FIFO Fix ', v_eo_number), 'confirmed', NOW(), 'SQL Fix'
            );

            -- 更新预付款余额
            UPDATE supplier_prepayments
            SET balance_amount = balance_amount - v_deduct_amount,
                status = CASE
                    WHEN balance_amount - v_deduct_amount <= 0 THEN 'consumed'
                    WHEN balance_amount - v_deduct_amount < amount THEN 'partial_used'
                    ELSE status
                END,
                updated_at = NOW()
            WHERE id = v_prepayment_id;

            SET v_remaining = v_remaining - v_deduct_amount;
            SET v_prepayment_id = NULL;

        END WHILE;

    END LOOP;

    CLOSE eo_cursor;

    -- 输出结果
    SELECT 'FIFO分配完成' AS message;

END//

DELIMITER ;


-- -----------------------------------------------------------------------
-- 第5步：执行修复（按顺序执行）
-- -----------------------------------------------------------------------

-- 5.1 先执行第2步的 START TRANSACTION，删除和重置
-- 5.2 确认无误后 COMMIT

-- 5.3 调用存储过程进行FIFO分配
-- CALL fix_usbangla_prepayment_fifo();

-- 5.4 查看最终结果
-- SELECT id, prepayment_number, amount, balance_amount,
--        amount - balance_amount AS used_amount, status
-- FROM supplier_prepayments WHERE supplier_id = 227 ORDER BY payment_date, id;

-- 5.5 清理存储过程（可选）
-- DROP PROCEDURE IF EXISTS fix_usbangla_prepayment_fifo;
