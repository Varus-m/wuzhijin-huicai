import os
from datetime import timedelta

class Config:
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://root:wuzhijin%40123@sh-cynosdbmysql-grp-1zl2d8bg.sql.tencentcdb.com:21111/wuzhijin'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_POOL_TIMEOUT = 30
    SQLALCHEMY_POOL_RECYCLE = 3600
    
    # 微信小程序配置
    WECHAT_APPID = os.environ.get('WECHAT_APPID') or 'wx8bf8e615cf7de804'
    WECHAT_SECRET = os.environ.get('WECHAT_SECRET') or '874e241f32d32b02937d27cf495d2d89'
    
    # ERP系统配置
    ERP_BASE_URL = os.environ.get('ERP_BASE_URL') or 'http://localhost:5001'
    ERP_API_KEY = os.environ.get('ERP_API_KEY') or 'your_erp_api_key'
    ERP_TIMEOUT = 30  # 秒
    ERP_MAX_RETRIES = 3
    
    # 微信模板消息配置
    TEMPLATE_IDS = {
        'order_status_change': os.environ.get('TEMPLATE_ORDER_STATUS') or 'order_status_template_id',
        'material_progress': os.environ.get('TEMPLATE_MATERIAL_PROGRESS') or 'material_progress_template_id',
        'delivery_notice': os.environ.get('TEMPLATE_DELIVERY') or 'delivery_notice_template_id'
    }
    
    # 接口限流配置
    RATELIMIT_STORAGE_URL = "memory://"
    RATELIMIT_DEFAULT = "100 per hour"
    
    # 监控配置
    PROMETHEUS_PORT = 9090
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = os.environ.get('LOG_FILE') or 'logs/app.log'
    
    # 会话配置
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'erp_tracking:'
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    
    # 安全配置
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    
    # 跨域配置
    CORS_ORIGINS = ['*']  # 生产环境需要限制域名
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    CORS_HEADERS = ['Content-Type', 'Authorization']
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False
    
class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}