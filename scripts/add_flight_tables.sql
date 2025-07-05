-- 创建机票乘客信息表
CREATE TABLE IF NOT EXISTS `project_flight_passengers` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `ref_id` int(11) NOT NULL COMMENT 'REF明细ID',
    `name` varchar(50) NOT NULL COMMENT '乘客姓名',
    `passenger_type` varchar(10) NOT NULL DEFAULT 'adult' COMMENT '乘客类型：adult/child/infant',
    `selling_price` decimal(10,2) DEFAULT NULL COMMENT '售价',
    `cost_price` decimal(10,2) DEFAULT NULL COMMENT '成本',
    `ticket_number` varchar(50) DEFAULT NULL COMMENT '电子客票号',
    `pnr` varchar(6) DEFAULT NULL COMMENT 'PNR编码',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_ref_id` (`ref_id`),
    KEY `idx_passenger_type` (`passenger_type`),
    CONSTRAINT `fk_flight_passengers_ref` FOREIGN KEY (`ref_id`) REFERENCES `project_refs` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='机票乘客信息表';

-- 创建机票航段信息表
CREATE TABLE IF NOT EXISTS `project_flight_segments` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `ref_id` int(11) NOT NULL COMMENT 'REF明细ID',
    `flight_number` varchar(10) NOT NULL COMMENT '航班号',
    `departure_airport` varchar(3) NOT NULL COMMENT '出发机场',
    `arrival_airport` varchar(3) NOT NULL COMMENT '到达机场',
    `departure_time` datetime NOT NULL COMMENT '起飞时间',
    `arrival_time` datetime NOT NULL COMMENT '到达时间',
    `cabin_class` varchar(20) NOT NULL COMMENT '舱位等级',
    `cabin_code` varchar(2) NOT NULL COMMENT '舱位代码',
    `status` varchar(20) NOT NULL DEFAULT 'pending' COMMENT '航段状态',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_ref_id` (`ref_id`),
    KEY `idx_flight_number` (`flight_number`),
    KEY `idx_departure_airport` (`departure_airport`),
    KEY `idx_arrival_airport` (`arrival_airport`),
    KEY `idx_departure_time` (`departure_time`),
    CONSTRAINT `fk_flight_segments_ref` FOREIGN KEY (`ref_id`) REFERENCES `project_refs` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='机票航段信息表'; 