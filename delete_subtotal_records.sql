-- 删除athina_booking_details表中所有小计行记录（is_subtotal=True）
-- 因为Sub Total行不应该存储在details表中，只应该更新header的汇总数据

-- 先查看有多少小计行记录
-- SELECT COUNT(*) FROM athina_booking_details WHERE is_subtotal = 1;

-- 删除所有小计行记录（使用id > 0以符合安全模式要求）
DELETE FROM athina_booking_details WHERE is_subtotal = 1 AND id > 0;

