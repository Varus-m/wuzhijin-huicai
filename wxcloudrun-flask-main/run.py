#!/usr/bin/env python3
"""
惠采订单信息查询系统 - Flask应用入口
"""

import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 将当前目录添加到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from wxcloudrun import create_app

def main():
    """主函数"""
    
    # 获取配置名称
    config_name = os.getenv('FLASK_CONFIG', 'development')
    
    # 创建应用
    app = create_app(config_name)
    
    # 获取主机和端口
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    
    # 运行应用
    app.run(
        host=host,
        port=port,
        debug=app.config.get('DEBUG', False),
        threaded=True
    )

if __name__ == '__main__':
    main()