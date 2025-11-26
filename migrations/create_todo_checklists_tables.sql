-- 创建任务清单相关表
-- 用于支持重复任务和任务模板功能

-- 1. 创建任务清单表
CREATE TABLE IF NOT EXISTS todo_checklists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(50),
    is_recurring BOOLEAN DEFAULT 0,
    recurrence_type VARCHAR(20),  -- daily, weekly, monthly
    recurrence_days VARCHAR(50),  -- 用于 weekly: 1,2,3,4,5,6,0 (周一到周日)
    recurrence_time VARCHAR(10),  -- HH:MM
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    last_generated_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE
);

-- 2. 创建任务清单项表
CREATE TABLE IF NOT EXISTS todo_checklist_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    checklist_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    priority INTEGER DEFAULT 2,  -- 1=高，2=中，3=低
    order_index INTEGER DEFAULT 0,
    FOREIGN KEY (checklist_id) REFERENCES todo_checklists(id) ON DELETE CASCADE
);

-- 3. 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_todo_checklists_user_id ON todo_checklists(user_id);
CREATE INDEX IF NOT EXISTS idx_todo_checklists_is_active ON todo_checklists(is_active);
CREATE INDEX IF NOT EXISTS idx_todo_checklists_is_recurring ON todo_checklists(is_recurring);
CREATE INDEX IF NOT EXISTS idx_todo_checklist_items_checklist_id ON todo_checklist_items(checklist_id);
CREATE INDEX IF NOT EXISTS idx_todo_checklist_items_order_index ON todo_checklist_items(order_index);

-- 4. 验证表是否创建成功
SELECT 
    'todo_checklists' as table_name,
    COUNT(*) as column_count
FROM pragma_table_info('todo_checklists')
UNION ALL
SELECT 
    'todo_checklist_items' as table_name,
    COUNT(*) as column_count
FROM pragma_table_info('todo_checklist_items');

-- 使用说明：
-- 1. 在本地执行此脚本：sqlite3 instance/travel_panel_new.db < migrations/create_todo_checklists_tables.sql
-- 2. 在服务器上执行此脚本：sqlite3 /path/to/database.db < migrations/create_todo_checklists_tables.sql
-- 3. 或使用 Python 脚本执行（见下方示例）

-- Python 执行示例：
-- python -c "import sqlite3; conn = sqlite3.connect('instance/travel_panel_new.db'); conn.executescript(open('migrations/create_todo_checklists_tables.sql', encoding='utf-8').read()); conn.commit(); conn.close()"

