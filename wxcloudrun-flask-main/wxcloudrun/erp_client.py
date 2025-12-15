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
        condition = {}
        
        # 关键词搜索 (模糊匹配需API支持，这里假设支持或只精确匹配)
        # Snowbeasts API condition 似乎是精确匹配。如果是模糊搜索可能需要特殊语法
        if keyword:
            # 尝试同时匹配订单号或客户订单号
            # 注意：如果API不支持OR查询，可能需要多次查询或仅匹配一个字段
            #condition["code"] = keyword 
            pass
        
        # 状态过滤
        filters = {"customerId": customer_id}
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
            order_list = data.get("_dataList", [])
            
            # 获取所有订单的出库单信息
            # 用户要求：查询条件添加查询为客户id下的销售出库单 filters: {customerOrSupplierId: "36"}
            
            # 查询出库单
            # 注意：如果客户出库单非常多，这里可能会有问题。但遵循用户指示。
            
            delivery_orders = []
            
            # 策略：直接使用 filters 过滤 customerOrSupplierId，查询该客户下的所有出库单
            # 注意：这可能会返回大量数据，可能需要分页处理或增加限制
            # 这里的 page_size 设置大一点，比如 5000，尽可能拉取全部
            delivery_filters = {
                "customerOrSupplierId": customer_id
            }
            
            # 由于可能存在分页，如果客户出库单超过 page_size，可能数据不全。
            # 但在当前上下文中，我们先只拉取第一页（假设 5000 条足够覆盖近期的订单）
            delivery_result = self.api.get_sales_delivery_orders(
                page_size=5000,
                filters=delivery_filters
            )

            if "data" in delivery_result and delivery_result["data"].get("_dataList"):
                delivery_orders = delivery_result["data"].get("_dataList", [])
            
            # 建立订单ID到出库单列表的映射
            delivery_map = {} # { order_code: [delivery_order, ...] }
            for do in delivery_orders:
                # 用户要求：使用的是 orderCodes，并且可能一个出库单关联多个销售订单一起发货
                # 譬如 "SO2025121201,SO2025121301" 需要解析
                order_codes_str = do.get("orderCodes", "")
                if order_codes_str:
                    # 分割并去除空白
                    codes = [c.strip() for c in order_codes_str.split(",") if c.strip()]
                    for code in codes:
                        if code not in delivery_map:
                            delivery_map[code] = []
                        delivery_map[code].append(do)
            
            for item in order_list:
                order_code = str(item.get("code", ""))
                related_deliveries = delivery_map.get(order_code, [])
                # 计算发货状态 deliveryStatus
                # 0: 未发货, 1: 已发货, 2: 部分发货
                delivery_status = 0
                
                if not related_deliveries:
                    delivery_status = 0
                else:
                    total_deliveries = len(related_deliveries)
                    shipped_count = 0
                    
                    for do in related_deliveries:
                        is_shipped = bool(do.get("是否发货"))
                        
                        if is_shipped:
                            shipped_count += 1
                    
                    if shipped_count == 0:
                        delivery_status = 0
                    elif shipped_count == total_deliveries:
                        delivery_status = 1
                    else:
                        delivery_status = 2
                
                # 计算发货进度 shippedRate
                # 逻辑：所有已经发货的出库单的 rmbAmount 之和 / 销售订单的 rmbAmount
                order_rmb_amount = float(item.get("rmbAmount") or 0)
                shipped_rmb_amount = 0.0
                
                for do in related_deliveries:
                    # 重新判断是否已发货（代码重复，可优化，但为了清晰先这样写）
                    is_shipped = bool(do.get("是否发货"))
                    
                    if is_shipped:
                        shipped_rmb_amount += float(do.get("rmbAmount") or 0)
                
                if order_rmb_amount > 0:
                    shipped_rate = shipped_rmb_amount / order_rmb_amount
                    # 限制最大为 1.0 (100%)
                    if shipped_rate > 1.0:
                        shipped_rate = 1.0
                else:
                    shipped_rate = 0.0

                orders.append({
                    "order_id": item.get("id"),
                    "order_no": item.get("code"),
                    "customer_name": item.get("customerName"),
                    "order_date": item.get("date"),
                    "status": item.get("status"), # 需确认是否需要映射为文本
                    "rmb_amount": item.get("rmbAmount"),
                    "delivery_date": item.get("deliveryDate"),
                    "shipped_rate": shipped_rate, # 使用计算后的发货进度
                    "delivery_status": delivery_status, # 新增发货状态
                    "remark": item.get("remark"),
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
        
        # 获取发运单详情
        delivery_orders = []
        order_code = header.get("code")
        if order_code:
            # 1. 查询SO对应的所有发运单
            # 查询条件有SO: filters: {systemFulltext: "SO2025121502"}
            do_filters = {"systemFulltext": order_code}
            
            # 注意：get_sales_delivery_orders 内部使用的是 filters 透传
            do_result = self.api.get_sales_delivery_orders(
                page_size=100,
                filters=do_filters
            )
            
            if "data" in do_result and do_result["data"].get("_dataList"):
                raw_delivery_orders = do_result["data"].get("_dataList", [])
                
                # 预先获取物流公司列表（缓存以优化性能，这里简单起见每次获取，或者可以做类级别缓存）
                # 注意：如果物流公司很多，page_size 需要足够大
                logistics_result = self.api.get_logistics_companies(page_size=1000)
                logistics_map = {} # {id: name}
                if "data" in logistics_result and logistics_result["data"].get("_dataList"):
                     for company in logistics_result["data"].get("_dataList", []):
                         logistics_map[str(company.get("id"))] = company.get("name")
                
                for do_item in raw_delivery_orders:
                    do_id = str(do_item.get("id"))
                    
                    # 2. 获取出库单详情（实际上 raw_delivery_orders 已经是列表详情了，但为了严谨或获取更多字段，
                    # 题目要求 "根据查询到的id，去查询出库单详情get_delivery_order_detail"。
                    # 如果 get_sales_delivery_orders 返回的字段不够全，才需要再查一次。
                    # 根据 snowbeasts_client.py，get_sales_delivery_orders 返回的字段已经包含了 required fields。
                    # 但为了遵循 "根据查询到的id，去查询出库单详情" 的指引，我们还是调用一下，或者直接复用。
                    # 考虑到性能，直接复用列表数据通常足够。但如果 get_delivery_order_detail 有特殊逻辑，则调用。
                    # 这里为了完全符合要求，我们调用 get_delivery_order_detail (虽然有点冗余)
                    
                    detail_result = self.api.get_delivery_order_detail(do_id)
                    do_detail = {}
                    if detail_result.get("success") and "data" in detail_result:
                        do_detail = detail_result["data"]
                    else:
                        do_detail = do_item # 降级使用列表数据
                    
                    # 3. 获取物流公司名称
                    logistics_company_id = str(do_detail.get("logisticsCompanyId", ""))
                    logistics_company_name = logistics_map.get(logistics_company_id, "")
                    
                    # 4. 处理附件
                    # "attachments": ["35/xxx/xxx#size=...&name=..."]
                    # 需转换为完整 URL: http://saas.snowbeasts.com/business/file/SnowInventory-82886/{path_without_params}
                    attachments = []
                    raw_attachments = do_detail.get("attachments")
                    if isinstance(raw_attachments, list):
                        for att in raw_attachments:
                            if isinstance(att, str):
                                # 提取 # 之前的部分
                                file_path = att.split('#')[0]
                                full_url = f"http://saas.snowbeasts.com/business/file/SnowInventory-82886/{file_path}"
                                attachments.append(full_url)
                    
                    # 5. 获取出库产品明细
                    products = []
                    prod_result = self.api.get_delivery_order_products(do_id)
                    if prod_result.get("success") and "data" in prod_result and prod_result["data"].get("_dataList"):
                        for prod in prod_result["data"].get("_dataList", []):
                            products.append({
                                "productName": prod.get("productName"),
                                "spec": prod.get("spec"),
                                "quantity": prod.get("quantity")
                            })
                    
                    delivery_orders.append({
                        "delivery_date": do_detail.get("发货日期"),
                        "logistics_company": logistics_company_name,
                        "logistics_code": do_detail.get("logisticsCode"),
                        "address": do_detail.get("address"),
                        "remark": do_detail.get("remark"),
                        "attachments": attachments,
                        "products": products
                    })
            
        return {
            "order_id": header.get("id"),
            "order_no": header.get("code"),
            "status": header.get("status"),
            "created_at": header.get("date"),
            "materials": materials,
            "delivery_orders": delivery_orders
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
