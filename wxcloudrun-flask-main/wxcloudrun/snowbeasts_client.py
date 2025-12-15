import requests
import json
import time
from typing import Optional, Dict, Any

class SnowbeastsAPI:
    def __init__(self):
        self.base_url = "https://saas.snowbeasts.com/apps/service"
        self.session = requests.Session()
        self.jsessionid = None
        self.sid = None
        self.app_jsessionid = None  # 新增：存储app的jsessionid
        self.headers = {
            'Content-Type': 'application/json'
        }
        self._is_logged_in = False  # 添加登录状态标记
        self._last_login_time = 0  # 记录上次登录时间
        self._login_interval = 300  # 登录间隔时间（5分钟 = 300秒）
    
    def _ensure_login(self, account: str = "15068471011", password: str = "2a1b583f9a8d20004379fe836a76c5f0d84c7ef9") -> bool:
        """
        确保已登录，如果未登录或登录超时（5分钟）则自动重新登录
        
        Args:
            account: 账号
            password: 密码
        
        Returns:
            登录是否成功
        """
        current_time = time.time()
        
        # 检查是否需要重新登录：未登录 或 距离上次登录超过5分钟
        if (not self._is_logged_in or 
            not self.jsessionid or 
            not self.sid or 
            not self.app_jsessionid or 
            (current_time - self._last_login_time) > self._login_interval):
            
            # if (current_time - self._last_login_time) > self._login_interval and self._is_logged_in:
            #     print("登录已超时（5分钟），正在重新登录...")
            # else:
            #     print("检测到未登录，正在自动登录...")
            
            login_result = self.login(account, password)
            
            if "error" not in login_result:
                self._is_logged_in = True
                self._last_login_time = current_time
                return True
            else:
                print(f"自动登录失败: {login_result.get('error', '未知错误')}")
                return False
        
        return True
    
    def login(self, account: str = "15068471011", password: str = "2a1b583f9a8d20004379fe836a76c5f0d84c7ef9") -> Dict[str, Any]:
        """
        登录接口
        """
        login_url = f"{self.base_url}/login"
        
        payload = {
            "state": True,
            "account": account,
            "token": "",
            "password": password
        }
        
        try:
            response = self.session.post(
                login_url,
                json=payload,
                headers=self.headers
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 从响应的cookies中提取JSESSIONID和sid
            cookies = response.cookies
            if 'JSESSIONID' in cookies:
                self.jsessionid = cookies['JSESSIONID']
            
            if 'sid' in cookies:
                self.sid = cookies['sid']
            
            # 更新会话cookie
            self._update_session_headers()
            
            # 解析响应数据
            response_data = response.json()
            
            # print(f"登录成功！JSESSIONID: {self.jsessionid}, SID: {self.sid}")
            
            # 新增：获取app的jsessionid
            app_result = self._get_app_jsessionid()
            if app_result.get('success', False):
                # print(f"获取app jsessionid成功: {self.app_jsessionid}")
                self._is_logged_in = True
            else:
                print(f"获取app jsessionid失败: {app_result.get('error', '未知错误')}")
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            print(f"登录请求失败: {e}")
            return {"error": str(e)}
        except json.JSONDecodeError as e:
            print(f"响应解析失败: {e}")
            return {"error": "响应格式错误"}
    
    def _get_app_jsessionid(self) -> Dict[str, Any]:
        """
        使用sid获取app的jsessionid
        """
        if not self.sid:
            return {"success": False, "error": "缺少sid，请先登录"}
        
        app_url = "http://saas.snowbeasts.com/apps/user/open-app/82886"
        
        app_headers = {
            'Cookie': f'sid={self.sid}'
        }
        
        try:
            # 允许重定向，并获取最终的响应
            response = self.session.get(app_url, headers=app_headers, allow_redirects=True)
            response.raise_for_status()
            
            # 从响应的cookies中提取app的JSESSIONID
            cookies = response.cookies
            if 'JSESSIONID' in cookies:
                self.app_jsessionid = cookies['JSESSIONID']
                self._update_session_headers()
                # print(f"重定向后的最终URL: {response.url}")
                return {"success": True, "app_jsessionid": self.app_jsessionid, "final_url": response.url}
            else:
                # 如果没有在cookies中找到JSESSIONID，检查所有历史响应
                for hist_response in response.history:
                    hist_cookies = hist_response.cookies
                    if 'JSESSIONID' in hist_cookies:
                        self.app_jsessionid = hist_cookies['JSESSIONID']
                        self._update_session_headers()
                        # print(f"从重定向历史中获取到JSESSIONID: {self.app_jsessionid}")
                        return {"success": True, "app_jsessionid": self.app_jsessionid, "final_url": response.url}
                
                return {"success": False, "error": "未能从app响应中获取到JSESSIONID", "final_url": response.url}
                
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"请求app接口失败: {str(e)}"}
    
    def _update_session_headers(self):
        """
        更新会话头部信息
        """
        cookie_parts = []
        
        if self.jsessionid:
            cookie_parts.append(f"JSESSIONID={self.jsessionid}")
        
        cookie_parts.append("lang=zh-cn")
        
        if self.sid:
            cookie_parts.append(f"sid={self.sid}")
        
        if self.app_jsessionid:
            cookie_parts.append(f"app_JSESSIONID={self.app_jsessionid}")
        
        cookie_value = "; ".join(cookie_parts)
        self.headers['Cookie'] = cookie_value
        self.session.headers.update({'Cookie': cookie_value})
    
    def get_sales_order_page_list(self, 
                              app_name: str = "SnowInventory-82886",
                              form_id: int = 100001,
                              condition: Dict[str, Any] = None,
                              columns: list = None,
                              page: int = 0,
                              page_size: int = 20,
                              filters: Dict[str, Any] = None,
                              orderby: str = "") -> Dict[str, Any]:
        """
        查询业务页面列表（自动登录）
        """
        # 确保已登录
        if not self._ensure_login():
            return {"error": "登录失败，无法执行查询"}
        
        if condition is None:
            condition = {"customerId": None}
        
        if columns is None:
            columns = [] # Default columns skipped for brevity
        
        if filters is None:
            # filters = {"status": [1, 2, 4, 5]}
            # 用户要求取消默认的状态过滤，查询所有状态
            filters = {}
        
        payload = {
            "appName": app_name,
            "formId": form_id,
            "condition": condition,
            "columns": columns,
            "page": page,
            "pageSize": page_size,
            "filters": filters,
            "orderby": orderby
        }
        
        request_headers = {
            'Content-Type': 'application/json',
            'Cookie': f'JSESSIONID={self.app_jsessionid}; sid={self.sid}'
        }
        
        url = "http://saas.snowbeasts.com/business/getBusinessPageList"
        
        try:
            response = self.session.post(
                url,
                json=payload,
                headers=request_headers
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"查询请求失败: {e}")
            return {"error": str(e)}
        except json.JSONDecodeError as e:
            print(f"响应解析失败: {e}")
            return {"error": "响应格式错误"}
    
    def find_customer_by_invite_code(self, invite_code: str) -> Dict[str, Any]:
        """
        根据微信邀请码查找客户
        """
        if not invite_code:
            return {"error": "邀请码不能为空"}
            
        # 确保已登录
        if not self._ensure_login():
            return {"error": "登录失败，无法执行查询"}
            
        columns = [
            "customerType", "type", "code", "abbr", "name", "countryId", 
            "province", "city", "county", "category", "currency", "level", 
            "industry", "ownerId", "shareUserIds", "disable", "微信邀请码"
        ]
        
        # 尝试直接使用条件查询（如果支持）
        # 假设 condition 可以支持 微信邀请码 字段
        filters = {"微信邀请码": invite_code}
        
        result = self.get_sales_order_page_list(
            form_id=100004,  # 客户列表的formId
            filters=filters,
            columns=columns,
            page=0,
            page_size=1
        )
        
        if "data" in result and result["data"].get("_dataList"):
             return {"success": True, "customer": result["data"]["_dataList"][0]}
        
        # 如果直接查询不支持或没查到，可能需要遍历（但考虑到效率，先假设支持或只查第一页）
        # 如果需要遍历查找，可以扩展此处逻辑
        # 暂时返回未找到
        if "data" in result and result["data"].get("_count", 0) == 0:
             return {"success": False, "error": "无效的邀请码"}
             
        return {"success": False, "error": result.get("error", "查询失败")}

    def get_sales_delivery_orders(self, 
                                 sales_order_product_ids: list = None,
                                 page: int = 0,
                                 page_size: int = 20,
                                 orderby: str = "",
                                 filters: Dict[str, Any] = None,
                                 condition: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        获取销售出库单数据（自动登录）
        
        Args:
            sales_order_product_ids: 销售订单产品ID列表，为None时查询所有
            page: 页码，默认为 0
            page_size: 每页大小，默认为 20
            orderby: 排序字段
            filters: 过滤条件
            condition: 查询条件
        
        Returns:
            销售出库单数据
        """
        # 确保已登录
        if not self._ensure_login():
            return {"error": "登录失败，无法执行查询"}
        
        # 销售出库单的字段列表
        columns = [
            "finished", "code", "orderCodes", "date", "category", "customerOrSupplierId", 
            "projectIds", "salesOrderId", "currency", "exchangeRate", "salesOrderIds", 
            "customerOrderCodes", "collectionDate", "produceOrderId", "salesOrderCode", 
            "contact", "tel", "mobile", "address", "companyId", "userId", "ownerId", 
            "departmentId", "amount", "deductionAmount", "grossProfit", "rmbAmount", 
            "receivedAmount", "receivingAmount", "receivableAmount", "returnedAmount", 
            "returningAmount", "invoicedAmount", "invoicingAmount", "unInvoicedAmount", 
            "warehouseId", "reconciliation", "reconciliationStatus", "qualityInspectionStatus", 
            "qualityInspection", "detectionQuantity", "remark","发货日期","logisticsCode","attachments","已出库","是否发货"
        ]
        
        # 构建查询条件
        final_condition = {}
        if condition:
            final_condition.update(condition)
        
        if sales_order_product_ids:
            final_condition["salesOrderProductIds"] = sales_order_product_ids
        
        result = self.get_sales_order_page_list(
            form_id=100039,  # 销售出库单的formId
            condition=final_condition,
            columns=columns,
            page=page,
            page_size=page_size,
            filters=filters or {},
            orderby=orderby
        )
        
        return result

    def get_logistics_companies(self, 
                               app_name: str = "SnowInventory-82886",
                               page: int = 0,
                               page_size: int = 1000) -> Dict[str, Any]:
        """
        获取物流公司列表（自动登录）
        
        Args:
            app_name: 应用名称，默认为 "SnowInventory-82886"
            page: 页码，默认为 0
            page_size: 每页大小，默认为 1000
        
        Returns:
            物流公司列表数据
        """
        # 确保已登录
        if not self._ensure_login():
            return {"error": "登录失败，无法执行查询"}
        
        payload = {
            "columns": ["name"],
            "condition": {},
            "page": page,
            "pageSize": page_size,
            "appName": app_name,
            "datasourceId": 100292,
            "isNonfilter": True,
            "formId": 100039,
            "filters": {},
            "orderby": "",
            "colId": 110673
        }
        
        request_headers = {
            'Content-Type': 'application/json',
            'Cookie': f'JSESSIONID={self.app_jsessionid}; sid={self.sid}'
        }
        
        url = "http://saas.snowbeasts.com/business/getDatasource"
        
        try:
            response = self.session.post(
                url,
                json=payload,
                headers=request_headers
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"查询物流公司请求失败: {e}")
            return {"error": str(e)}
        except json.JSONDecodeError as e:
            print(f"响应解析失败: {e}")
            return {"error": "响应格式错误"}

    def get_delivery_order_detail(self, delivery_order_id: str, app_name: str = "SnowInventory-82886") -> Dict[str, Any]:
        """
        获取出库单详情（自动登录）

        Args:
            delivery_order_id: 出库单ID
            app_name: 应用名称，默认为 "SnowInventory-82886"

        Returns:
            出库单详情数据
        """
        # 确保已登录
        if not self._ensure_login():
            return {"error": "登录失败，无法执行查询"}

        payload = {
            "appName": app_name,
            "formId": 100039,  # 出库单的formId
            "condition": {"salesOrderProductIds": None},
            "id": delivery_order_id
        }

        request_headers = {
            'Content-Type': 'application/json',
            'Cookie': f'JSESSIONID={self.app_jsessionid}; sid={self.sid}'
        }

        url = "http://saas.snowbeasts.com/business/getBusiness"

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=request_headers
            )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"获取出库单详情请求失败: {e}")
            return {"error": str(e)}
        except json.JSONDecodeError as e:
            print(f"响应解析失败: {e}")
            return {"error": "响应格式错误"}

    def get_delivery_order_products(self, delivery_order_id: str, sales_order_ids: list = None, 
                                   customer_or_supplier_id: str = "", sales_order_id: str = "",
                                   app_name: str = "SnowInventory-82886") -> Dict[str, Any]:
        """
        获取出库单关联的产品信息（自动登录）
        
        Args:
            delivery_order_id: 出库单ID（作为parent.id）
            sales_order_ids: 销售订单ID列表，默认为None
            customer_or_supplier_id: 客户或供应商ID，默认为空
            sales_order_id: 销售订单ID，默认为空
            app_name: 应用名称，默认为 "SnowInventory-82886"
        
        Returns:
            出库单产品信息数据
        """
        # 确保已登录
        if not self._ensure_login():
            return {"error": "登录失败，无法执行查询"}
        
        # 构建查询条件
        condition = {
            "parent.id": delivery_order_id,
            "exchangeRate": 1,
            "category": 1,
            "salesOrderId": sales_order_id
        }
        
        # 添加可选参数
        if sales_order_ids:
            condition["salesOrderIds"] = sales_order_ids
        if customer_or_supplier_id:
            condition["customerOrSupplierId"] = customer_or_supplier_id
        
        payload = {
            "appName": app_name,
            "formId": 100041,  # 出库单产品的formId
            "condition": condition,
            "page": 0,
            "pageSize": 5000,
            "orderby": "",
            "isColumnForm": True
        }
        
        request_headers = {
            'Content-Type': 'application/json',
            'Cookie': f'JSESSIONID={self.app_jsessionid}; sid={self.sid}'
        }
        
        url = "http://saas.snowbeasts.com/business/getBusinessPageList"
        
        try:
            response = self.session.post(
                url,
                json=payload,
                headers=request_headers
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"获取出库单产品信息请求失败: {e}")
            return {"error": str(e)}
        except json.JSONDecodeError as e:
            print(f"响应解析失败: {e}")
            return {"error": "响应格式错误"}
