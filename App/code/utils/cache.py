from functools import wraps
from datetime import datetime, timedelta
import json

class SimpleCache:
    def __init__(self):
        self._cache = {}
        self._expiry = {}

    def set(self, key, value, expire_minutes=60):
        """设置缓存"""
        self._cache[key] = value
        self._expiry[key] = datetime.now() + timedelta(minutes=expire_minutes)

    def get(self, key):
        """获取缓存"""
        if key not in self._cache:
            return None
        
        if datetime.now() > self._expiry[key]:
            del self._cache[key]
            del self._expiry[key]
            return None
            
        return self._cache[key]

    def delete(self, key):
        """删除缓存"""
        if key in self._cache:
            del self._cache[key]
            del self._expiry[key]

# 创建全局缓存实例
cache = SimpleCache()

def cached(expire_minutes=60):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # 尝试从缓存获取
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache.set(cache_key, result, expire_minutes)
            return result
        return wrapper
    return decorator 