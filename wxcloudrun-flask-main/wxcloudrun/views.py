import logging
import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from .extensions import db, limiter
from .models import User, UserCompany, ApiCallLog, MessageLog, generate_uuid
from .erp_client import get_erp_client, ErpClient
from .wechat_client import get_wechat_client, send_order_status_notification, send_material_progress_notification, send_delivery_notification
import jwt
from .utils import validate_request, create_response, log_api_call, verify_token, verify_invite_code

logger = logging.getLogger(__name__)

# 创建蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')

# 工具函数
def get_current_timestamp():
    """获取当前时间戳"""
    return int(datetime.utcnow().timestamp() * 1000)

def get_user_by_id(user_id: str) -> User:
    """通过用户ID获取用户"""
    if not user_id:
        return None
    return User.query.filter_by(id=user_id, is_active=True).first()

def get_user_by_openid(openid: str) -> User:
    """获取用户"""
    return User.query.filter_by(openid=openid, is_active=True).first()

def create_user(openid: str, unionid: str = None, user_info: dict = None) -> User:
    """创建用户"""
    user = User(
        id=generate_uuid(),
        openid=openid,
        unionid=unionid,
        nickname=user_info.get('nickName') if user_info else None,
        avatar_url=user_info.get('avatarUrl') if user_info else None,
        last_login=datetime.utcnow(),
        is_active=True
    )
    db.session.add(user)
    db.session.commit()
    return user

# 认证相关API
@api_bp.route('/auth/wx-login', methods=['POST'])
@limiter.limit("10 per minute")
def wx_login():
    """微信小程序登录"""
    try:
        data = request.get_json()
        if not data:
            return jsonify(create_response(False, "请求数据不能为空")), 200
        
        code = data.get('code')
        user_info = data.get('userInfo') or {}
        
        if not code:
            return jsonify(create_response(False, "code不能为空")), 400
        
        # 调用微信接口验证code
        wechat_client = get_wechat_client()
        wx_result = wechat_client.code2session(code)
        
        openid = wx_result.get('openid')
        # session_key = wx_result.get('session_key') # 不再需要存储
        unionid = wx_result.get('unionid')
        
        if not openid:
            return jsonify(create_response(False, "获取openid失败")), 400
        
        # 查找或创建用户
        user = get_user_by_openid(openid)
        if not user:
            user = create_user(openid, unionid, user_info)
        else:
            # 更新最后登录时间
            user.unionid = unionid
            user.last_login = datetime.utcnow()
            # 如果有传入用户信息，则更新
            if user_info.get('nickName'):
                user.nickname = user_info.get('nickName')
            if user_info.get('avatarUrl'):
                user.avatar_url = user_info.get('avatarUrl')
            db.session.commit()
        
        # 记录API调用
        log_api_call(
            user_id=user.id,
            endpoint='/api/auth/wx-login',
            method='POST',
            status_code=200,
            response_time=0
        )
        
        # 生成 JWT Token
        token_payload = {
            'openid': openid,
            'user_id': user.id,
            'exp': datetime.utcnow() + timedelta(days=7) # Token 7天过期
        }
        token = jwt.encode(token_payload, current_app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify(create_response(True, "登录成功", {
            "token": token,  # 返回 token
            # "sessionKey": session_key, # 不再返回
            "openid": openid,
            "unionid": unionid,
            "userId": user.id,
            "expiresAt": int((datetime.utcnow() + timedelta(days=7)).timestamp() * 1000)
        }))
        
    except Exception as e:
        logger.error(f"微信登录失败: {str(e)}")
        return jsonify(create_response(False, f"登录失败: {str(e)}")), 500

@api_bp.route('/auth/bind-company', methods=['POST'])
@limiter.limit("5 per minute")
@verify_token
def bind_company():
    """企业绑定 (通过微信邀请码)"""
    try:
        # 从 Token 获取 user_id（后端以 user_id 为准）
        user_id = getattr(request, 'user_id', None)

        data = request.get_json()
        if not data:
            return jsonify(create_response(False, "请求数据不能为空")), 400
        
        invite_code = (data.get('inviteCode') or '').strip()
        
        # 邀请码校验：允许多次使用，不做格式限制
        if not invite_code:
            return jsonify(create_response(False, "邀请码不能为空")), 200
        
        # 验证用户是否存在
        user = User.query.filter_by(id=user_id, is_active=True).first()
        if not user:
            return jsonify(create_response(False, "用户不存在")), 200
        
        # 调用ERP接口验证邀请码
        erp_client = get_erp_client()
        verify_result = erp_client.verify_invite_code(invite_code)
        if not verify_result.get('success'):
            return jsonify(create_response(False, verify_result.get('error', "邀请码无效"))), 200
        customer = verify_result.get('customer', {})
        if not customer:
            return jsonify(create_response(False, "未找到对应企业信息")), 200
        # 服务器端二次校验：必须严格匹配返回的微信邀请码字段
        customer_invite = str(customer.get('微信邀请码', '')).strip()
        if customer_invite != invite_code:
            return jsonify(create_response(False, "邀请码不匹配")), 200
        # 关键字段校验
        if not customer.get('id') or not customer.get('name'):
            return jsonify(create_response(False, "企业数据不完整，绑定失败")), 200
            
        # 创建绑定关系；如果已存在绑定则提示已绑定，不更新
        binding = UserCompany.query.filter_by(user_id=user.id).first()
        if binding:
            return jsonify(create_response(True, "已绑定该企业", {
                "bindStatus": True,
                "companyInfo": {
                    "companyId": binding.company_code,
                    "companyName": binding.company_name,
                    "customerId": binding.customer_id
                }
            }))
        else:
            binding = UserCompany(
                id=generate_uuid(),
                user_id=user.id,
                company_code=customer.get('code'),
                company_name=customer.get('name'),
                customer_id=customer.get('id'),
                invite_code=invite_code,
                owner_id=customer.get('ownerId'),
                is_valid=True
            )
            db.session.add(binding)
        
        db.session.commit()
        
        # 记录API调用
        log_api_call(
            user_id=user.id,
            endpoint='/api/auth/bind-company',
            method='POST',
            status_code=200,
            response_time=0
        )
        
        return jsonify(create_response(True, "绑定成功", {
            "bindStatus": True,
            "companyInfo": {
                "companyId": binding.company_code, # 前端展示可能用code或name
                "companyName": binding.company_name,
                "customerId": binding.customer_id
            }
        }))
        
    except Exception as e:
        logger.error(f"企业绑定失败: {str(e)}")
        db.session.rollback()
        return jsonify(create_response(False, f"绑定失败: {str(e)}")), 500

# 订单相关API
@api_bp.route('/orders/search', methods=['GET'])
@limiter.limit("30 per minute")
@verify_token
@verify_invite_code
def search_orders():
    """搜索订单"""
    try:
        user_id = getattr(request, 'user_id', None)
        keyword = request.args.get('keyword', '')
        status = request.args.get('status', '')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 20))
        
        if not user_id:
            return jsonify(create_response(False, "认证信息缺失")), 401
        
        # 验证用户
        user = get_user_by_id(user_id)
        if not user:
            return jsonify(create_response(False, "用户不存在")), 200
        
        # 检查企业绑定
        binding = UserCompany.query.filter_by(user_id=user.id, is_valid=True).first()
        if not binding or not binding.customer_id:
            return jsonify(create_response(False, "用户未绑定企业")), 200
        
        # 调用ERP接口搜索订单
        erp_client = get_erp_client()
        erp_result = erp_client.search_orders(
            customer_id=binding.customer_id,
            keyword=keyword if keyword else None,
            status=status if status else None,
            page=page,
            page_size=page_size
        )
        
        # 记录API调用
        log_api_call(
            user_id=user.id,
            endpoint='/api/orders/search',
            method='GET',
            status_code=200,
            response_time=0
        )
        
        return jsonify(create_response(True, "查询成功", {
            "orders": erp_result.get('orders', []),
            "total": erp_result.get('total', 0),
            "page": page,
            "pageSize": page_size,
            "queryTime": get_current_timestamp(),
            "cacheHit": False
        }))
        
    except Exception as e:
        logger.error(f"搜索订单失败: {str(e)}")
        return jsonify(create_response(False, f"查询失败: {str(e)}")), 500

@api_bp.route('/orders/<order_id>/status', methods=['GET'])
@limiter.limit("60 per minute")
@verify_token
@verify_invite_code
def get_order_status(order_id: str):
    """获取订单状态"""
    try:
        # 从 request 获取 openid (由 verify_token 注入)
        user_id = getattr(request, 'user_id', None)
        
        # 调用ERP接口获取订单状态
        erp_client = get_erp_client()
        erp_result = erp_client.get_order_status(order_id)
        
        # 记录API调用
        log_api_call(
            user_id=user_id,
            endpoint=f'/api/orders/{order_id}/status',
            method='GET',
            status_code=200,
            response_time=0
        )
        
        return jsonify(create_response(True, "查询成功", erp_result))
        
    except Exception as e:
        logger.error(f"获取订单状态失败: {str(e)}")
        return jsonify(create_response(False, f"查询失败: {str(e)}")), 500

@api_bp.route('/orders/<order_id>/materials', methods=['GET'])
@limiter.limit("60 per minute")
@verify_token
@verify_invite_code
def get_order_materials(order_id: str):
    """获取订单物料清单"""
    try:
        # 从 request 获取 openid
        user_id = getattr(request, 'user_id', None)
        
        # 调用ERP接口获取订单物料
        erp_client = get_erp_client()
        erp_result = erp_client.get_order_materials(order_id)
        
        # 记录API调用
        log_api_call(
            user_id=user_id,
            endpoint=f'/api/orders/{order_id}/materials',
            method='GET',
            status_code=200,
            response_time=0
        )
        
        return jsonify(create_response(True, "查询成功", erp_result))
        
    except Exception as e:
        logger.error(f"获取订单物料失败: {str(e)}")
        return jsonify(create_response(False, f"查询失败: {str(e)}")), 500

@api_bp.route('/materials/<material_id>/progress', methods=['GET'])
@limiter.limit("60 per minute")
@verify_token
@verify_invite_code
def get_material_progress(material_id: str):
    """获取物料生产进度"""
    try:
        # 从 request 获取 openid
        user_id = getattr(request, 'user_id', None)
        
        # 调用ERP接口获取物料进度
        erp_client = get_erp_client()
        erp_result = erp_client.get_material_progress(material_id)
        
        # 记录API调用
        log_api_call(
            user_id=user_id,
            endpoint=f'/api/materials/{material_id}/progress',
            method='GET',
            status_code=200,
            response_time=0
        )
        
        return jsonify(create_response(True, "查询成功", erp_result))
        
    except Exception as e:
        logger.error(f"获取物料进度失败: {str(e)}")
        return jsonify(create_response(False, f"查询失败: {str(e)}")), 500

# 微信消息相关API
@api_bp.route('/wechat/template-msg', methods=['POST'])
@limiter.limit("10 per minute")
@verify_token
@verify_invite_code
def send_template_message():
    """发送微信模板消息"""
    try:
        data = request.get_json()
        if not data:
            return jsonify(create_response(False, "请求数据不能为空")), 200
        
        user_id = getattr(request, 'user_id', None)
        template_id = data.get('templateId')
        template_data = data.get('data')
        page = data.get('page')
        
        if not all([user_id, template_id, template_data]):
            return jsonify(create_response(False, "参数不完整")), 200
        
        # 验证用户
        user = get_user_by_id(user_id)
        if not user:
            return jsonify(create_response(False, "用户不存在")), 200
        
        # 发送模板消息
        wechat_client = get_wechat_client()
        result = wechat_client.send_template_message(
            openid=user.openid,
            template_id=template_id,
            data=template_data,
            page=page
        )
        
        # 记录消息日志
        message_log = MessageLog(
            msg_id=result.get("msgid", ""),
            user_id=user.id,
            template_id=template_id,
            msg_content=json.dumps(template_data, ensure_ascii=False),
            msg_status="sent",
            sent_at=datetime.utcnow()
        )
        db.session.add(message_log)
        db.session.commit()
        
        # 记录API调用
        log_api_call(
            user_id=user.id,
            endpoint='/api/wechat/template-msg',
            method='POST',
            status_code=200,
            response_time=0
        )
        
        return jsonify(create_response(True, "消息发送成功", {
            "msgid": result.get("msgid", ""),
            "status": "sent",
            "sendTime": get_current_timestamp()
        }))
        
    except Exception as e:
        logger.error(f"发送模板消息失败: {str(e)}")
        db.session.rollback()
        return jsonify(create_response(False, f"消息发送失败: {str(e)}")), 500

# 用户相关API
@api_bp.route('/user/profile', methods=['GET'])
@limiter.limit("30 per minute")
@verify_token
@verify_invite_code
def get_user_profile():
    """获取用户信息"""
    try:
        user_id = getattr(request, 'user_id', None)
        if not user_id:
            return jsonify(create_response(False, "认证信息缺失")), 401
        
        # 验证用户
        user = get_user_by_id(user_id)
        if not user:
            return jsonify(create_response(False, "用户不存在")), 200
        
        # 获取ERP绑定信息
        binding = UserCompany.query.filter_by(user_id=user.id, is_valid=True).first()
        
        # 记录API调用
        log_api_call(
            user_id=user.id,
            endpoint='/api/user/profile',
            method='GET',
            status_code=200,
            response_time=0
        )
        
        return jsonify(create_response(True, "查询成功", {
            "erpBinding": {
                "companyId": binding.company_code if binding else None,
                "companyName": binding.company_name if binding else None,
                "customerId": binding.customer_id if binding else None,
                "boundAt": int(binding.bound_at.timestamp() * 1000) if binding else None
            },
            # 兼容旧字段，虽已不再使用session过期机制
            "sessionExpiresAt": int((datetime.utcnow() + timedelta(days=30)).timestamp() * 1000)
        }))
        
    except Exception as e:
        logger.error(f"获取用户信息失败: {str(e)}")
        return jsonify(create_response(False, f"查询失败: {str(e)}")), 500

# 系统监控相关API
@api_bp.route('/health/check', methods=['GET'])
def health_check():
    """系统健康检查"""
    try:
        # 检查数据库连接
        db.session.execute('SELECT 1')
        
        # 检查ERP连接
        erp_client = get_erp_client()
        erp_status = erp_client.check_health()
        
        # 检查微信连接
        wechat_client = get_wechat_client()
        # 这里可以添加微信接口健康检查
        
        return jsonify(create_response(True, "系统健康", {
            "status": "healthy",
            "timestamp": get_current_timestamp(),
            "services": {
                "database": "healthy",
                "erp": "healthy" if erp_status.get("status") == "ok" else "unhealthy",
                "wechat": "healthy"
            }
        }))
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return jsonify(create_response(False, "系统异常", {
            "status": "unhealthy",
            "error": str(e)
        })), 500

@api_bp.route('/erp/status', methods=['GET'])
def erp_status():
    """ERP接口状态监控"""
    try:
        # 获取最近1小时的API调用统计
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        api_stats = db.session.query(
            ApiCallLog.api_endpoint,
            db.func.count(ApiCallLog.log_id).label('total_calls'),
            db.func.avg(ApiCallLog.response_time_ms).label('avg_response_time'),
            db.func.sum(db.case((ApiCallLog.response_status >= 400, 1), else_=0)).label('error_calls')
        ).filter(
            ApiCallLog.called_at >= one_hour_ago
        ).group_by(
            ApiCallLog.api_endpoint
        ).all()
        
        # 计算成功率
        stats = []
        for stat in api_stats:
            error_rate = (stat.error_calls / stat.total_calls * 100) if stat.total_calls > 0 else 0
            stats.append({
                "endpoint": stat.api_endpoint,
                "totalCalls": stat.total_calls,
                "avgResponseTime": round(float(stat.avg_response_time or 0), 2),
                "errorRate": round(error_rate, 2),
                "successRate": round(100 - error_rate, 2)
            })
        
        return jsonify(create_response(True, "查询成功", {
            "stats": stats,
            "checkTime": get_current_timestamp()
        }))
        
    except Exception as e:
        logger.error(f"获取ERP状态失败: {str(e)}")
        return jsonify(create_response(False, f"查询失败: {str(e)}")), 500

@api_bp.route('/metrics/performance', methods=['GET'])
def performance_metrics():
    """接口性能指标"""
    try:
        # 获取最近24小时的性能数据
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        
        # 按小时统计
        hourly_stats = db.session.query(
            db.func.date_format(ApiCallLog.called_at, '%Y-%m-%d %H:00:00').label('hour'),
            db.func.count(ApiCallLog.log_id).label('total_calls'),
            db.func.avg(ApiCallLog.response_time_ms).label('avg_response_time'),
            db.func.max(ApiCallLog.response_time_ms).label('max_response_time'),
            db.func.sum(db.case((ApiCallLog.response_status >= 400, 1), else_=0)).label('error_calls')
        ).filter(
            ApiCallLog.called_at >= one_day_ago
        ).group_by(
            db.func.date_format(ApiCallLog.called_at, '%Y-%m-%d %H:00:00')
        ).order_by(
            db.func.date_format(ApiCallLog.called_at, '%Y-%m-%d %H:00:00')
        ).all()
        
        # 按接口统计
        endpoint_stats = db.session.query(
            ApiCallLog.api_endpoint,
            db.func.count(ApiCallLog.log_id).label('total_calls'),
            db.func.avg(ApiCallLog.response_time_ms).label('avg_response_time'),
            db.func.max(ApiCallLog.response_time_ms).label('max_response_time'),
            db.func.sum(db.case((ApiCallLog.response_status >= 400, 1), else_=0)).label('error_calls')
        ).filter(
            ApiCallLog.called_at >= one_day_ago
        ).group_by(
            ApiCallLog.api_endpoint
        ).all()
        
        return jsonify(create_response(True, "查询成功", {
            "hourlyStats": [
                {
                    "hour": stat.hour,
                    "totalCalls": stat.total_calls,
                    "avgResponseTime": round(float(stat.avg_response_time or 0), 2),
                    "maxResponseTime": stat.max_response_time or 0,
                    "errorCalls": stat.error_calls,
                    "errorRate": round((stat.error_calls / stat.total_calls * 100) if stat.total_calls > 0 else 0, 2)
                }
                for stat in hourly_stats
            ],
            "endpointStats": [
                {
                    "endpoint": stat.api_endpoint,
                    "totalCalls": stat.total_calls,
                    "avgResponseTime": round(float(stat.avg_response_time or 0), 2),
                    "maxResponseTime": stat.max_response_time or 0,
                    "errorCalls": stat.error_calls,
                    "errorRate": round((stat.error_calls / stat.total_calls * 100) if stat.total_calls > 0 else 0, 2)
                }
                for stat in endpoint_stats
            ]
        }))
        
    except Exception as e:
        logger.error(f"获取性能指标失败: {str(e)}")
        return jsonify(create_response(False, f"查询失败: {str(e)}")), 500
