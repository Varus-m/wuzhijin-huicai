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
            
            if (current_time - self._last_login_time) > self._login_interval and self._is_logged_in:
                print("登录已超时（5分钟），正在重新登录...")
            else:
                print("检测到未登录，正在自动登录...")
            
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
        
        Args:
            account: 账号，默认为 "15068471011"
            password: 密码，默认为 "2a1b583f9a8d20004379fe836a76c5f0d84c7ef9"
        
        Returns:
            登录响应结果
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
            
            print(f"登录成功！JSESSIONID: {self.jsessionid}, SID: {self.sid}")
            
            # 新增：获取app的jsessionid
            app_result = self._get_app_jsessionid()
            if app_result.get('success', False):
                print(f"获取app jsessionid成功: {self.app_jsessionid}")
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
    
    def update_customer_wechat_invite_code(self, customer_id: str, invite_code: str, 
                                         app_name: str = "SnowInventory-82886") -> Dict[str, Any]:
        """
        更新客户的微信邀请码（自动登录）
        
        Args:
            customer_id: 客户ID
            invite_code: 微信邀请码
            app_name: 应用名称，默认为 "SnowInventory-82886"
        
        Returns:
            更新结果
        """
        # 确保已登录
        if not self._ensure_login():
            return {"error": "登录失败，无法执行更新"}
        
        payload = {
            "appName": app_name,
            "formId": 100004,  # 客户表单ID
            "condition": {},
            "action": 2,  # 更新操作
            "id": customer_id,
            "data": {
                "微信邀请码": invite_code
            }
        }
        
        request_headers = {
            'Content-Type': 'application/json',
            'Cookie': f'JSESSIONID={self.app_jsessionid}; sid={self.sid}'
        }
        
        url = "http://saas.snowbeasts.com/business/updateBusiness"
        
        try:
            response = self.session.post(
                url,
                json=payload,
                headers=request_headers
            )
            
            response.raise_for_status()
            response_data = response.json()
            
            print(f"更新客户 {customer_id} 的微信邀请码为: {invite_code}")
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            print(f"更新微信邀请码请求失败: {e}")
            return {"error": str(e)}
        except json.JSONDecodeError as e:
            print(f"响应解析失败: {e}")
            return {"error": "响应格式错误"}
    
    def _get_app_jsessionid(self) -> Dict[str, Any]:
        """
        使用sid获取app的jsessionid
        
        Returns:
            获取结果
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
                print(f"重定向后的最终URL: {response.url}")
                return {"success": True, "app_jsessionid": self.app_jsessionid, "final_url": response.url}
            else:
                # 如果没有在cookies中找到JSESSIONID，检查所有历史响应
                for hist_response in response.history:
                    hist_cookies = hist_response.cookies
                    if 'JSESSIONID' in hist_cookies:
                        self.app_jsessionid = hist_cookies['JSESSIONID']
                        self._update_session_headers()
                        print(f"从重定向历史中获取到JSESSIONID: {self.app_jsessionid}")
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
    
    def get_headers(self) -> Dict[str, str]:
        """
        获取包含认证信息的请求头
        
        Returns:
            包含Cookie的请求头字典
        """
        return self.headers.copy()
    
    def make_authenticated_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        发起已认证的请求
        
        Args:
            method: HTTP方法 (GET, POST, PUT, DELETE等)
            endpoint: API端点 (相对于base_url)
            **kwargs: 其他requests参数
        
        Returns:
            响应对象
        """
        if not self.jsessionid or not self.sid:
            raise Exception("请先登录获取认证信息")
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # 确保使用最新的认证头部
        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        kwargs['headers'].update(self.get_headers())
        
        return self.session.request(method, url, **kwargs)
    
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """发起GET请求"""
        return self.make_authenticated_request('GET', endpoint, **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """发起POST请求"""
        return self.make_authenticated_request('POST', endpoint, **kwargs)
    
    def put(self, endpoint: str, **kwargs) -> requests.Response:
        """发起PUT请求"""
        return self.make_authenticated_request('PUT', endpoint, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """发起DELETE请求"""
        return self.make_authenticated_request('DELETE', endpoint, **kwargs)
    
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
            columns = [
                "opportunityId", "id", "produced", "produceQuantity", "outsourcingQuantity", 
                "quantity", "code", "customerOrderCode", "date", "customerId", "countryId", 
                "province", "city", "county", "customerCategory", "projectId", "deliveryDate", 
                "collectionDate", "paymentMethod", "currency", "exchangeRate", "noTaxAmount", 
                "amount", "deductionAmount", "grossProfit", "taxGrossProfit", "profit", 
                "taxProfit", "rmbAmount", "shippedRate", "shippingRate", "stockOutRate", 
                "receivedRate", "receivingRate", "invoicedRate", "invoicingRate", "producedRate", 
                "producingRate", "produceAmount", "returnedRate", "refundRate", "shipped", 
                "returnRate", "requisitionedRate", "requisitioningRate", "quotationId", "vat", 
                "stockOutAmount", "companyId", "accountId", "userId", "departmentId", 
                "shippedAmount", "ownerId", "shareUserIds", "unInvoicedAmount", "returnedAmount", 
                "refundAmount", "status", "advanceAmount", "purchasingOrderIds", "remark", 
                "contact", "tel", "mobile", "address", "customerName", "customerTax", 
                "invoiceContact", "bankAndAccount", "invoiceType", "invoiceShipment", 
                "financeContact", "financeTel", "financeMobile", "invoiceAddress", 
                "shipmentContact", "shipmentTel", "shipmentMobile", "shipmentAddress", 
                "requirement", "termSubjectId"
            ]
        
        if filters is None:
            filters = {"status": [1, 2, 4, 5]}
        
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
            response_data = response.json()
            
            if "data" in response_data:
                data = response_data["data"]
                count = data.get("_count", 0)
                sum_info = data.get("_sum", {})
                data_list = data.get("_dataList", [])
                
                print(f"查询成功！")
                print(f"总记录数: {count}")
                print(f"本页记录数: {len(data_list)}")
                # if sum_info:
                #     print(f"汇总信息:")
                #     for key, value in sum_info.items():
                #         print(f"  - {key}: {value}")
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            print(f"查询请求失败: {e}")
            return {"error": str(e)}
        except json.JSONDecodeError as e:
            print(f"响应解析失败: {e}")
            return {"error": "响应格式错误"}
    
    def get_sales_order_lines(self, 
                             sales_order_id: str,
                             app_name: str = "SnowInventory-82886",
                             page: int = 0,
                             page_size: int = 20,
                             orderby: str = "") -> Dict[str, Any]:
        """
        获取销售订单行数据（自动登录）
        """
        # 确保已登录
        if not self._ensure_login():
            return {"error": "登录失败，无法执行查询"}
        
        columns = [
            "image", "productCode", "warehouseId", "productId", "productName", 
            "productCategory", "productCategory1", "field", "brand", "spec", 
            "weight", "weightAmount", "weightUnitId", "skuProp", "skuCode", 
            "skuData", "stockQuantity", "availableQuantity", "quantity", 
            "salesOrderId", "salesOrderCode", "shippedQuantity", "shippingQuantity", 
            "returnedQuantity", "returningQuantity", "refundedQuantity", 
            "refundingQuantity", "requisitionedQuantity", "unRequisitionedQuantity", 
            "producingQuantity", "producedQuantity", "unProducedQuantity", 
            "defaultUnitId", "customerId", "date", "unitRatio", "userId", 
            "ownerId", "shareUserIds", "status", "vat", "priceMethod", 
            "currency", "exchangeRate", "cost", "noTaxPrice", "price", 
            "discount", "discountPrice", "rmbPrice", "taxRate", "noTaxAmount", 
            "amount", "grossProfit", "rmbAmount", "unitId", "produceType", 
            "deliveryDate", "stockOutDate", "remark", "companyId", "projectId", 
            "supplierId", "purchasingOrderId"
        ]
        
        return self.get_sales_order_page_list(
            form_id=100185,
            condition={"form.id": sales_order_id},
            columns=columns,
            page=page,
            page_size=page_size,
            filters={}
        )
    
    def get_sales_delivery_orders(self, 
                                 sales_order_product_ids: list = None,
                                 page: int = 0,
                                 page_size: int = 20,
                                 orderby: str = "",
                                 filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        获取销售出库单数据（自动登录）
        
        Args:
            sales_order_product_ids: 销售订单产品ID列表，为None时查询所有
            page: 页码，默认为 0
            page_size: 每页大小，默认为 20
            orderby: 排序字段
        
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
        condition = {
            "salesOrderProductIds": sales_order_product_ids
        }
        
        result = self.get_sales_order_page_list(
            form_id=100039,  # 销售出库单的formId
            condition=condition,
            columns=columns,
            page=page,
            page_size=page_size,
            filters=filters or {},
            orderby=orderby
        )
        
        # 增强的数据展示
        if "data" in result and "error" not in result:
            data = result["data"]
            count = data.get("_count", 0)
            sum_info = data.get("_sum", {})
            data_list = data.get("_dataList", [])
            
            #print(f"\n=== 销售出库单查询结果 ===")
            #print(f"总记录数: {count}")
            #print(f"本页记录数: {len(data_list)}")
            
            # if sum_info:
            #     print(f"汇总信息:")
            #     print(f"  - 总金额: {sum_info.get('amount', 0):.2f}")
            #     print(f"  - 已开票金额: {sum_info.get('invoicedAmount', 0):.2f}")
            #     print(f"  - 应收金额: {sum_info.get('receivableAmount', 0):.2f}")
            #     print(f"  - 已收金额: {sum_info.get('receivedAmount', 0):.2f}")
            #     print(f"  - 未开票金额: {sum_info.get('unInvoicedAmount', 0):.2f}")
            #
            # # 显示出库单详情
            # if data_list:
            #     print(f"\n出库单详情:")
            #     for i, delivery in enumerate(data_list[:3], 1):  # 只显示前3条
            #         print(f"  第{i}单:")
            #         print(f"    - 出库单号: {delivery.get('code', 'N/A')}")
            #         print(f"    - 关联订单: {delivery.get('orderCodes', 'N/A')}")
            #         print(f"    - 客户/供应商ID: {delivery.get('customerOrSupplierId', 'N/A')}")
            #         print(f"    - 金额: {delivery.get('amount', 0)}")
            #         print(f"    - 联系人: {delivery.get('contact', 'N/A')}")
            #         print(f"    - 电话: {delivery.get('mobile', 'N/A')}")
            #         print(f"    - 是否完成: {'是' if delivery.get('finished') else '否'}")
            #         print(f"    - 对账状态: {delivery.get('reconciliationStatus', 'N/A')}")
            #         if delivery.get('remark'):
            #             print(f"    - 备注: {delivery.get('remark')}")
            #         print()
            #
            #     if len(data_list) > 3:
            #         print(f"    ... 还有 {len(data_list) - 3} 条记录")
        
        return result
    
    def get_customer_list(self, 
                         app_name: str = "SnowInventory-82886",
                         condition: Dict[str, Any] = None,
                         page: int = 0,
                         page_size: int = 100,
                         filters: Dict[str, Any] = None,
                         orderby: str = "") -> Dict[str, Any]:
        """
        获取客户列表（自动登录）
        
        Args:
            app_name: 应用名称，默认为 "SnowInventory-82886"
            condition: 查询条件，默认为空字典
            page: 页码，默认为 0
            page_size: 每页大小，默认为 100
            filters: 过滤条件，默认为空字典
            orderby: 排序字段，默认为空字符串
        
        Returns:
            客户列表数据
        """
        # 确保已登录
        if not self._ensure_login():
            return {"error": "登录失败，无法执行查询"}
        
        if condition is None:
            condition = {}
        
        if filters is None:
            filters = {}
        
        # 客户列表的字段
        columns = [
            "customerType", "type", "code", "abbr", "name", "countryId", 
            "province", "city", "county", "category", "currency", "level", 
            "industry", "ownerId", "shareUserIds", "disable", "微信邀请码"
        ]
        
        result = self.get_sales_order_page_list(
            app_name=app_name,
            form_id=100004,  # 客户列表的formId
            condition=condition,
            columns=columns,
            page=page,
            page_size=page_size,
            filters=filters,
            orderby=orderby
        )
        
        # 增强的数据展示
        if "data" in result and "error" not in result:
            data = result["data"]
            count = data.get("_count", 0)
            data_list = data.get("_dataList", [])
            
            print(f"\n=== 客户列表查询结果 ===")
            print(f"总记录数: {count}")
            print(f"本页记录数: {len(data_list)}")
            
            # 显示客户详情（前5条）
            if data_list:
                print(f"\n客户详情:")
                for i, customer in enumerate(data_list[:5], 1):
                    print(f"  第{i}个客户:")
                    print(f"    - 客户编号: {customer.get('code', 'N/A')}")
                    print(f"    - 客户名称: {customer.get('name', 'N/A')}")
                    print(f"    - 客户简称: {customer.get('abbr', 'N/A')}")
                    print(f"    - 客户类型: {customer.get('customerType', 'N/A')}")
                    print(f"    - 省份: {customer.get('province', 'N/A')}")
                    print(f"    - 城市: {customer.get('city', 'N/A')}")
                    print(f"    - 区县: {customer.get('county', 'N/A')}")
                    print(f"    - 货币: {customer.get('currency', 'N/A')}")
                    print(f"    - 是否禁用: {'是' if customer.get('disable') else '否'}")
                    print(f"    - 所有者ID: {customer.get('ownerId', 'N/A')}")
                    if customer.get('category'):
                        print(f"    - 分类: {customer.get('category')}")
                    if customer.get('level'):
                        print(f"    - 级别: {customer.get('level')}")
                    if customer.get('industry'):
                        print(f"    - 行业: {customer.get('industry')}")
                    if customer.get('微信邀请码'):
                        print(f"    - 微信邀请码: {customer.get('微信邀请码')}")
                    print()
                
                if len(data_list) > 5:
                    print(f"    ... 还有 {len(data_list) - 5} 条记录")
        
        return result
    
    def get_order_with_lines(self, sales_order_id: str) -> Dict[str, Any]:
        """
        获取销售订单及其订单行的完整信息（自动登录）
        
        Args:
            sales_order_id: 销售订单ID
        
        Returns:
            包含订单头和订单行的完整信息
        """
        # 确保已登录
        if not self._ensure_login():
            return {"error": "登录失败，无法执行查询"}
        
        result = {
            "order_header": None,
            "order_lines": None,
            "error": None
        }
        
        try:
            # 首先获取订单头信息（通过ID过滤）
            order_filter = {"id": [sales_order_id]}
            header_result = self.get_sales_order_page_list(filters=order_filter, page_size=1)
            
            if "error" in header_result:
                result["error"] = f"获取订单头失败: {header_result['error']}"
                return result
            
            if "data" in header_result and header_result["data"].get("_dataList"):
                result["order_header"] = header_result["data"]["_dataList"][0]
            
            # 然后获取订单行信息
            lines_result = self.get_sales_order_lines(sales_order_id)
            
            if "error" in lines_result:
                result["error"] = f"获取订单行失败: {lines_result['error']}"
                return result
            
            result["order_lines"] = lines_result
            
            print(f"\n=== 订单完整信息 ===")
            if result["order_header"]:
                header = result["order_header"]
                print(f"订单号: {header.get('code', 'N/A')}")
                print(f"客户: {header.get('customerName', 'N/A')}")
                print(f"订单金额: {header.get('amount', 0)}")
                print(f"订单状态: {header.get('status', 'N/A')}")
            
            if result["order_lines"] and "data" in result["order_lines"]:
                lines_data = result["order_lines"]["data"]
                print(f"订单行数量: {lines_data.get('_count', 0)}")
            
            return result
            
        except Exception as e:
            result["error"] = f"获取订单完整信息失败: {str(e)}"
            return {"error": "响应格式错误"}

    def get_sales_order_products(self, sales_order_id: str, app_name: str = "SnowInventory-82886") -> Dict[str, Any]:
        """
        获取销售订单关联的产品信息（自动登录）
        
        Args:
            sales_order_id: 销售订单ID（作为form.id）
            app_name: 应用名称，默认为 "SnowInventory-82886"
        
        Returns:
            销售订单产品信息数据
        """
        # 确保已登录
        if not self._ensure_login():
            return {"error": "登录失败，无法执行查询"}
        
        # 构建查询条件
        condition = {
            "form.id": sales_order_id
        }
        
        # 完整的字段列表
        columns = [
            "image", "productCode", "warehouseId", "productId", "productName", 
            "productCategory", "productCategory1", "field", "brand", "spec", 
            "weight", "weightAmount", "weightUnitId", "skuProp", "skuCode", 
            "skuData", "stockQuantity", "availableQuantity", "quantity", 
            "salesOrderId", "salesOrderCode", "shippedQuantity", "shippingQuantity", 
            "returnedQuantity", "returningQuantity", "refundedQuantity", 
            "refundingQuantity", "requisitionedQuantity", "unRequisitionedQuantity", 
            "producingQuantity", "producedQuantity", "unProducedQuantity", 
            "defaultUnitId", "customerId", "date", "unitRatio", "userId", 
            "ownerId", "shareUserIds", "status", "vat", "priceMethod", 
            "currency", "exchangeRate", "cost", "noTaxPrice", "price", 
            "discount", "discountPrice", "rmbPrice", "taxRate", "noTaxAmount", 
            "amount", "grossProfit", "rmbAmount", "unitId", "produceType", 
            "deliveryDate", "stockOutDate", "remark", "companyId", "projectId", 
            "supplierId", "purchasingOrderId"
        ]
        
        payload = {
            "appName": app_name,
            "formId": 100185,  # 销售订单产品的formId
            "condition": condition,
            "columns": columns,
            "page": 0,
            "pageSize": 20,
            "filters": {},
            "orderby": ""
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
            response_data = response.json()
            
            if response_data.get("success") and "data" in response_data:
                data = response_data["data"]
                
                print(f"\n=== 销售订单产品信息 ===")
                print(f"销售订单ID: {sales_order_id}")
                print(f"产品总数: {data.get('_count', 0)}")
                
                # 显示汇总信息
                if "_sum" in data:
                    sum_data = data["_sum"]
                    print(f"\n--- 汇总信息 ---")
                    print(f"总数量: {sum_data.get('quantity', 0)}")
                    print(f"总金额: {sum_data.get('amount', 0)}")
                    print(f"人民币总金额: {sum_data.get('rmbAmount', 0)}")
                    print(f"未税总金额: {sum_data.get('noTaxAmount', 0)}")
                    print(f"已发货数量: {sum_data.get('shippedQuantity', 0)}")
                    print(f"发货中数量: {sum_data.get('shippingQuantity', 0)}")
                    print(f"已退货数量: {sum_data.get('returnedQuantity', 0)}")
                    print(f"退货中数量: {sum_data.get('returningQuantity', 0)}")
                    print(f"重量总金额: {sum_data.get('weightAmount', 0)}")
                
                # 显示产品列表
                if "_dataList" in data and data["_dataList"]:
                    print(f"\n--- 产品明细 ---")
                    for i, product in enumerate(data["_dataList"], 1):
                        print(f"\n产品 {i}:")
                        print(f"  产品名称: {product.get('productName', 'N/A')}")
                        print(f"  产品编码: {product.get('productCode', 'N/A')}")
                        print(f"  规格型号: {product.get('spec', 'N/A')}")
                        print(f"  品牌: {product.get('brand', 'N/A')}")
                        print(f"  数量: {product.get('quantity', 0)}")
                        print(f"  单价: {product.get('price', 0)}")
                        print(f"  金额: {product.get('amount', 0)}")
                        print(f"  成本: {product.get('cost', 0)}")
                        print(f"  毛利润: {product.get('grossProfit', 0)}")
                        print(f"  已发货数量: {product.get('shippedQuantity', 0)}")
                        print(f"  发货中数量: {product.get('shippingQuantity', 0)}")
                        print(f"  已退货数量: {product.get('returnedQuantity', 0)}")
                        print(f"  退货中数量: {product.get('returningQuantity', 0)}")
                        print(f"  销售订单编码: {product.get('salesOrderCode', 'N/A')}")
                        print(f"  状态: {product.get('status', 'N/A')}")
                        print(f"  交货日期: {product.get('deliveryDate', 'N/A')}")
                        print(f"  出库日期: {product.get('stockOutDate', 'N/A')}")
                        if product.get('remark'):
                            print(f"  备注: {product.get('remark')}")
                
                print(f"\n销售订单产品信息获取成功！")
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            print(f"获取销售订单产品信息请求失败: {e}")
            return {"error": str(e)}
        except json.JSONDecodeError as e:
            print(f"响应解析失败: {e}")
            return {"error": "响应格式错误"}

    def get_delivery_order_detail(self, delivery_order_id: str, app_name: str = "SnowInventory-82886") -> Dict[
        str, Any]:
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
            response_data = response.json()

            if response_data.get("success") and "data" in response_data:
                data = response_data["data"]

                print(f"\n=== 出库单详情 ===")
                print(f"出库单号: {data.get('code', 'N/A')}")
                print(f"关联订单: {data.get('orderCodes', 'N/A')}")
                print(f"销售订单号: {data.get('salesOrderCode', 'N/A')}")
                print(f"客户/供应商ID: {data.get('customerOrSupplierId', 'N/A')}")
                print(f"联系人: {data.get('contact', 'N/A')}")
                print(f"电话: {data.get('mobile', 'N/A')}")
                print(f"地址: {data.get('address', 'N/A')}")
                print(f"出库数量: {data.get('quantity', 0)}")
                print(f"出库金额: {data.get('amount', 0)}")
                print(f"人民币金额: {data.get('rmbAmount', 0)}")
                print(f"毛利润: {data.get('grossProfit', 0)}")
                print(f"毛利率: {data.get('grossProfitRate', 0):.2%}")
                print(f"是否完成: {'是' if data.get('finished') else '否'}")
                print(f"对账状态: {data.get('reconciliationStatus', 'N/A')}")
                print(f"质检状态: {data.get('qualityInspectionStatus', 'N/A')}")
                print(f"已开票金额: {data.get('invoicedAmount', 0)}")
                print(f"未开票金额: {data.get('unInvoicedAmount', 0)}")
                print(f"应收金额: {data.get('receivableAmount', 0)}")
                print(f"已收金额: {data.get('receivedAmount', 0)}")
                if data.get('remark'):
                    print(f"备注: {data.get('remark')}")

                print(f"\n详情获取成功！")

            return response_data

        except requests.exceptions.RequestException as e:
            print(f"获取出库单详情请求失败: {e}")
            return {"error": str(e)}
        except json.JSONDecodeError as e:
            print(f"响应解析失败: {e}")
            return {"error": "响应格式错误"}
    
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
            response_data = response.json()
            
            if "data" in response_data and response_data.get("success", False):
                data = response_data["data"]
                count = data.get("_count", 0)
                data_list = data.get("_dataList", [])
                
                print(f"\n=== 物流公司查询结果 ===")
                print(f"总记录数: {count}")
                print(f"本页记录数: {len(data_list)}")
                
                # 显示物流公司列表
                if data_list:
                    print(f"\n物流公司列表:")
                    for i, company in enumerate(data_list[:10], 1):  # 只显示前10条
                        print(f"  {i}. {company.get('name', 'N/A')} (ID: {company.get('id', 'N/A')})")
                    
                    if len(data_list) > 10:
                        print(f"    ... 还有 {len(data_list) - 10} 家物流公司")
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            print(f"查询物流公司请求失败: {e}")
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
            response_data = response.json()
            
            if response_data.get("success") and "data" in response_data:
                data = response_data["data"]
                
                print(f"\n=== 出库单产品信息 ===")
                print(f"出库单ID: {delivery_order_id}")
                print(f"产品总数: {data.get('_count', 0)}")
                
                # 显示汇总信息
                if "_sum" in data:
                    sum_data = data["_sum"]
                    print(f"\n--- 汇总信息 ---")
                    print(f"总数量: {sum_data.get('quantity', 0)}")
                    print(f"总金额: {sum_data.get('amount', 0)}")
                    print(f"人民币总金额: {sum_data.get('rmbAmount', 0)}")
                    print(f"未税总金额: {sum_data.get('noTaxAmount', 0)}")
                    print(f"重量总金额: {sum_data.get('weightAmount', 0)}")
                
                # 显示产品列表
                if "_dataList" in data and data["_dataList"]:
                    print(f"\n--- 产品明细 ---")
                    for i, product in enumerate(data["_dataList"], 1):
                        print(f"\n产品 {i}:")
                        print(f"  产品名称: {product.get('productName', 'N/A')}")
                        print(f"  产品编码: {product.get('productCode', 'N/A')}")
                        print(f"  规格型号: {product.get('spec', 'N/A')}")
                        print(f"  品牌: {product.get('brand', 'N/A')}")
                        print(f"  数量: {product.get('quantity', 0)}")
                        print(f"  单价: {product.get('price', 0)}")
                        print(f"  金额: {product.get('amount', 0)}")
                        print(f"  成本: {product.get('cost', 0)}")
                        print(f"  毛利润: {product.get('grossProfit', 0)}")
                        print(f"  毛利率: {product.get('grossProfitRate', 0):.2%}")
                        print(f"  库存编码: {product.get('stockCode', 'N/A')}")
                        print(f"  批次: {product.get('batch', 'N/A')}")
                        print(f"  是否完成: {'是' if product.get('finished') else '否'}")
                        if product.get('remark'):
                            print(f"  备注: {product.get('remark')}")
                
                print(f"\n出库单产品信息获取成功！")
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            print(f"获取出库单产品信息请求失败: {e}")
            return {"error": str(e)}
        except json.JSONDecodeError as e:
            print(f"响应解析失败: {e}")
            return {"error": "响应格式错误"}


api = SnowbeastsAPI()
api.login()
api.get_sales_order_lines
