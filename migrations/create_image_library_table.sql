-- 创建图片库表
CREATE TABLE IF NOT EXISTS `image_library` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '图片ID',
    `title` VARCHAR(200) NULL COMMENT '图片标题/描述',
    `image_path` VARCHAR(500) NOT NULL COMMENT '图片路径（相对于static）',
    `tags` VARCHAR(200) NULL COMMENT '标签（逗号分隔）',
    `category` VARCHAR(50) NULL COMMENT '分类：tour/product/destination/other',
    `file_size` INT NULL COMMENT '文件大小（字节）',
    `width` INT NULL COMMENT '图片宽度',
    `height` INT NULL COMMENT '图片高度',
    `usage_count` INT DEFAULT 0 COMMENT '使用次数',
    `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否激活',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `created_by` VARCHAR(100) NULL COMMENT '创建人',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_category` (`category`),
    INDEX `idx_is_active` (`is_active`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='图片库表';

-- 创建产品图片关联表（多对多关系）
CREATE TABLE IF NOT EXISTS `product_images` (
    `product_id` INT NOT NULL COMMENT '产品ID',
    `image_id` INT NOT NULL COMMENT '图片ID',
    `image_type` VARCHAR(20) DEFAULT 'gallery' COMMENT '图片类型：cover/gallery',
    `sort_order` INT DEFAULT 0 COMMENT '排序顺序',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '关联创建时间',
    PRIMARY KEY (`product_id`, `image_id`),
    FOREIGN KEY (`product_id`) REFERENCES `package_products`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`image_id`) REFERENCES `image_library`(`id`) ON DELETE CASCADE,
    INDEX `idx_image_type` (`image_type`),
    INDEX `idx_sort_order` (`sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='产品图片关联表';
