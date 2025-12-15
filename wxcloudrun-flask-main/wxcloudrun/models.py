from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, Index
from sqlalchemy.dialects.mysql import VARCHAR
import uuid
from .extensions import db

class BaseModel(db.Model):
    """基础模型类"""
    __abstract__ = True
    
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

class User(BaseModel):
    """用户表"""
    __tablename__ = 'users'
    
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()).replace('-', ''), comment='用户ID')
    openid = Column(String(100), nullable=False, unique=True, comment='微信openid')
    unionid = Column(String(100), comment='微信unionid')
    nickname = Column(String(100), comment='昵称')
    avatar_url = Column(String(500), comment='头像URL')
    # 移除 session_key，仅在需要解密时临时使用或直接依赖openid认证
    last_login = Column(DateTime, default=datetime.utcnow, comment='最后登录时间')
    is_active = Column(Boolean, default=True, comment='是否有效')
    
    # 关联关系
    user_company = db.relationship('UserCompany', backref='user', uselist=False, lazy=True)
    api_logs = db.relationship('ApiCallLog', backref='user', lazy=True)
    message_logs = db.relationship('MessageLog', backref='user', lazy=True)
    
    # 索引
    __table_args__ = (
        Index('idx_openid', 'openid'),
    )
    
    def __repr__(self):
        return f'<User {self.openid}>'

class UserCompany(BaseModel):
    """用户关联企业表（原ErpBinding）"""
    __tablename__ = 'user_companies'
    
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()).replace('-', ''), comment='关联ID')
    user_id = Column(String(64), db.ForeignKey('users.id'), nullable=False, comment='用户ID')
    company_code = Column(String(100), comment='客户/企业编号')
    company_name = Column(String(200), comment='客户/企业名称')
    customer_id = Column(String(100), comment='SaaS系统中的客户ID')
    invite_code = Column(String(50), comment='绑定时使用的邀请码')
    owner_id = Column(String(100), comment='所有者ID')
    bound_at = Column(DateTime, default=datetime.utcnow, comment='绑定时间')
    is_valid = Column(Boolean, default=True, comment='是否有效')
    
    # 索引
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_invite_code', 'invite_code'),
    )
    
    def __repr__(self):
        return f'<UserCompany {self.company_name}>'

class ApiCallLog(BaseModel):
    """API调用日志表"""
    __tablename__ = 'api_call_logs'
    
    log_id = Column(String(64), primary_key=True, comment='日志ID')
    user_id = Column(String(64), db.ForeignKey('users.id'), comment='用户ID')
    api_endpoint = Column(String(200), nullable=False, comment='API端点')
    request_method = Column(String(10), nullable=False, comment='请求方法')
    request_params = Column(Text, comment='请求参数')
    response_status = Column(Integer, comment='响应状态码')
    response_data = Column(Text, comment='响应数据')
    response_time_ms = Column(Integer, comment='响应时间毫秒')
    error_message = Column(Text, comment='错误信息')
    called_at = Column(DateTime, default=datetime.utcnow, comment='调用时间')
    
    # 索引
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_api_endpoint', 'api_endpoint'),
        Index('idx_called_at', 'called_at'),
    )
    
    def __repr__(self):
        return f'<ApiCallLog {self.api_endpoint}>'

class MessageLog(BaseModel):
    """消息发送日志表"""
    __tablename__ = 'message_logs'
    
    msg_id = Column(String(64), primary_key=True, comment='消息ID')
    user_id = Column(String(64), db.ForeignKey('users.id'), nullable=False, comment='用户ID')
    template_id = Column(String(100), nullable=False, comment='模板ID')
    msg_content = Column(Text, comment='消息内容')
    msg_status = Column(String(20), default='sent', comment='发送状态')
    sent_at = Column(DateTime, default=datetime.utcnow, comment='发送时间')
    error_detail = Column(Text, comment='错误详情')
    
    # 索引
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_template_id', 'template_id'),
        Index('idx_sent_at', 'sent_at'),
    )
    
    def __repr__(self):
        return f'<MessageLog {self.template_id}>'

class SystemConfig(BaseModel):
    """系统配置表"""
    __tablename__ = 'system_configs'
    
    config_key = Column(String(100), primary_key=True, comment='配置键')
    config_value = Column(Text, comment='配置值')
    description = Column(String(500), comment='配置描述')
    is_active = Column(Boolean, default=True, comment='是否启用')
    
    def __repr__(self):
        return f'<SystemConfig {self.config_key}>'

# 工具函数
def generate_uuid():
    """生成UUID"""
    return str(uuid.uuid4()).replace('-', '')

def get_current_timestamp():
    """获取当前时间戳"""
    return int(datetime.utcnow().timestamp() * 1000)