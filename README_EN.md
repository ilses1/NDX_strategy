# Nasdaq-100 Automated Investment System | 纳指100自动投资策略

> 🚀 Python-based Nasdaq-100 smart dollar-cost averaging tool with PE valuation strategy, drawdown scaling, profit-taking, email notifications, and GitHub Actions automation

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Automated-orange.svg)](.github/workflows/run.yml)

[English](README_EN.md) | [简体中文](README.md)

---

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Key Features](#key-features)
- [Investment Strategy](#investment-strategy)
- [Quick Start](#quick-start)
- [GitHub Actions Setup](#github-actions-setup)
- [FAQ](#faq)
- [Project Structure](#project-structure)

---

## Project Overview

An **automated Nasdaq-100 investment strategy system** built with Python and yfinance library, implementing intelligent investment management for the Nasdaq-100 Index.

### Keywords

`Nasdaq 100` `NDX` `QQQ ETF` `PE Valuation` `Dollar-Cost Averaging` `DCA` `Drawdown Scaling` `Profit Taking` `Python Automation` `Investment Bot` `ETF Investing` `Systematic Investment`

### Target Audience

- Long-term investors in Nasdaq-100 Index
- Programmers seeking automated investment strategies
- Users doing quantitative investing with Python
- Investors needing index valuation tools

### Key Features

- ✅ **PE Valuation DCA**: Smart adjustment of investment amounts based on Nasdaq-100 PE-TTM
- ✅ **Drawdown Scaling**: Automatically increase investment during market pullbacks
- ✅ **Profit-Taking**: Phase out holdings when PE is too high
- ✅ **Buyback Mechanism**: Full reinvestment when PE returns to low levels
- ✅ **Automated Execution**: GitHub Actions runs daily automatically
- ✅ **Email Notifications**: Real-time investment recommendation delivery

---

## Key Features

### 1. Data Acquisition

Use `yfinance` to fetch the following data:

| Data Type     | Data Source     | Description                      |
| ------------- | --------------- | -------------------------------- |
| Real-time PE  | QQQ ETF         | Nasdaq-100 ETF trailing PE (TTM) |
| Current Price | ^NDX            | Real-time Nasdaq-100 price       |
| 1-Year High   | ^NDX            | Highest close in past year       |
| Drawdown      | Auto-calculated | (High - Current) / High          |

### 2. Email Notifications

Support QQ Mail SMTP for sending investment recommendation emails, including:

- Current PE valuation
- Current price and drawdown percentage
- Investment recommendation (investment amount or profit-taking action)
- Trigger reason explanation

---

## Investment Strategy

### Strategy Priority

```
Drawdown Scaling Rules (Highest Priority)
    ↓
Base Investment Rules
    ↓
Profit-Taking Redemption Rules
    ↓
Buyback Rules (Lowest Priority)
```

### 1. Base Investment Rules (by PE-TTM)

Determine daily investment amount based on current Nasdaq-100 PE valuation:

| Nasdaq-100 PE-TTM | Investment Amount | Strategy Description                   |
| ----------------- | ----------------- | -------------------------------------- |
| 32～36x           | 200 CNY           | Normal investment range                |
| 36～38x           | 100 CNY           | Slightly overvalued, reduce investment |
| ≥38x              | Stop investment   | High valuation zone, wait              |

### 2. Drawdown Scaling Rules (Highest Priority)

Automatically increase investment when the index pulls back from highs (commonly called "pyramid scaling"):

| Drawdown from High | Investment Amount | Scaling Logic                   |
| ------------------ | ----------------- | ------------------------------- |
| ≥6%                | 200 CNY           | Start scaling on small pullback |
| ≥8%                | 400 CNY           | Double investment               |
| ≥10%               | 600 CNY           | Continue scaling                |
| ≥12%               | 1000 CNY          | Significant scaling             |
| ≥15%               | 1500 CNY          | Deep scaling                    |
| ≥18%               | 2000 CNY          | Force investment                |
| ≥20%               | 2500 CNY          | Heavy position                  |
| ≥25%               | 3500 CNY          | Ultra-deep scaling              |
| ≥30%               | 5000 CNY          | Maximum scaling tier            |

### 3. Profit-Taking Redemption Rules

Phase out holdings when PE is too high:

| Nasdaq-100 PE-TTM | Redemption Operation | Cumulative Redemption |
| ----------------- | -------------------- | --------------------- |
| ≥40x              | Redeem 50%           | 50%                   |
| ≥42x              | Redeem another 30%   | 80%                   |
| ≥45x              | Redeem remaining 20% | 100% (Full exit)      |

### 4. Buyback Rules

Wait for PE to return to low levels after profit-taking for full reinvestment:

- **Trigger Condition**: Nasdaq-100 PE-TTM ≤ 35x
- **Operation**: Invest all previously redeemed funds in a one-time operation
- **One-time trigger**: After buyback, reset state and continue normal investment

---

## Quick Start

### Requirements

- Python 3.10 or higher
- pip package manager
- Optional: QQ Mail SMTP service (for email notifications)

### Installation Steps

#### 1. Clone the Project

```bash
git clone https://github.com/yourusername/NDX_strategy.git
cd NDX_strategy
```

#### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Required dependencies:

```
yfinance      # Yahoo Finance data source
pandas        # Data processing
requests      # HTTP requests
python-dotenv # Environment variable management
```

#### 3. Configure Environment Variables (Optional)

Create a `.env` file for local testing:

```bash
# .env file
MAIL_HOST=smtp.qq.com
MAIL_USER=your_email@qq.com
MAIL_PASS=your_smtp_authorization_code
MAIL_RECEIVER=receiver@example.com
```

> **Note**: QQ Mail requires enabling SMTP service and obtaining an authorization code

#### 4. Run the Strategy

```bash
python main.py
```

Expected output example:

```
========================================
Nasdaq-100 Strategy Tool (yfinance) - 2026-05-27 13:00
========================================
Current Index: Nasdaq 100 (^NDX)
Data Date: 2026-05-27
QQQ ETF Current PE: 35.42 (based on known valuation)
Current Price: 18500.25
1-Year High: 19200.50
Current Drawdown: 3.65%
----------------------------------------
【Investment Recommendation】: Invest 200 CNY
【Trigger Reason】: Base investment rule triggered: PE 35.42 in [32, 36) range
----------------------------------------
```

---

## GitHub Actions Setup

### Features

- ⏰ **Scheduled Execution**: Runs automatically daily at 13:00 Beijing Time
- 🔒 **Secure Configuration**: Sensitive information managed via GitHub Secrets
- 🚀 **On-Demand**: Supports manual trigger
- 📧 **Auto Notification**: Run results sent via email

### Configuration Steps

#### 1. Create GitHub Secrets

Configure the following secrets in your GitHub repository:

| Secret Name     | Description             | Example                |
| --------------- | ----------------------- | ---------------------- |
| `MAIL_HOST`     | SMTP Server             | `smtp.qq.com`          |
| `MAIL_USER`     | Sender Email            | `your_email@qq.com`    |
| `MAIL_PASS`     | SMTP Authorization Code | `xxxxxxxx`             |
| `MAIL_RECEIVER` | Receiver Email          | `receiver@example.com` |

Configuration path: `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

#### 2. Workflow File

The configuration file is located at [`.github/workflows/run.yml`](.github/workflows/run.yml):

```yaml
name: 纳指100自动策略

on:
  schedule:
    - cron: "0 5 * * *" # Daily at UTC 05:00 = Beijing Time 13:00
  workflow_dispatch: # Enable manual trigger

jobs:
  run-strategy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install yfinance pandas

      - name: Run strategy
        env:
          MAIL_HOST: ${{ secrets.MAIL_HOST }}
          MAIL_USER: ${{ secrets.MAIL_USER }}
          MAIL_PASS: ${{ secrets.MAIL_PASS }}
          MAIL_RECEIVER: ${{ secrets.MAIL_RECEIVER }}
        run: python main.py
```

#### 3. Manual Trigger

1. Go to the `Actions` page of your GitHub repository
2. Select the "纳指100自动策略" workflow
3. Click the `Run workflow` button

---

## FAQ

### Q1: What to do if yfinance fails to fetch data?

```bash
# Try upgrading yfinance
pip install --upgrade yfinance

# Or set Chinese mirror source
pip install yfinance -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q2: Email sending failed?

1. Confirm QQ Mail SMTP service is enabled
2. Check if authorization code is correct
3. Check log file `logs/strategy_yf.log`

### Q3: How to adjust strategy parameters?

Edit strategy rules in `main.py`:

```python
# Drawdown scaling rules (customizable thresholds and amounts)
drawdown_rules = [
    (30, 5000), (25, 3500), (20, 2500),
    (18, 2000), (15, 1500), (12, 1000),
    (10, 600), (8, 400), (6, 200)
]

# Base investment rules (customizable PE ranges and amounts)
# PE 32-36: 200 CNY
# PE 36-38: 100 CNY
# PE >= 38: Stop investment
```

### Q4: How to convert time zones?

GitHub Actions uses UTC time:

| Beijing Time | UTC Time | cron Expression |
| ------------ | -------- | --------------- |
| 13:00        | 05:00    | `0 5 * * *`     |
| 14:00        | 06:00    | `0 6 * * *`     |
| 08:00        | 00:00    | `0 0 * * *`     |

---

## Project Structure

```
NDX_strategy/
├── .github/
│   └── workflows/
│       └── run.yml           # GitHub Actions workflow
├── data/                      # Data directory
│   ├── yf_cache/             # yfinance cache
│   ├── nasdaq_history_yf.csv # Historical data
│   └── state_yf.json        # Strategy state
├── logs/                      # Log directory
│   └── strategy_yf.log       # Execution logs
├── docs/                      # Documentation directory
├── main.py                    # Main program ⭐
├── QQQPE.py                   # PE fetching script
├── requirements.txt          # Dependencies list
└── README_EN.md              # This file
```

---

## Tech Stack

| Technology     | Purpose              |
| -------------- | -------------------- |
| Python 3.10    | Programming language |
| yfinance       | Data acquisition     |
| pandas         | Data processing      |
| GitHub Actions | Automated deployment |
| SMTP           | Email notifications  |

---

## License

This project is open source under the MIT License.

---

## Disclaimer

⚠️ **Investments involve risk, enter the market with caution**

This tool is for learning and reference purposes only and does not constitute any investment advice. Investors should make investment decisions based on their own risk tolerance and bear full responsibility for the investment results.
