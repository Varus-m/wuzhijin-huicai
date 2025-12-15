import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from config import config
from .extensions import db, limiter

# 初始化扩展
# db 和 limiter 已在 extensions.py 中创建实例，此处仅需导入

def create_app(config_name=None):
    """应用工厂函数"""
    
    # 获取配置名称
    config_name = config_name or os.getenv('FLASK_CONFIG', 'development')
    
    # 创建Flask应用
    app = Flask(__name__)
    
    # 加载配置
    app.config.from_object(config[config_name])
    
    # 初始化扩展
    db.init_app(app)
    limiter.init_app(app)
    
    # 配置CORS
    CORS(app, 
         origins=app.config.get('CORS_ORIGINS', ['*']),
         methods=app.config.get('CORS_METHODS', ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']),
         headers=app.config.get('CORS_HEADERS', ['Content-Type', 'Authorization']),
         supports_credentials=True)
    
    # 配置日志
    configure_logging(app)
    
    # 注册蓝图
    register_blueprints(app)
    
    # 注册错误处理器
    register_error_handlers(app)
    
    # 创建数据库表
    with app.app_context():
        try:
            db.create_all()
            app.logger.info('数据库表创建成功')
        except Exception as e:
            app.logger.error(f'数据库表创建失败: {str(e)}')
    
    return app

def configure_logging(app):
    """配置日志"""
    
    # 设置日志级别
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO').upper())
    
    # 创建日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 控制台日志
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # 文件日志（如果配置了日志文件）
    if app.config.get('LOG_FILE'):
        import os
        log_dir = os.path.dirname(app.config['LOG_FILE'])
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        file_handler = logging.FileHandler(app.config['LOG_FILE'])
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        app.logger.addHandler(file_handler)
    
    # 添加处理器
    app.logger.addHandler(console_handler)
    app.logger.setLevel(log_level)
    
    # 配置werkzeug日志
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(log_level)
    werkzeug_logger.addHandler(console_handler)
    
    # 配置SQLAlchemy日志
    sqlalchemy_logger = logging.getLogger('sqlalchemy')
    sqlalchemy_logger.setLevel(log_level)
    sqlalchemy_logger.addHandler(console_handler)

def register_blueprints(app):
    """注册蓝图"""
    
    # 导入并注册API蓝图
    from .views import api_bp
    app.register_blueprint(api_bp)
    
    # 导入并注册其他蓝图（如果有）
    # from .other_module import other_bp
    # app.register_blueprint(other_bp)

def register_error_handlers(app):
    """注册错误处理器"""
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'message': '资源未找到',
            'timestamp': int(datetime.utcnow().timestamp() * 1000)
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            'success': False,
            'message': '方法不允许',
            'timestamp': int(datetime.utcnow().timestamp() * 1000)
        }), 405
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'内部服务器错误: {str(error)}')
        return jsonify({
            'success': False,
            'message': '服务器内部错误',
            'timestamp': int(datetime.utcnow().timestamp() * 1000)
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        app.logger.error(f'未处理的异常: {str(error)}', exc_info=True)
        return jsonify({
            'success': False,
            'message': '服务器异常',
            'timestamp': int(datetime.utcnow().timestamp() * 1000)
        }), 500

# 导入模型，确保在创建应用时注册到SQLAlchemy
from . import models