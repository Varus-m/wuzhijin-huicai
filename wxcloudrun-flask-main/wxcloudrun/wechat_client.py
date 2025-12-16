import requests
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from flask import current_app
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class WeChatClient:
    """微信客户端"""
    
    def __init__(self, appid: str, secret: str):
        self.appid = appid
        self.secret = secret
        self.base_url = "https://api.weixin.qq.com"
        self.access_token = None
        self.token_expires_at = 0
    
    def _get_access_token(self) -> str:
        """获取微信访问令牌"""
        current_time = int(time.time())
        
        # 检查令牌是否过期
        if self.access_token and current_time < self.token_expires_at:
            return self.access_token
        
        # 获取新的访问令牌
        url = f"{self.base_url}/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.appid,
            "secret": self.secret
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if "access_token" in data:
                self.access_token = data["access_token"]
                # 提前5分钟过期，避免临界问题
                self.token_expires_at = current_time + data.get("expires_in", 7200) - 300
                return self.access_token
            else:
                logger.error(f"获取微信访问令牌失败: {data}")
                raise Exception(f"获取访问令牌失败: {data.get('errmsg', '未知错误')}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"请求微信访问令牌失败: {str(e)}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    def code2session(self, code: str) -> Dict[str, Any]:
        """微信登录凭证校验"""
        url = f"{self.base_url}/sns/jscode2session"
        params = {
            "appid": self.appid,
            "secret": self.secret,
            "js_code": code,
            "grant_type": "authorization_code"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if "openid" in data:
                return data
            else:
                logger.error(f"微信登录凭证校验失败: {data}")
                raise Exception(f"登录凭证校验失败: {data.get('errmsg', '未知错误')}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"请求微信登录凭证校验失败: {str(e)}")
            raise
    
    def send_template_message(self, openid: str, template_id: str, 
                            data: Dict[str, Any], page: str = None) -> Dict[str, Any]:
        """发送模板消息"""
        access_token = self._get_access_token()
        url = f"{self.base_url}/cgi-bin/message/subscribe/send"
        params = {"access_token": access_token}
        
        message_data = {
            "touser": openid,
            "template_id": template_id,
            "data": data
        }
        
        if page:
            message_data["page"] = page
        
        try:
            response = requests.post(url, params=params, json=message_data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get("errcode") == 0:
                logger.info(f"模板消息发送成功: {openid}, 模板ID: {template_id}")
                return result
            else:
                logger.error(f"模板消息发送失败: {result}")
                raise Exception(f"模板消息发送失败: {result.get('errmsg', '未知错误')}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"请求模板消息发送失败: {str(e)}")
            raise
    
    def get_template_list(self) -> List[Dict[str, Any]]:
        """获取模板列表"""
        access_token = self._get_access_token()
        url = f"{self.base_url}/cgi-bin/wxopen/template/list"
        params = {"access_token": access_token}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get("errcode") == 0:
                return data.get("list", [])
            else:
                logger.error(f"获取模板列表失败: {data}")
                raise Exception(f"获取模板列表失败: {data.get('errmsg', '未知错误')}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"请求模板列表失败: {str(e)}")
            raise
    
    def send_custom_message(self, openid: str, content: str) -> Dict[str, Any]:
        """发送客服消息"""
        access_token = self._get_access_token()
        url = f"{self.base_url}/cgi-bin/message/custom/send"
        params = {"access_token": access_token}
        
        message_data = {
            "touser": openid,
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        
        try:
            response = requests.post(url, params=params, json=message_data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get("errcode") == 0:
                logger.info(f"客服消息发送成功: {openid}")
                return result
            else:
                logger.error(f"客服消息发送失败: {result}")
                raise Exception(f"客服消息发送失败: {result.get('errmsg', '未知错误')}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"请求客服消息发送失败: {str(e)}")
            raise

# 全局微信客户端实例
_wechat_client: Optional[WeChatClient] = None

def get_wechat_client() -> WeChatClient:
    """获取微信客户端实例"""
    global _wechat_client
    
    if _wechat_client is None:
        config = current_app.config
        _wechat_client = WeChatClient(
            appid=config['WECHAT_APPID'],
            secret=config['WECHAT_SECRET']
        )
    
    return _wechat_client

def reset_wechat_client():
    """重置微信客户端实例"""
    global _wechat_client
    _wechat_client = None

# 模板消息发送函数
def send_order_status_notification(openid: str, order_data: Dict[str, Any]) -> bool:
    """发送订单状态变更通知"""
    try:
        client = get_wechat_client()
        template_id = current_app.config['TEMPLATE_IDS']['order_status_change']
        
        # 格式化模板数据
        template_data = {
            "thing1": {"value": order_data.get("order_no", "")},
            "phrase2": {"value": order_data.get("status_text", "")},
            "date3": {"value": order_data.get("update_time", "")},
            "thing4": {"value": order_data.get("remark", "订单状态已更新")}
        }
        
        result = client.send_template_message(
            openid=openid,
            template_id=template_id,
            data=template_data,
            page=f"/pages/order-detail/order-detail?orderNo={order_data.get('order_no', '')}"
        )
        
        # 记录消息日志
        from .models import MessageLog, db
        
        log = MessageLog(
            msg_id=result.get("msgid", ""),
            session_id=openid,  # 简化处理，实际应该关联到session
            template_id=template_id,
            msg_content=json.dumps(template_data, ensure_ascii=False),
            msg_status="sent",
            sent_at=datetime.utcnow()
        )
        
        db.session.add(log)
        db.session.commit()
        
        return True
        
    except Exception as e:
        logger.error(f"发送订单状态通知失败: {str(e)}")
        
        # 记录失败日志
        try:
            from .models import MessageLog, db
            
            log = MessageLog(
                msg_id=generate_uuid(),
                session_id=openid,
                template_id=current_app.config['TEMPLATE_IDS']['order_status_change'],
                msg_content=json.dumps(order_data, ensure_ascii=False),
                msg_status="failed",
                sent_at=datetime.utcnow(),
                error_detail=str(e)
            )
            
            db.session.add(log)
            db.session.commit()
        except Exception as log_error:
            logger.error(f"记录消息失败日志失败: {str(log_error)}")
        
        return False

def send_material_progress_notification(openid: str, material_data: Dict[str, Any]) -> bool:
    """发送物料进度通知"""
    try:
        client = get_wechat_client()
        template_id = current_app.config['TEMPLATE_IDS']['material_progress']
        
        # 格式化模板数据
        template_data = {
            "thing1": {"value": material_data.get("material_name", "")},
            "number2": {"value": f"{material_data.get('progress', 0)}%"},
            "thing3": {"value": material_data.get("status_text", "")},
            "date4": {"value": material_data.get("update_time", "")}
        }
        
        result = client.send_template_message(
            openid=openid,
            template_id=template_id,
            data=template_data
        )
        
        return True
        
    except Exception as e:
        logger.error(f"发送物料进度通知失败: {str(e)}")
        return False

def send_delivery_notification(openid: str, delivery_data: Dict[str, Any]) -> bool:
    """发送发货通知"""
    try:
        client = get_wechat_client()
        template_id = current_app.config['TEMPLATE_IDS']['delivery_notice']
        
        # 格式化模板数据
        template_data = {
            "character_string1": {"value": delivery_data.get("tracking_no", "")},
            "thing2": {"value": delivery_data.get("delivery_company", "")},
            "time3": {"value": delivery_data.get("delivery_time", "")},
            "thing4": {"value": delivery_data.get("remark", "您的订单已发货")}
        }
        
        result = client.send_template_message(
            openid=openid,
            template_id=template_id,
            data=template_data
        )
        
        return True
        
    except Exception as e:
        logger.error(f"发送发货通知失败: {str(e)}")
        return False