from flask_caching import Cache

# 创建缓存实例
cache = Cache()  # 初始化时不传入配置，而是在init_app时传入 