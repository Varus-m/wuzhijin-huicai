import logging
import json
import time
from functools import wraps
import jwt
from flask import request, jsonify, current_app
from datetime import datetime
from .models import db, ApiCallLog, generate_uuid, User, UserCompany

logger = logging.getLogger(__name__)

def verify_token(f):
    """JWT Token 验证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # 从 Authorization 头获取 token
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify(create_response(False, "未提供认证令牌")), 401
        
        try:
            # 解码 token
            payload = jwt.decode(
                token, 
                current_app.config['SECRET_KEY'], 
                algorithms=["HS256"]
            )
            
            # 将 user_id 注入到 request 中
            request.user_id = payload['user_id']
            request.user_openid = payload['openid']
            
        except jwt.ExpiredSignatureError:
            return jsonify(create_response(False, "令牌已过期")), 401
        except jwt.InvalidTokenError:
            return jsonify(create_response(False, "无效的令牌")), 401
        except Exception as e:
            logger.error(f"Token验证失败: {str(e)}")
            return jsonify(create_response(False, "认证失败")), 401
            
        return f(*args, **kwargs)
    
    return decorated

def create_response(success: bool, message: str, data: dict = None) -> dict:
    """创建统一响应格式"""
    response = {
        "success": success,
        "message": message,
        "timestamp": int(datetime.utcnow().timestamp() * 1000)
    }
    
    if data is not None:
        response["data"] = data
    
    return response

def is_admin_user(user_id: str) -> bool:
    """判断用户是否为管理员（基于配置）"""
    try:
        admin_ids = current_app.config.get('ADMIN_USER_IDS', []) or []
        return user_id in admin_ids
    except Exception:
        return False

def verify_invite_code(f):
    """企业绑定邀请码校验装饰器：非管理员必须已绑定企业邀请码"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = getattr(request, 'user_id', None)
        if not user_id:
            return jsonify(create_response(False, "认证信息缺失")), 401
        
        # 初始化 binding
        request.user_binding = None
        
        user = User.query.filter_by(id=user_id, is_active=True).first()
        if not user:
            return jsonify(create_response(False, "用户不存在")), 200
            
        # 检查绑定
        binding = UserCompany.query.filter_by(user_id=user.id, is_valid=True).first()
        
        # 管理员豁免校验，但如果有绑定信息还是会带上
        if is_admin_user(user_id):
            if binding:
                request.user_binding = binding
            return f(*args, **kwargs)
            
        if not binding or not binding.invite_code or not binding.customer_id:
            resp = create_response(False, "未绑定企业")
            resp["code"] = "NEED_INVITE_BIND"
            return jsonify(resp), 200
            
        request.user_binding = binding
        return f(*args, **kwargs)
    return decorated

def validate_request(required_fields: list = None, optional_fields: list = None):
    """请求参数验证装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                data = request.get_json() or {}
                
                # 检查必需字段
                if required_fields:
                    missing_fields = []
                    for field in required_fields:
                        if field not in data or data[field] is None:
                            missing_fields.append(field)
                    
                    if missing_fields:
                        return jsonify(create_response(
                            False, 
                            f"缺少必需参数: {', '.join(missing_fields)}"
                        )), 400
                
                # 验证可选字段
                if optional_fields:
                    for field in optional_fields:
                        if field in data and data[field] is not None:
                            # 这里可以添加字段类型验证
                            pass
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"请求参数验证失败: {str(e)}")
                return jsonify(create_response(False, "请求参数格式错误")), 400
        
        return decorated_function
    return decorator

def log_api_call(user_id: str, endpoint: str, method: str, 
                status_code: int, response_time: int, 
                request_params: dict = None, response_data: dict = None, 
                error_message: str = None):
    """记录API调用日志"""
    try:
        log = ApiCallLog(
            log_id=generate_uuid(),
            user_id=user_id,
            api_endpoint=endpoint,
            request_method=method,
            request_params=json.dumps(request_params, ensure_ascii=False) if request_params else None,
            response_status=status_code,
            response_data=json.dumps(response_data, ensure_ascii=False) if response_data else None,
            response_time_ms=response_time,
            error_message=error_message,
            called_at=datetime.utcnow()
        )
        
        db.session.add(log)
        db.session.commit()
        
    except Exception as e:
        logger.error(f"记录API调用日志失败: {str(e)}")
        db.session.rollback()

def measure_time(f):
    """测量函数执行时间的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        try:
            result = f(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000  # 转换为毫秒
            
            # 如果执行时间超过阈值，记录警告
            if execution_time > 1000:  # 超过1秒
                logger.warning(f"函数 {f.__name__} 执行时间过长: {execution_time:.2f}ms")
            
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"函数 {f.__name__} 执行失败，耗时: {execution_time:.2f}ms, 错误: {str(e)}")
            raise
    
    return decorated_function

def rate_limit(max_calls: int = 100, time_window: int = 3600):
    """简单的速率限制装饰器"""
    def decorator(f):
        call_counts = {}
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取客户端标识（这里简化处理，实际应该基于用户或IP）
            client_id = request.remote_addr or "unknown"
            current_time = time.time()
            
            # 清理过期的调用记录
            expired_keys = [
                key for key, (timestamp, _) in call_counts.items()
                if current_time - timestamp > time_window
            ]
            for key in expired_keys:
                del call_counts[key]
            
            # 检查速率限制
            client_key = f"{client_id}:{f.__name__}"
            if client_key in call_counts:
                timestamp, count = call_counts[client_key]
                if current_time - timestamp <= time_window:
                    if count >= max_calls:
                        return jsonify(create_response(
                            False, 
                            f"请求过于频繁，请稍后再试"
                        )), 429
                    call_counts[client_key] = (timestamp, count + 1)
                else:
                    call_counts[client_key] = (current_time, 1)
            else:
                call_counts[client_key] = (current_time, 1)
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def handle_errors(f):
    """统一错误处理装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
            
        except ValueError as e:
            logger.warning(f"值错误: {str(e)}")
            return jsonify(create_response(False, f"参数错误: {str(e)}")), 400
            
        except PermissionError as e:
            logger.warning(f"权限错误: {str(e)}")
            return jsonify(create_response(False, f"权限不足: {str(e)}")), 403
            
        except KeyError as e:
            logger.warning(f"键错误: {str(e)}")
            return jsonify(create_response(False, f"数据错误: {str(e)}")), 400
            
        except Exception as e:
            logger.error(f"未预期的错误: {str(e)}", exc_info=True)
            return jsonify(create_response(False, "服务器内部错误")), 500
    
    return decorated_function

def validate_openid_format(openid: str) -> bool:
    """验证openid格式"""
    if not openid:
        return False
    
    # OpenID通常是28位字符串
    if len(openid) != 28:
        return False
    
    # 检查是否只包含字母和数字
    if not openid.isalnum():
        return False
    
    return True

def validate_phone_number(phone: str) -> bool:
    """验证手机号格式"""
    if not phone:
        return False
    
    # 中国大陆手机号格式：1开头，第二位3-9，后面9位数字
    import re
    pattern = r'^1[3-9]\d{9}$'
    return bool(re.match(pattern, phone))

def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    if not email:
        return False
    
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def safe_json_loads(json_str: str, default=None):
    """安全地解析JSON字符串"""
    try:
        if json_str:
            return json.loads(json_str)
        return default
    except (json.JSONDecodeError, TypeError):
        return default

def safe_json_dumps(obj, default=None):
    """安全地将对象转换为JSON字符串"""
    try:
        if obj is not None:
            return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
        return default
    except (TypeError, ValueError):
        return default

def get_client_ip():
    """获取客户端IP地址"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def generate_order_no():
    """生成订单号"""
    import random
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_num = str(random.randint(1000, 9999))
    return f"ORD{timestamp}{random_num}"

def format_datetime(dt: datetime, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """格式化日期时间"""
    if not dt:
        return ""
    return dt.strftime(format_str)

def parse_datetime(date_str: str, format_str: str = '%Y-%m-%d %H:%M:%S') -> datetime:
    """解析日期时间字符串"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, format_str)
    except ValueError:
        return None

def get_current_timestamp():
    """获取当前时间戳（毫秒）"""
    return int(datetime.utcnow().timestamp() * 1000)

def get_date_days_ago(days: int) -> datetime:
    """获取几天前的日期"""
    from datetime import timedelta
    return datetime.utcnow() - timedelta(days=days)
