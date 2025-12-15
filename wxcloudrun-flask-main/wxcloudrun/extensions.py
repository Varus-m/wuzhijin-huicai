from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# 初始化数据库
db = SQLAlchemy()

# 初始化限流器
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)
