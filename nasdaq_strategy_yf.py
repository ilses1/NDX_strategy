import os
import json
import yfinance as yf
import pandas as pd
from datetime import datetime

# --- 配置参数 ---
DATA_DIR = "data"                                      
LOG_DIR = "logs"                                       
STATE_FILE = os.path.join(DATA_DIR, "state_yf.json")      # 使用独立的状态文件
HISTORY_FILE = os.path.join(DATA_DIR, "nasdaq_history_yf.csv") # 使用独立的历史文件
TICKER_SYMBOL = "^NDX"                                    # 纳斯达克100指数代码

def ensure_dirs():
    """确保必要的本地目录已创建。"""
    for d in [DATA_DIR, LOG_DIR]:
        if not os.path.exists(d):
            os.makedirs(d)
    # 设置 yfinance 缓存位置以避免权限问题
    try:
        yf.set_tz_cache_location(os.path.join(DATA_DIR, "yf_cache"))
    except:
        pass

def load_state():
    """从本地 JSON 文件加载策略执行状态。"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "max_value": 0.0,
        "is_sold_out": False,
        "buy_back_triggered": False
    }

def save_state(state):
    """持久化策略状态。"""
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

def fetch_data():
    """
    使用 yfinance 获取纳指100数据。
    """
    try:
        ticker = yf.Ticker(TICKER_SYMBOL)
        # 获取最近一天的历史数据
        hist = ticker.history(period="1d")
        
        if hist.empty:
            # 如果 1d 没数据（可能是非交易日），尝试 5d 取最后一条
            hist = ticker.history(period="5d")
            
        if not hist.empty:
            latest = hist.iloc[-1]
            # yfinance 不直接提供实时的 PE 指数，这里使用 fallback PE
            # 因为 yfinance 的 info 在某些环境下（如 windows sandbox）可能因为 sqlite 缓存报错
            # 我们优先保证点位的准确性，PE 采用固定值或从历史中推断（如果可能）
            
            # 尝试获取 PE (yfinance 指数 PE 通常不直接提供，这里使用 2026-05-24 已知值)
            current_pe = 35.04 
            
            return {
                "name": "Nasdaq 100 (^NDX)",
                "pe": current_pe,
                "value": float(latest['Close']),
                "date": hist.index[-1].strftime("%Y-%m-%d")
            }
    except Exception as e:
        print(f"Error fetching data via yfinance: {e}")
    return None

def calculate_strategy(current_pe, current_value, state):
    """
    策略逻辑与 nasdaq_strategy.py 保持完全一致。
    """
    if current_value > state["max_value"]:
        state["max_value"] = current_value
    
    max_val = state["max_value"]
    drawdown = (max_val - current_value) / max_val if max_val > 0 else 0
    drawdown_pct = drawdown * 100

    recommendation = ""
    reason = ""

    # --- 规则二：回撤加码规则 (优先级最高) ---
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

    # --- 规则一：基础定投规则 ---
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

    # --- 规则三：赎回止盈规则 ---
    if current_pe >= 45:
        recommendation = "赎回剩余 20% 持仓 (清仓)"
        reason = f"触发赎回规则: PE {current_pe:.2f} >= 45"
        state["is_sold_out"] = True
    elif current_pe >= 42:
        recommendation = "再赎回 30% 持仓 (累计 80%)"
        reason = f"触发赎回规则: PE {current_pe:.2f} >= 42"
        state["is_sold_out"] = True
    elif current_pe >= 40:
        recommendation = "赎回 50% 持仓"
        reason = f"触发赎回规则: PE {current_pe:.2f} >= 40"
        state["is_sold_out"] = True

    # --- 规则四：买回规则 ---
    if state["is_sold_out"] and not state["buy_back_triggered"]:
        if current_pe <= 35:
            recommendation = "全额买回之前赎回的资金 (一次性操作)"
            reason = f"触发买回规则: PE {current_pe:.2f} <= 35"
            state["buy_back_triggered"] = True
            state["is_sold_out"] = False 

    return recommendation, reason, drawdown_pct

def update_history(date, pe, value, high, drawdown, recommendation):
    """保存历史记录。"""
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
        df_combined.drop_duplicates(subset=['date'], keep='last', inplace=True)
        df_combined.to_csv(HISTORY_FILE, index=False)
    else:
        df_new.to_csv(HISTORY_FILE, index=False)

def main():
    ensure_dirs()
    print("="*40)
    print(f"纳指100 策略提示工具 (yfinance版) - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*40)

    state = load_state()
    data = fetch_data()

    if data:
        pe = data['pe']
        val = data['value']
        date = data['date']

        rec, reason, dd_pct = calculate_strategy(pe, val, state)
        
        print(f"当前指数: {data['name']}")
        print(f"数据日期: {date}")
        print(f"当前 PE:  {pe:.2f} (基于已知估值)")
        print(f"当前点位: {val:.2f}")
        print(f"历史高点: {state['max_value']:.2f}")
        print(f"当前回撤: {dd_pct:.2f}%")
        print("-" * 40)
        print(f"【投资建议】: {rec}")
        print(f"【触发理由】: {reason}")
        print("-" * 40)

        save_state(state)
        update_history(date, pe, val, state['max_value'], dd_pct, rec)
        
        log_msg = f"{datetime.now().isoformat()} | YF | PE: {pe:.2f} | VAL: {val:.2f} | DD: {dd_pct:.2f}% | REC: {rec}\n"
        with open(os.path.join(LOG_DIR, "strategy_yf.log"), "a", encoding="utf-8") as f:
            f.write(log_msg)
    else:
        print("无法通过 yfinance 获取数据，请检查网络或 Ticker 代码。")

if __name__ == "__main__":
    main()
