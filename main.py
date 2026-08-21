import os
import json
import yfinance as yf
import pandas as pd
from datetime import datetime
# 新增发邮件依赖
import smtplib
from email.mime.text import MIMEText
from email.header import Header

# --- 配置参数 ---
DATA_DIR = "data"                                      
LOG_DIR = "logs"                                       
STATE_FILE = os.path.join(DATA_DIR, "state_yf.json")      # 使用独立的状态文件
HISTORY_FILE = os.path.join(DATA_DIR, "nasdaq_history_yf.csv") # 使用独立的历史文件
TICKER_SYMBOL = "^NDX"                                    # 纳斯达克100指数代码
TICKER_SYMBOL_QQQ = "QQQ"                                # 纳斯达克100ETF代码
TICKER_SYMBOL_VIX = "VIXY"                               # 恐慌指数代码
MA6_DAYS = 126                                           # 半年线（约6个月交易日）

# 邮箱环境变量（不硬编码，从GitHub Secrets读取）
MAIL_HOST = os.getenv("MAIL_HOST", "smtp.qq.com")
MAIL_USER = os.getenv("MAIL_USER")
MAIL_PASS = os.getenv("MAIL_PASS")
MAIL_RECEIVER = os.getenv("MAIL_RECEIVER")

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
    使用 yfinance 获取纳指100数据，包含当前点位和近一年最高点。
    """
    try:
        ticker = yf.Ticker(TICKER_SYMBOL)
        
        # 1. 获取近一年的历史数据用于计算最高点
        hist_1y = ticker.history(period="1y")
        if hist_1y.empty:
            print("Warning: 1y history is empty.")
            return None
            
        high_1y = float(hist_1y['High'].max())
        latest = hist_1y.iloc[-1]
        
        # 2. 获取 PE (yfinance 指数 PE 通常不直接提供，这里使用 2026-05-24 已知值作为 fallback)
        qqq = yf.Ticker(TICKER_SYMBOL_QQQ)
        current_pe = qqq.info.get("trailingPE")
        
        ndx_close = hist_1y['Close']
        ndx_ma6 = float(ndx_close.rolling(MA6_DAYS).mean().iloc[-1])
        if pd.isna(ndx_ma6):
            print("Warning: insufficient NDX history for 6-month MA.")
            return None

        vix = yf.Ticker(TICKER_SYMBOL_VIX)
        vix_hist = vix.history(period="1y")
        if vix_hist.empty or len(vix_hist) < MA6_DAYS:
            print("Warning: insufficient VIX history for 6-month MA.")
            return None
        vix_value = float(vix_hist['Close'].iloc[-1])
        vix_ma6 = float(vix_hist['Close'].rolling(MA6_DAYS).mean().iloc[-1])
        if pd.isna(vix_ma6):
            print("Warning: VIX 6-month MA is NaN.")
            return None

        return {
            "name": "Nasdaq 100 (^NDX)",
            "pe": current_pe,
            "value": float(latest['Close']),
            "high_1y": high_1y,
            "date": hist_1y.index[-1].strftime("%Y-%m-%d"),
            "ndx_ma6": ndx_ma6,
            "ndx_below_ma6": float(latest['Close']) < ndx_ma6,
            "vix_value": vix_value,
            "vix_ma6": vix_ma6,
            "vix_above_ma6": vix_value > vix_ma6,
        }
    except Exception as e:
        print(f"Error fetching data via yfinance: {e}")
    return None

def check_dca_plan_alert(data):
    """纳指低于半年线且 VIXY 高于半年线时，提示计划全仓定投。"""
    if data.get("ndx_below_ma6") and data.get("vix_above_ma6"):
        return "可以开始计划30天内定投全仓买入"
    return None

def calculate_strategy(current_pe, current_value, high_value, state):
    """
    策略逻辑。
    high_value: 传入的近一年最高点。
    """
    # 同步状态中的最高点（虽然计算主要以传入的 high_value 为准）
    if high_value > state["max_value"]:
        state["max_value"] = high_value
    
    drawdown = (high_value - current_value) / high_value if high_value > 0 else 0
    drawdown_pct = drawdown * 100

    recommendation = ""
    reason = ""

    # --- 规则一：基础定投规则（按PE） ---
    pe_amount = 0
    pe_reason = ""
    if current_pe < 32:
        pe_amount = 400
        pe_reason = f"触发基础定投规则: PE {current_pe:.2f} < 32, 定投400元"
    elif 32 <= current_pe < 36:
        pe_amount = 200
        pe_reason = f"触发基础定投规则: PE {current_pe:.2f} 在 [32, 36) 区间"
    elif 36 <= current_pe < 38:
        pe_amount = 100
        pe_reason = f"触发基础定投规则: PE {current_pe:.2f} 在 [36, 38) 区间"
    elif current_pe >= 38:
        pe_amount = 0
        pe_reason = f"触发基础定投规则: PE {current_pe:.2f} >= 38, 停止定投"

    # --- 规则二：回撤加码规则 ---
    drawdown_rules = [
        (30, 5000), (25, 3500), (20, 2500), (18, 2000), 
        (15, 1500), (12, 1000), (10, 600), (8, 400), (6, 200)
    ]
    
    dd_amount = 0
    dd_reason = ""
    for threshold, amount in drawdown_rules:
        if drawdown_pct >= threshold:
            dd_amount = amount
            dd_reason = f"触发回撤加码规则: 当前回撤 {drawdown_pct:.2f}% >= {threshold}%"
            break

    # --- PE和回撤结果取高 ---
    if pe_amount >= dd_amount:
        recommendation = f"定投 {pe_amount} 元" if pe_amount > 0 else "停止定投"
        reason = pe_reason
    else:
        recommendation = f"定投 {dd_amount} 元"
        reason = dd_reason

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

# ===================== 【新增】邮件发送函数 =====================
def send_email(subject, content):
    if not all([MAIL_USER, MAIL_PASS, MAIL_RECEIVER]):
        print("未配置邮箱信息，跳过邮件发送")
        return False
    try:
        msg = MIMEText(content, 'plain', 'utf-8')
        # ✅ 修复 QQ 邮箱报错：From 头需要正确编码
        from_header = Header("纳指100自动策略", 'utf-8')
        from_header.append(f"<{MAIL_USER}>", 'ascii')
        msg['From'] = from_header
        msg['To'] = MAIL_RECEIVER
        msg['Subject'] = Header(subject, 'utf-8')

        server = smtplib.SMTP_SSL(MAIL_HOST, 465)
        server.login(MAIL_USER, MAIL_PASS)
        server.sendmail(MAIL_USER, [MAIL_RECEIVER], msg.as_string())
        server.quit()
        print("✅ 邮件发送成功")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

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
        high_1y = data['high_1y']
        date = data['date']

        rec, reason, dd_pct = calculate_strategy(pe, val, high_1y, state)
        dca_plan_alert = check_dca_plan_alert(data)
        
        print(f"当前指数: {data['name']}")
        print(f"数据日期: {date}")
        print(f"QQQ ETF当前 PE:  {pe:.2f} (基于已知估值)")
        print(f"当前点位: {val:.2f}")
        print(f"纳指100半年线: {data['ndx_ma6']:.2f} ({'低于' if data['ndx_below_ma6'] else '高于'}半年线)")
        print(f"VIXY: {data['vix_value']:.2f}")
        print(f"VIXY半年线: {data['vix_ma6']:.2f} ({'高于' if data['vix_above_ma6'] else '低于'}半年线)")
        print(f"一年高点: {high_1y:.2f}")
        print(f"当前回撤: {dd_pct:.2f}%")
        print("-" * 40)
        print(f"【投资建议】: {rec}")
        print(f"【触发理由】: {reason}")
        if dca_plan_alert:
            print(f"【额外提示】: {dca_plan_alert}")
        print("-" * 40)

        save_state(state)
        update_history(date, pe, val, state['max_value'], dd_pct, rec)
        
        alert_suffix = f" | ALERT: {dca_plan_alert}" if dca_plan_alert else ""
        log_msg = f"{datetime.now().isoformat()} | YF | PE: {pe:.2f} | VAL: {val:.2f} | DD: {dd_pct:.2f}% | REC: {rec}{alert_suffix}\n"
        with open(os.path.join(LOG_DIR, "strategy_yf.log"), "a", encoding="utf-8") as f:
            f.write(log_msg)

        # ===================== 【新增】调用发邮件 =====================
        email_title = f"【纳指100策略】{rec} | PE {pe:.2f}"
        extra_alert_line = f"\n额外提示：{dca_plan_alert}\n" if dca_plan_alert else ""
        email_content = f"""纳指100 自动投资提醒

数据日期：{date}
QQQ PE：{pe:.2f}
当前点位：{val:.2f}
纳指100半年线：{data['ndx_ma6']:.2f}
恐慌指数 VIXY：{data['vix_value']:.2f}
VIXY半年线：{data['vix_ma6']:.2f}
近一年高点：{high_1y:.2f}
当前回撤：{dd_pct:.2f}%

投资建议：{rec}
触发理由：{reason}
{extra_alert_line}
系统自动发送
"""
        send_email(email_title, email_content)
        
    else:
        print("无法通过 yfinance 获取数据，请检查网络或 Ticker 代码。")
        send_email("纳指100策略执行失败", "数据获取失败，请检查")

if __name__ == "__main__":
    main()