import os
import json
import requests
import pandas as pd
from datetime import datetime

# --- 配置参数 ---
DATA_DIR = "data"                                      # 数据存储目录
LOG_DIR = "logs"                                       # 日志存储目录
STATE_FILE = os.path.join(DATA_DIR, "state.json")       # 存储核心状态（如历史最高点）的文件
HISTORY_FILE = os.path.join(DATA_DIR, "nasdaq_history.csv") # 存储每日抓取历史记录的文件
DANJUAN_API = "https://danjuanfunds.com/djapi/index_valuation/results" # 蛋卷基金估值接口
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def ensure_dirs():
    """
    确保必要的本地目录（data 和 logs）已创建。
    """
    for d in [DATA_DIR, LOG_DIR]:
        if not os.path.exists(d):
            os.makedirs(d)

def load_state():
    """
    从本地 JSON 文件加载策略执行状态。
    返回包含最高点、赎回状态、买回状态的字典。
    """
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    # 如果文件不存在，初始化默认状态
    return {
        "max_value": 0.0,           # 记录观察到的最高指数点位，用于计算回撤
        "is_sold_out": False,       # 标记当前是否处于“已赎回”状态（PE过高触发）
        "buy_back_triggered": False # 标记是否已经执行过“全额买回”操作（买回操作仅触发一次）
    }

def save_state(state):
    """
    将当前的策略状态持久化到本地 JSON 文件。
    """
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

def fetch_data():
    """
    多源获取纳指100数据：
    1. 从雪球抓取实时指数点位（用于精确计算回撤）。
    2. 从蛋卷抓取 PE 数据（如果 API 受限则使用硬编码的 fallback 值）。
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://xueqiu.com/"
    }
    
    # 默认数据模板（包含 Fallback PE）
    data = {
        "name": "纳斯达克100",
        "pe": 35.04,  # 默认使用 2026-05-24 的已知 PE 值作为兜底
        "value": 0.0,
        "date": datetime.now().strftime("%Y-%m-%d")
    }

    # 第一步：从雪球抓取最新价格
    try:
        session = requests.Session()
        # 访问首页以获取必要的 Cookie
        session.get("https://xueqiu.com/", headers=headers, timeout=5)
        # 抓取纳指100（.NDX）实时行情
        price_url = "https://xueqiu.com/service/v5/stock/batch/quote?symbol=.NDX"
        r = session.get(price_url, headers=headers, timeout=5)
        if r.status_code == 200:
            items = r.json().get('data', {}).get('items', [])
            if items:
                quote = items[0].get('quote', {})
                data['value'] = float(quote.get('current', 0))
                data['name'] = quote.get('name', data['name'])
    except Exception as e:
        print(f"警告: 从雪球获取价格失败: {e}")

    # 第二步：尝试从蛋卷获取最新 PE（蛋卷 API 经常有登录校验，可能失败）
    try:
        dj_url = "https://danjuanfunds.com/djapi/index_valuation/results?category=1"
        dj_headers = headers.copy()
        dj_headers["Referer"] = "https://danjuanfunds.com/rn/value-center"
        r = requests.get(dj_url, headers=dj_headers, timeout=5)
        if r.status_code == 200:
            dj_data = r.json()
            items = dj_data.get('data', {}).get('items', [])
            for item in items:
                if '纳斯达克100' in item.get('name', ''):
                    data['pe'] = float(item.get('pe'))
                    break
    except Exception:
        pass # 失败则继续使用 fallback PE

    # 如果无法获取到价格，则视为抓取失败
    if data['value'] == 0:
        return None
        
    return data

def calculate_strategy(current_pe, current_value, state):
    """
    根据 bs.md 中定义的金字塔定投策略（激进版）计算今日建议。
    
    规则优先级：
    1. 回撤加码规则 (最高优先级)
    2. 基础定投规则 (基于 PE)
    3. 赎回止盈规则 (基于 PE)
    4. 买回规则 (基于 PE 和历史状态)
    """
    
    # 1. 动态更新历史最高点
    if current_value > state["max_value"]:
        state["max_value"] = current_value
    
    # 2. 计算当前回撤幅度
    max_val = state["max_value"]
    drawdown = (max_val - current_value) / max_val if max_val > 0 else 0
    drawdown_pct = drawdown * 100

    recommendation = ""
    reason = ""

    # --- 规则二：回撤加码规则 (优先级高于普通定投) ---
    # 根据回撤幅度对应的定投金额（从高到低检查）
    drawdown_rules = [
        (30, 5000), (25, 3500), (20, 2500), (18, 2000), 
        (15, 1500), (12, 1000), (10, 600), (8, 400), (6, 200)
    ]
    
    triggered_drawdown = False
    for threshold, amount in drawdown_rules:
        if drawdown_pct >= threshold:
            recommendation = f"定投 {amount} 元"
            reason = f"触发回撤加码规则: 当前回撤 {drawdown_pct:.2f}% >= {threshold}%"
            triggered_drawdown = True
            break

    # --- 规则一：基础定投规则 (仅在未触发回撤加码时执行) ---
    if not triggered_drawdown:
        if 32 <= current_pe < 36:
            recommendation = "定投 200 元"
            reason = f"触发基础定投规则: PE {current_pe:.2f} 在 [32, 36) 区间"
        elif 36 <= current_pe < 38:
            recommendation = "定投 100 元"
            reason = f"触发基础定投规则: PE {current_pe:.2f} 在 [36, 38) 区间"
        elif current_pe >= 38:
            recommendation = "停止定投"
            reason = f"触发基础定投规则: PE {current_pe:.2f} >= 38"
        else:
            recommendation = "观察 (PE < 32)"
            reason = f"当前 PE {current_pe:.2f} 低于定投起始线"

    # --- 规则三：赎回止盈规则 (基于 PE，分批卖出) ---
    if current_pe >= 45:
        recommendation = "赎回剩余 20% 持仓 (清仓)"
        reason = f"触发赎回规则: PE {current_pe:.2f} >= 45"
        state["is_sold_out"] = True # 标记已进入卖出状态
    elif current_pe >= 42:
        recommendation = "再赎回 30% 持仓 (累计 80%)"
        reason = f"触发赎回规则: PE {current_pe:.2f} >= 42"
        state["is_sold_out"] = True
    elif current_pe >= 40:
        recommendation = "赎回 50% 持仓"
        reason = f"触发赎回规则: PE {current_pe:.2f} >= 40"
        state["is_sold_out"] = True

    # --- 规则四：买回规则 (仅在已赎回且未买回过时触发) ---
    if state["is_sold_out"] and not state["buy_back_triggered"]:
        if current_pe <= 35:
            recommendation = "全额买回之前赎回的资金 (一次性操作)"
            reason = f"触发买回规则: PE {current_pe:.2f} <= 35"
            state["buy_back_triggered"] = True # 标记买回操作已触发，后续不再重复
            state["is_sold_out"] = False      # 重置赎回状态

    return recommendation, reason, drawdown_pct

def update_history(date, pe, value, high, drawdown, recommendation):
    """
    将今日的详细数据追加到历史 CSV 文件中。
    如果同一天运行多次，则保留最后一次的结果。
    """
    new_data = {
        "date": [date],
        "pe": [pe],
        "value": [value],
        "high": [high],
        "drawdown": [drawdown],
        "recommendation": [recommendation]
    }
    df_new = pd.DataFrame(new_data)
    
    if os.path.exists(HISTORY_FILE):
        df_old = pd.read_csv(HISTORY_FILE)
        df_combined = pd.concat([df_old, df_new], ignore_index=True)
        # 根据日期去重，保留最新的一条记录
        df_combined.drop_duplicates(subset=['date'], keep='last', inplace=True)
        df_combined.to_csv(HISTORY_FILE, index=False)
    else:
        df_new.to_csv(HISTORY_FILE, index=False)

def main():
    """
    主程序入口。
    """
    ensure_dirs() # 创建目录
    print("="*40)
    print(f"纳指100 策略提示工具 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*40)

    state = load_state() # 加载状态
    data = fetch_data()  # 抓取数据

    if data:
        pe = data['pe']
        val = data['value']
        date = data['date']

        # 执行策略计算
        rec, reason, dd_pct = calculate_strategy(pe, val, state)
        
        # 终端美化输出
        print(f"当前指数: {data['name']}")
        print(f"当前日期: {date}")
        print(f"当前 PE:  {pe:.2f}")
        print(f"当前点位: {val:.2f}")
        print(f"历史高点: {state['max_value']:.2f}")
        print(f"当前回撤: {dd_pct:.2f}%")
        print("-" * 40)
        print(f"【投资建议】: {rec}")
        print(f"【触发理由】: {reason}")
        print("-" * 40)

        # 数据落地持久化
        save_state(state)
        update_history(date, pe, val, state['max_value'], dd_pct, rec)
        
        # 记录详细日志
        log_msg = f"{datetime.now().isoformat()} | PE: {pe:.2f} | VAL: {val:.2f} | DD: {dd_pct:.2f}% | REC: {rec} | REASON: {reason}\n"
        with open(os.path.join(LOG_DIR, "strategy.log"), "a", encoding="utf-8") as f:
            f.write(log_msg)
    else:
        print("无法获取数据，请检查网络连接或 API 状态。")

if __name__ == "__main__":
    main()
