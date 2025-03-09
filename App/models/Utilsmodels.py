from ..exts import db  # 确保你已正确导入 db 对象


# 定义数据库模型
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    remaining_time = db.Column(db.Integer, default=600)  # 默认为 600 秒 (10分钟)
    status = db.Column(db.String(20), default='stopped')  # 状态字段，可以是 'running', 'paused', 'stopped'

    def create(self, name):
        self.name = name
        db.session.add(self)
        db.session.commit()

    @classmethod
    def update_status(cls, task_id, status, remaining_time=None):
        task = cls.query.get(task_id)
        if task:
            task.status = status
            if remaining_time is not None:  # 如果传递了剩余时间
                task.remaining_time = remaining_time
            db.session.commit()
            return task
        return None

    @classmethod
    def reset(cls, task_id):
        task = cls.query.get(task_id)
        if task:
            task.remaining_time = 600  # 重置为10分钟
            task.status = 'paused'  # 假设任务重置后是暂停状态
            db.session.commit()
            return task
        return None

    @classmethod
    def delete(cls, task_id):
        task = cls.query.get(task_id)
        if task:
            db.session.delete(task)
            db.session.commit()
            return True
        return False