-- 创建首页轮播图表
-- 执行此脚本前请确保已连接到正确的数据库

CREATE TABLE IF NOT EXISTS home_banners (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100) NULL COMMENT '图片标题',
    description VARCHAR(255) NULL COMMENT '图片描述',
    image_path VARCHAR(500) NOT NULL COMMENT '图片路径',
    link_url VARCHAR(500) NULL COMMENT '点击跳转链接',
    sort_order INT DEFAULT 0 COMMENT '排序顺序，数字越小越靠前',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    created_by VARCHAR(100) NULL COMMENT '创建人'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='首页轮播图管理';

-- 创建索引
CREATE INDEX idx_home_banners_active ON home_banners(is_active);
CREATE INDEX idx_home_banners_sort ON home_banners(sort_order);

-- 查看表结构
-- DESCRIBE home_banners;
