#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本 - 验证币安API和企业微信连接
"""

import os
import requests
from datetime import datetime, timezone, timedelta

# 企业微信 Webhook URL
WECHAT_WEBHOOK_URL = os.getenv('WECHAT_WEBHOOK_URL', '')

def get_beijing_time():
    """获取北京时间"""
    beijing_tz = timezone(timedelta(hours=8))
    return datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')

def test_binance_api():
    """测试币安API连接"""
    print("=" * 60)
    print("测试币安API连接...")
    print("=" * 60)
    
    try:
        url = 'https://api.binance.com/api/v3/ticker/price'
        params = {'symbol': 'BTCUSDT'}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        price = float(data.get('price', 0))
        print(f"✅ 币安API连接成功")
        print(f"   当前BT价格: ${price:,.2f}")
        return True
    except Exception as e:
        print(f"❌ 币安API连接失败: {e}")
        return False

def test_wechat_webhook():
    """测试企业微信Webhook"""
    print("\n" + "=" * 60)
    print("测试企业微信Webhook...")
    print("=" * 60)
    
    if not WECHAT_WEBHOOK_URL or WECHAT_WEBHOOK_URL == '':
        print("❌ 未配置企业微信 Webhook URL")
        print("   请设置环境变量 WECHAT_WEBHOOK_URL")
        return False
    
    try:
        beijing_time = get_beijing_time()
        message = f"""# ✅ 连接测试成功

**测试时间（北京时间）:** {beijing_time}

这是一条测试消息，如果你看到这条消息，说明企业微信配置正确！

程序可以正常工作了。"""
        
        data = {
            'msgtype': 'markdown',
            'markdown': {
                'content': message
            }
        }
        
        response = requests.post(WECHAT_WEBHOOK_URL, json=data, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get('errcode') == 0:
            print("✅ 企业微信Webhook连接成功")
            print("   请检查企业微信群，应该能看到测试消息")
            return True
        else:
            print(f"❌ 企业微信返回错误: {result.get('errmsg', '未知错误')}")
            return False
    except Exception as e:
        print(f"❌ 企业微信Webhook连接失败: {e}")
        return False

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("BT价格监控程序 - 连接测试")
    print("=" * 60 + "\n")
    
    # 测试币安API
    binance_ok = test_binance_api()
    
    # 测试企业微信
    wechat_ok = test_wechat_webhook()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    print(f"币安API: {'✅ 正常' if binance_ok else '❌ 失败'}")
    print(f"企业微信: {'✅ 正常' if wechat_ok else '❌ 失败'}")
    
    if binance_ok and wechat_ok:
        print("\n🎉 所有测试通过！可以运行主程序了。")
        print("   运行命令: python btc_price_monitor.py")
    else:
        print("\n⚠️  请检查失败的配置项后再运行主程序。")
    print()

if __name__ == '__main__':
    main()

