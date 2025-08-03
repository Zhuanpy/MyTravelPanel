from flask_caching import Cache
from functools import wraps
from datetime import datetime, timedelta
import json

# 创建Flask缓存实例
cache = Cache()  # 初始化时不传入配置，而是在init_app时传入

# 自定义简单缓存类
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

# 创建全局简单缓存实例
simple_cache = SimpleCache()

def cached(expire_minutes=60):
    """缓存装饰器 - 用于模型属性缓存"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # 尝试从缓存获取
            result = simple_cache.get(cache_key)
            if result is not None:
                return result
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            simple_cache.set(cache_key, result, expire_minutes)
            return result
        return wrapper
    return decorator 