import yfinance as yf

# 用 QQQ（纳指100ETF）
qqq = yf.Ticker("QQQ")
info = qqq.info

# 滚动PE（TTM）、前瞻PE
trailing_pe = info.get("trailingPE")
forward_pe  = info.get("forwardPE")

print("QQQ trailingPE（代表纳指100 TTM PE）:", trailing_pe)
print("QQQ forwardPE（前瞻PE）:", forward_pe)