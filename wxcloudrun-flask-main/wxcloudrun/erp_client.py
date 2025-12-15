import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from flask import current_app
from .snowbeasts_client import SnowbeastsAPI
from .models import generate_uuid, ApiCallLog, db

logger = logging.getLogger(__name__)

class ErpClient:
    """ERP系统客户端 (适配Snowbeasts SaaS)"""
    
    def __init__(self):
        self.api = SnowbeastsAPI()
        # 确保初始化时尝试登录（虽然后续调用也会自动确保）
        # self.api._ensure_login() 
    
    def _log_api_call(self, endpoint: str, method: str, status_code: int, response_time: float):
        """记录API调用日志"""
        try:
            log = ApiCallLog(
                log_id=generate_uuid(),
                api_endpoint=endpoint,
                request_method=method,
                response_status=status_code,
                response_time_ms=int(response_time),
                called_at=datetime.utcnow()
            )
            
            db.session.add(log)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"记录API调用日志失败: {str(e)}")

    def verify_invite_code(self, invite_code: str) -> Dict[str, Any]:
        """验证邀请码并返回客户信息"""
        return self.api.find_customer_by_invite_code(invite_code)
    
    def search_orders(self, customer_id: str, keyword: str = None, status: str = None, 
                     page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        搜索订单
        Args:
            customer_id: 客户ID (必填，用于隔离数据)
            keyword: 搜索关键词 (对应 code 或 customerOrderCode)
            status: 订单状态
        """
        condition = {
            "customerId": customer_id
        }
        
        # 关键词搜索 (模糊匹配需API支持，这里假设支持或只精确匹配)
        # Snowbeasts API condition 似乎是精确匹配。如果是模糊搜索可能需要特殊语法
        if keyword:
            # 尝试同时匹配订单号或客户订单号
            # 注意：如果API不支持OR查询，可能需要多次查询或仅匹配一个字段
            condition["code"] = keyword 
        
        # 状态过滤
        filters = {}
        if status:
            # 假设 status 传入的是数字或需要映射
            # 示例: 1:未开始, 2:进行中, 4:已完成, 5:已取消 (参考 snowbeasts_apis.py 中的 defaults)
            # 这里直接透传，或者前端传递正确的值
            pass 

        # 调用API (注意页码 Snowbeasts 从0开始)
        result = self.api.get_sales_order_page_list(
            condition=condition,
            page=page-1 if page > 0 else 0,
            page_size=page_size,
            filters=filters
        )
        
        # 转换返回格式适配前端
        orders = []
        total = 0
        
        if "data" in result and result["data"].get("_dataList"):
            data = result["data"]
            total = data.get("_count", 0)
            for item in data.get("_dataList", []):
                orders.append({
                    "order_id": item.get("id"),
                    "order_no": item.get("code"),
                    "customer_name": item.get("customerName"),
                    "order_date": item.get("date"),
                    "status": item.get("status"), # 需确认是否需要映射为文本
                    # "materials": [] # 列表页通常不含详情
                })
                
        return {
            "orders": orders,
            "total": total
        }

    def get_order_detail(self, order_id: str) -> Dict[str, Any]:
        """获取订单详情"""
        result = self.api.get_order_with_lines(order_id)
        
        if result.get("error"):
            return {"success": False, "error": result["error"]}
            
        header = result.get("order_header", {})
        lines = result.get("order_lines", {}).get("data", {}).get("_dataList", [])
        
        # 转换格式
        materials = []
        for line in lines:
            materials.append({
                "material_id": line.get("id"),
                "material_code": line.get("productCode"),
                "material_name": line.get("productName"),
                "quantity": line.get("quantity"),
                "produced_quantity": line.get("producedQuantity"),
                "shipped_quantity": line.get("shippedQuantity"),
                "status": line.get("status")
            })
            
        return {
            "order_id": header.get("id"),
            "order_no": header.get("code"),
            "status": header.get("status"),
            "created_at": header.get("date"),
            "materials": materials
        }

    # 其他方法按需适配或保留空实现
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        return self.get_order_detail(order_id)
        
    def get_order_materials(self, order_id: str) -> Dict[str, Any]:
        return self.get_order_detail(order_id)
        
    def get_material_progress(self, material_id: str) -> Dict[str, Any]:
        # 暂时无法精确获取单个物料进度，除非遍历。
        # 这里建议前端通过订单详情获取
        return {}

# 全局ERP客户端实例
_erp_client: Optional[ErpClient] = None

def get_erp_client() -> ErpClient:
    """获取ERP客户端实例"""
    global _erp_client
    
    if _erp_client is None:
        _erp_client = ErpClient()
    
    return _erp_client
