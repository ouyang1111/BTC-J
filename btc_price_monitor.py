#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
币安BT价格监控程序
监控BT价格变化，当涨跌超过500美元时发送提醒
用于信息提醒，不做任何交易决策
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

# ==================== 配置区域 ====================
# 企业微信机器人 Webhook URL
# 获取方式：在企业微信群中添加机器人，获取 Webhook URL
WECHAT_WEBHOOK_URL = os.getenv('WECHAT_WEBHOOK_URL', '')

# 检查间隔（秒）- 建议设置为30-60秒
CHECK_INTERVAL_SECONDS = 30

# 价格变化提醒阈值（美元）
PRICE_CHANGE_THRESHOLD = 500  # 涨跌超过此金额时提醒（美元）

# 今日最大涨跌阈值（美元）
DAILY_MAX_CHANGE_THRESHOLD = 2000

# ==================== API 配置 ====================
BINANCE_API_URL = 'https://api.binance.com/api/v3/ticker/price'
BINANCE_24H_STATS_URL = 'https://api.binance.com/api/v3/ticker/24hr'

# ==================== 状态文件路径 ====================
STATE_FILE = 'btc_price_state.json'


def get_beijing_time() -> str:
    """获取北京时间（UTC+8）"""
    beijing_tz = timezone(timedelta(hours=8))
    beijing_time = datetime.now(beijing_tz)
    return beijing_time.strftime('%Y-%m-%d %H:%M:%S')


def get_beijing_datetime() -> datetime:
    """获取北京时间的datetime对象"""
    beijing_tz = timezone(timedelta(hours=8))
    return datetime.now(beijing_tz)


def get_btc_price() -> Optional[float]:
    """
    从币安API获取BTC当前价格
    
    Returns:
        BTC价格（美元），如果失败返回 None
    """
    try:
        params = {'symbol': 'BTCUSDT'}
        response = requests.get(BINANCE_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return float(data.get('price', 0))
    except Exception as e:
        print(f"获取BT价格失败: {e}")
        return None


def get_btc_24h_stats() -> Optional[Dict]:
    """
    从币安API获取BTC 24小时统计数据
    
    Returns:
        包含24小时统计数据的字典，如果失败返回 None
    """
    try:
        params = {'symbol': 'BTCUSDT'}
        response = requests.get(BINANCE_24H_STATS_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {
            'priceChange': float(data.get('priceChange', 0)),  # 24小时价格变化（美元）
            'priceChangePercent': float(data.get('priceChangePercent', 0)),  # 24小时价格变化百分比
            'highPrice': float(data.get('highPrice', 0)),  # 24小时最高价
            'lowPrice': float(data.get('lowPrice', 0)),  # 24小时最低价
            'lastPrice': float(data.get('lastPrice', 0)),  # 最新价格
        }
    except Exception as e:
        print(f"获取BT 24小时统计数据失败: {e}")
        return None


def send_wechat_message(message: str) -> bool:
    """
    通过企业微信机器人发送消息
    
    Args:
        message: 要发送的消息内容（Markdown格式）
    
    Returns:
        发送成功返回 True，失败返回 False
    """
    if not WECHAT_WEBHOOK_URL or WECHAT_WEBHOOK_URL == '':
        return False
    
    try:
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
            return True
        else:
            print(f"企业微信返回错误: {result.get('errmsg', '未知错误')}")
            return False
    except Exception as e:
        print(f"发送企业微信消息失败: {e}")
        return False


def load_state() -> Dict:
    """从文件加载上次检查的状态"""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"加载状态文件失败: {e}")
    
    # 返回默认状态
    return {
        'last_price': None,
        'last_check_date': None,
        'today_high': None,
        'today_low': None,
        'today_high_time': None,
        'today_low_time': None,
        'last_alert_price': None,  # 上次提醒时的价格
        'daily_max_change_events': []  # 今日超过2000美元涨跌的事件记录
    }


def save_state(state: Dict):
    """保存当前状态到文件"""
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存状态文件失败: {e}")


def format_price_message(current_price: float, price_change: float, price_change_percent: float,
                        today_high: Optional[float] = None, today_low: Optional[float] = None,
                        today_high_time: Optional[str] = None, today_low_time: Optional[str] = None,
                        daily_max_change_events: Optional[list] = None) -> str:
    """
    格式化价格提醒消息（企业微信 Markdown 格式）
    
    Args:
        current_price: 当前价格
        price_change: 价格变化（美元）
        price_change_percent: 价格变化百分比
        today_high: 今日最高价
        today_low: 今日最低价
        today_high_time: 今日最高价出现时间
        today_low_time: 今日最低价出现时间
        daily_max_change_events: 今日超过2000美元涨跌的事件列表
    
    Returns:
        格式化后的消息（Markdown格式）
    """
    beijing_time = get_beijing_time()
    
    # 判断涨跌
    if price_change > 0:
        change_symbol = "📈"
        change_text = "上涨"
    elif price_change < 0:
        change_symbol = "📉"
        change_text = "下跌"
    else:
        change_symbol = "➡️"
        change_text = "持平"
    
    message = f"""# {change_symbol} BT价格提醒

**🕐 更新时间（北京时间）:** {beijing_time}

## 💰 当前价格
**${current_price:,.2f}**

## 📊 价格变化
**{change_text} ${abs(price_change):,.2f} ({price_change_percent:+.2f}%)**"""
    
    # 添加今日最高最低价
    if today_high is not None and today_low is not None:
        message += f"""

## 📈 今日价格区间
• **最高价:** ${today_high:,.2f}"""
        if today_high_time:
            message += f" ({today_high_time})"
        message += f"""
• **最低价:** ${today_low:,.2f}"""
        if today_low_time:
            message += f" ({today_low_time})"
        
        # 计算今日最大涨跌
        daily_max_change = today_high - today_low
        if daily_max_change >= DAILY_MAX_CHANGE_THRESHOLD:
            message += f"""
• **今日最大涨跌:** ${daily_max_change:,.2f} (超过${DAILY_MAX_CHANGE_THRESHOLD:,.2f}阈值)"""
    
    # 添加超过2000美元涨跌的事件记录
    if daily_max_change_events and len(daily_max_change_events) > 0:
        message += """

## ⚠️ 今日超过2000美元涨跌记录"""
        for event in daily_max_change_events:
            event_type = event.get('type', '未知')
            event_price = event.get('price', 0)
            event_time = event.get('time', '')
            event_change = event.get('change', 0)
            message += f"""
• **{event_type}** ${event_price:,.2f} (涨跌${abs(event_change):,.2f}) - {event_time}"""
    
    message += "\n\n⚠️ *本程序仅用于信息提醒，不做任何交易决策*"
    
    return message


def check_price_change_and_alert():
    """检查价格变化并发送提醒"""
    # 加载状态
    state = load_state()
    last_price = state.get('last_price')
    last_check_date = state.get('last_check_date')
    today_high = state.get('today_high')
    today_low = state.get('today_low')
    today_high_time = state.get('today_high_time')
    today_low_time = state.get('today_low_time')
    last_alert_price = state.get('last_alert_price')
    daily_max_change_events = state.get('daily_max_change_events', [])
    
    # 获取当前日期（北京时间）
    beijing_now = get_beijing_datetime()
    current_date = beijing_now.strftime('%Y-%m-%d')
    current_time_str = beijing_now.strftime('%H:%M')
    
    # 如果是新的一天，重置今日数据
    is_new_day = (last_check_date != current_date)
    if is_new_day:
        print(f"[{get_beijing_time()}] 新的一天，重置今日数据")
        today_high = None
        today_low = None
        today_high_time = None
        today_low_time = None
        last_alert_price = None
        daily_max_change_events = []
    
    # 获取当前价格
    current_price = get_btc_price()
    if current_price is None:
        print(f"[{get_beijing_time()}] 获取价格失败，跳过本次检查")
        return
    
    print(f"[{get_beijing_time()}] 当前BT价格: ${current_price:,.2f}")
    
    # 更新今日最高最低价
    if today_high is None or current_price > today_high:
        today_high = current_price
        today_high_time = current_time_str
        print(f"  更新今日最高价: ${today_high:,.2f} ({today_high_time})")
    
    if today_low is None or current_price < today_low:
        today_low = current_price
        today_low_time = current_time_str
        print(f"  更新今日最低价: ${today_low:,.2f} ({today_low_time})")
    
    # 计算今日最大涨跌
    if today_high is not None and today_low is not None:
        daily_max_change = today_high - today_low
        if daily_max_change >= DAILY_MAX_CHANGE_THRESHOLD:
            # 检查是否已经记录过这个事件
            event_exists = False
            for event in daily_max_change_events:
                if (event.get('type') == '最高价' and event.get('price') == today_high) or \
                   (event.get('type') == '最低价' and event.get('price') == today_low):
                    event_exists = True
                    break
            
            # 如果当前价格是最高价或最低价，且超过阈值，记录事件
            if not event_exists:
                if current_price == today_high:
                    daily_max_change_events.append({
                        'type': '最高价',
                        'price': today_high,
                        'time': f"{current_date} {today_high_time}",
                        'change': daily_max_change
                    })
                    print(f"  记录超过${DAILY_MAX_CHANGE_THRESHOLD:,.2f}涨跌事件: 最高价 ${today_high:,.2f} ({current_date} {today_high_time})")
                elif current_price == today_low:
                    daily_max_change_events.append({
                        'type': '最低价',
                        'price': today_low,
                        'time': f"{current_date} {today_low_time}",
                        'change': daily_max_change
                    })
                    print(f"  记录超过${DAILY_MAX_CHANGE_THRESHOLD:,.2f}涨跌事件: 最低价 ${today_low:,.2f} ({current_date} {today_low_time})")
    
    # 计算价格变化（相对于上次提醒时的价格）
    should_alert = False
    price_change = 0
    price_change_percent = 0
    
    if last_alert_price is not None:
        price_change = current_price - last_alert_price
        price_change_percent = (price_change / last_alert_price) * 100
        abs_price_change = abs(price_change)
        
        # 检查是否超过提醒阈值（500美元）
        if abs_price_change >= PRICE_CHANGE_THRESHOLD:
            should_alert = True
            print(f"  价格变化超过提醒阈值: ${abs_price_change:,.2f} (阈值: ${PRICE_CHANGE_THRESHOLD:,.2f})")
    elif last_price is None:
        # 首次运行，不发送提醒，记录初始价格作为提醒基准
        print("  首次运行，记录初始价格")
        last_alert_price = current_price
    else:
        # 有上次价格但没有上次提醒价格（可能是新的一天），计算变化
        price_change = current_price - last_price
        price_change_percent = (price_change / last_price) * 100
        abs_price_change = abs(price_change)
        
        if abs_price_change >= PRICE_CHANGE_THRESHOLD:
            should_alert = True
            last_alert_price = last_price  # 使用上次价格作为基准
            print(f"  价格变化超过提醒阈值: ${abs_price_change:,.2f} (阈值: ${PRICE_CHANGE_THRESHOLD:,.2f})")
        else:
            # 如果不在提醒范围内，也设置提醒基准价格，避免下次误判
            if last_alert_price is None:
                last_alert_price = current_price
    
    # 如果需要发送提醒
    if should_alert:
        # 获取24小时统计数据用于显示
        stats_24h = get_btc_24h_stats()
        if stats_24h:
            price_change_percent = stats_24h.get('priceChangePercent', price_change_percent)
        
        # 格式化消息
        message = format_price_message(
            current_price=current_price,
            price_change=price_change,
            price_change_percent=price_change_percent,
            today_high=today_high,
            today_low=today_low,
            today_high_time=today_high_time,
            today_low_time=today_low_time,
            daily_max_change_events=daily_max_change_events
        )
        
        # 发送到企业微信
        success = send_wechat_message(message)
        if success:
            print(f"  ✅ 已发送价格提醒到企业微信")
            # 更新上次提醒价格
            last_alert_price = current_price
        else:
            print(f"  ❌ 发送价格提醒失败")
    else:
        if last_price is not None:
            price_change = current_price - last_price
            print(f"  价格变化: ${price_change:,.2f} (不在提醒范围内)")
    
    # 保存状态
    new_state = {
        'last_price': current_price,
        'last_check_date': current_date,
        'today_high': today_high,
        'today_low': today_low,
        'today_high_time': today_high_time,
        'today_low_time': today_low_time,
        'last_alert_price': last_alert_price,
        'daily_max_change_events': daily_max_change_events
    }
    save_state(new_state)


def main():
    """主程序"""
    print("=" * 60)
    print("BT价格监控程序")
    print("=" * 60)
    
    # 检查配置
    if not WECHAT_WEBHOOK_URL or WECHAT_WEBHOOK_URL == '':
        print("⚠️  警告: 未配置企业微信 Webhook URL")
        print("   程序将运行但不会发送消息")
        print("   请设置环境变量 WECHAT_WEBHOOK_URL 或在代码中配置")
        print()
    
    print(f"检查间隔: {CHECK_INTERVAL_SECONDS}秒")
    print(f"价格变化提醒阈值: 超过 ${PRICE_CHANGE_THRESHOLD:,.2f}")
    print(f"今日最大涨跌阈值: ${DAILY_MAX_CHANGE_THRESHOLD:,.2f}")
    print("=" * 60)
    print()
    
    # 检查是否在GitHub Actions中运行（单次运行模式）
    is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
    
    # 调试信息
    print(f"环境变量 GITHUB_ACTIONS: {os.getenv('GITHUB_ACTIONS')}")
    print(f"检测到GitHub Actions环境: {is_github_actions}")
    print()
    
    if is_github_actions:
        # GitHub Actions模式：只运行一次
        print("=" * 60)
        print("GitHub Actions模式：执行单次检查")
        print("=" * 60)
        try:
            check_price_change_and_alert()
            print("=" * 60)
            print("✅ 检查完成！程序退出")
            print("=" * 60)
        except Exception as e:
            print(f"\n❌ 程序运行出错: {e}")
            import traceback
            traceback.print_exc()
            raise
    else:
        # 本地运行模式：持续运行
        try:
            while True:
                check_price_change_and_alert()
                print(f"等待 {CHECK_INTERVAL_SECONDS} 秒后继续检查...\n")
                time.sleep(CHECK_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("\n程序已停止")
        except Exception as e:
            print(f"\n程序运行出错: {e}")
            raise


if __name__ == '__main__':
    main()
