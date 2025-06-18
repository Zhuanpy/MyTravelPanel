-- 创建 visa_documents_list 表
-- 用于存储所有可用的签证文档模板

CREATE TABLE IF NOT EXISTS `visa_documents_list` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL UNIQUE,
    `description` TEXT NULL,
    `category` VARCHAR(50) NULL
);

-- 创建 visa_document_documents 关联表
-- 用于存储签证配置与文档的多对多关系

CREATE TABLE IF NOT EXISTS `visa_document_documents` (
    `visa_document_id` INT NOT NULL,
    `document_id` INT NOT NULL,
    PRIMARY KEY (`visa_document_id`, `document_id`),
    FOREIGN KEY (`visa_document_id`) REFERENCES `visa_documents_request`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`document_id`) REFERENCES `visa_documents_list`(`id`) ON DELETE CASCADE
);

-- 添加索引以提高查询性能
CREATE INDEX `idx_visa_documents_list_name` ON `visa_documents_list`(`name`);
CREATE INDEX `idx_visa_documents_list_category` ON `visa_documents_list`(`category`);
CREATE INDEX `idx_visa_document_documents_visa_doc_id` ON `visa_document_documents`(`visa_document_id`);
CREATE INDEX `idx_visa_document_documents_doc_id` ON `visa_document_documents`(`document_id`);

-- 插入一些常用的文档模板
INSERT INTO `visa_documents_list` (`name`, `description`, `category`) VALUES
('护照原件', '申请人护照原件', '身份证明'),
('护照复印件', '申请人护照复印件', '身份证明'),
('近期护照照片', '近期拍摄的护照规格照片', '身份证明'),
('身份证复印件', '申请人身份证复印件', '身份证明'),
('出生证明', '申请人出生证明', '身份证明'),
('结婚证明', '申请人结婚证明（如适用）', '身份证明'),
('学历证明', '申请人学历证明', '教育背景'),
('工作证明', '申请人工作证明', '工作背景'),
('银行对账单', '申请人银行对账单', '财务证明'),
('申请表', '签证申请表', '申请材料'),
('邀请函', '邀请函或担保函', '申请材料'),
('行程安排', '详细的行程安排', '申请材料'),
('酒店预订', '酒店预订确认', '申请材料'),
('机票预订', '往返机票预订', '申请材料'),
('保险证明', '旅行保险证明', '申请材料'),
('在职证明', '在职证明信', '工作背景'),
('收入证明', '收入证明文件', '财务证明'),
('房产证明', '房产证明文件', '财务证明'),
('车辆证明', '车辆证明文件', '财务证明'),
('无犯罪记录证明', '无犯罪记录证明', '背景调查');

-- 显示创建结果
SELECT 'visa_documents_list 表创建完成' AS message;
SELECT COUNT(*) AS total_documents FROM `visa_documents_list`; 