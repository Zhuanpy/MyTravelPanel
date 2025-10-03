-- 创建签证访问统计表
CREATE TABLE visa_visit_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    visa_type_id INTEGER NOT NULL,
    visa_type_name VARCHAR(100) NOT NULL,
    country_name VARCHAR(100),
    visitor_ip VARCHAR(45),
    user_agent TEXT,
    referer TEXT,
    visit_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(100),
    FOREIGN KEY (visa_type_id) REFERENCES visa_types(id) ON DELETE CASCADE
);

-- 创建索引提高查询性能
CREATE INDEX idx_visa_visit_stats_visa_type_id ON visa_visit_stats(visa_type_id);
CREATE INDEX idx_visa_visit_stats_visit_time ON visa_visit_stats(visit_time);
CREATE INDEX idx_visa_visit_stats_session_id ON visa_visit_stats(session_id);
