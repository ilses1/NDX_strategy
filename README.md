# 纳指100自动投资策略 | Nasdaq-100 Automated Investment System

> 🚀 基于 Python + yfinance 的纳斯达克100智能定投工具，支持 PE 估值策略、回撤加码、止盈赎回、邮件通知和 GitHub Actions 自动化

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Automated-orange.svg)](.github/workflows/run.yml)

[English](README_EN.md) | 简体中文

---

## 📋 目录

- [项目简介](#项目简介)
- [核心功能](#核心功能)
- [投资策略详解](#投资策略详解)
- [快速开始](#快速开始)
- [GitHub Actions 配置](#github-actions-配置)
- [常见问题](#常见问题)
- [项目结构](#项目结构)

---

## 项目简介

本项目是一个**自动化纳指100投资策略系统**，基于 Python 和 yfinance 库，实现纳斯达克100指数的智能投资管理。

### 关键词

`纳斯达克100` `NDX` `QQQ ETF` `PE估值` `智能定投` `回撤加码` `止盈策略` `Python自动化` `投资机器人` `ETF定投`

### 适用人群

- 投资纳斯达克100指数的长期投资者
- 希望实现自动化投资策略的程序员
- 使用 Python 进行量化投资的用户
- 需要指数估值工具的投资者

### 主要特点

- ✅ **PE 估值定投**：根据纳指100 PE-TTM 智能调整定投金额
- ✅ **回撤加码**：从高点回撤时自动增加投资金额
- ✅ **止盈赎回**：PE 过高时分批止盈
- ✅ **买回机制**：PE 回归低位时全额买回
- ✅ **自动化运行**：GitHub Actions 每日自动执行
- ✅ **邮件通知**：投资建议实时推送

---

## 核心功能

### 1. 数据获取

使用 `yfinance` 获取以下数据：

| 数据类型   | 数据源   | 说明                        |
| ---------- | -------- | --------------------------- |
| 实时 PE 值 | QQQ ETF  | 纳指100 ETF 的滚动 PE (TTM) |
| 当前点位   | ^NDX     | 纳斯达克100实时价格         |
| 一年高点   | ^NDX     | 近一年最高收盘价            |
| 回撤计算   | 自动计算 | (高点-当前)/高点            |

### 2. 邮件通知

支持 QQ 邮箱 SMTP 发送投资建议邮件，包含：

- 当前 PE 估值
- 当前点位和回撤幅度
- 投资建议（定投金额或止盈操作）
- 触发原因说明

---

## 投资策略详解

### 策略优先级

```
回撤加码规则（最高优先级）
    ↓
基础定投规则
    ↓
赎回止盈规则
    ↓
买回规则（最低优先级）
```

### 1. 基础定投规则（按 PE-TTM）

根据纳指100当前 PE 估值确定每日定投金额：

| 纳指100 PE-TTM | 定投金额 | 策略说明         |
| -------------- | -------- | ---------------- |
| 32～36倍       | 200元    | 正常定投区间     |
| 36～38倍       | 100元    | 偏高估，降低投入 |
| ≥38倍          | 停止定投 | 高估区域，观望   |

### 2. 回撤加码规则（优先级最高）

当指数从高点回撤时，自动增加定投金额（俗称"金字塔加码"）：

| 从高点回撤幅度 | 定投金额 | 加码逻辑         |
| -------------- | -------- | ---------------- |
| ≥6%            | 200元    | 小幅回撤开始加码 |
| ≥8%            | 400元    | 加倍投入         |
| ≥10%           | 600元    | 继续加码         |
| ≥12%           | 1000元   | 大幅加码         |
| ≥15%           | 1500元   | 深度加码         |
| ≥18%           | 2000元   | 强制定投         |
| ≥20%           | 2500元   | 重仓投入         |
| ≥25%           | 3500元   | 超深度加码       |
| ≥30%           | 5000元   | 最大加码档位     |

### 3. 赎回止盈规则

当 PE 过高时分批赎回持仓：

| 纳指100 PE-TTM | 赎回操作  | 累计赎回    |
| -------------- | --------- | ----------- |
| ≥40倍          | 赎回50%   | 50%         |
| ≥42倍          | 再赎30%   | 80%         |
| ≥45倍          | 赎剩余20% | 100% (清仓) |

### 4. 买回规则

止盈后等待 PE 回归低位时全额买回：

- **触发条件**：纳指100 PE-TTM ≤ 35倍
- **操作方式**：一次性将所有赎回资金投入
- **仅触发一次**：买回后重置状态，继续常规定投

---

## 快速开始

### 环境要求

- Python 3.10 或更高版本
- pip 包管理器
- 可选：QQ 邮箱 SMTP 服务（用于邮件通知）

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/yourusername/NDX_strategy.git
cd NDX_strategy
```

#### 2. 安装依赖

```bash
pip install -r requirements.txt
```

所需依赖：

```
yfinance     # Yahoo Finance 数据源
pandas       # 数据处理
requests     # HTTP 请求
python-dotenv # 环境变量管理
```

#### 3. 配置环境变量（可选）

创建 `.env` 文件用于本地测试：

```bash
# .env 文件
MAIL_HOST=smtp.qq.com
MAIL_USER=your_email@qq.com
MAIL_PASS=your_smtp_authorization_code
MAIL_RECEIVER=receiver@example.com
```

> **注意**：QQ 邮箱需要开启 SMTP 服务并获取授权码

#### 4. 运行策略

```bash
python main.py
```

预期输出示例：

```
========================================
纳指100 策略提示工具 (yfinance版) - 2026-05-27 13:00
========================================
当前指数: Nasdaq 100 (^NDX)
数据日期: 2026-05-27
QQQ ETF当前 PE:  35.42 (基于已知估值)
当前点位: 18500.25
一年高点: 19200.50
当前回撤: 3.65%
----------------------------------------
【投资建议】: 定投 200 元
【触发理由】: 触发基础定投规则: PE 35.42 在 [32, 36) 区间
----------------------------------------
```

---

## GitHub Actions 配置

### 功能特性

- ⏰ **定时执行**：每天北京时间 13:00 自动运行
- 🔒 **安全配置**：敏感信息使用 GitHub Secrets 管理
- 🚀 **即点即用**：支持手动触发运行
- 📧 **自动通知**：运行结果自动发送邮件

### 配置步骤

#### 1. 创建 GitHub Secrets

在 GitHub 仓库中配置以下密钥：

| Secret 名称     | 说明        | 示例                   |
| --------------- | ----------- | ---------------------- |
| `MAIL_HOST`     | SMTP 服务器 | `smtp.qq.com`          |
| `MAIL_USER`     | 发件邮箱    | `your_email@qq.com`    |
| `MAIL_PASS`     | SMTP 授权码 | `xxxxxxxx`             |
| `MAIL_RECEIVER` | 收件邮箱    | `receiver@example.com` |

配置路径：`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

#### 2. 工作流文件

配置文件位于 [`.github/workflows/run.yml`](.github/workflows/run.yml)：

```yaml
name: 纳指100自动策略

on:
  schedule:
    - cron: "0 5 * * *" # 每天 UTC 05:00 = 北京时间 13:00
  workflow_dispatch: # 启用手动触发

jobs:
  run-strategy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: 设置 Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"

      - name: 安装依赖
        run: |
          python -m pip install --upgrade pip
          pip install yfinance pandas

      - name: 执行策略
        env:
          MAIL_HOST: ${{ secrets.MAIL_HOST }}
          MAIL_USER: ${{ secrets.MAIL_USER }}
          MAIL_PASS: ${{ secrets.MAIL_PASS }}
          MAIL_RECEIVER: ${{ secrets.MAIL_RECEIVER }}
        run: python main.py
```

#### 3. 手动触发

1. 进入 GitHub 仓库的 `Actions` 页面
2. 选择 "纳指100自动策略" 工作流
3. 点击 `Run workflow` 按钮

---

## 常见问题

### Q1: yfinance 无法获取数据怎么办？

```bash
# 尝试更新 yfinance
pip install --upgrade yfinance

# 或设置中国镜像源
pip install yfinance -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q2: 邮件发送失败？

1. 确认 QQ 邮箱已开启 SMTP 服务
2. 检查授权码是否正确
3. 查看日志文件 `logs/strategy_yf.log`

### Q3: 如何调整策略参数？

编辑 `main.py` 中的策略规则：

```python
# 回撤加码规则（可自定义阈值和金额）
drawdown_rules = [
    (30, 5000), (25, 3500), (20, 2500),
    (18, 2000), (15, 1500), (12, 1000),
    (10, 600), (8, 400), (6, 200)
]

# 基础定投规则（可自定义 PE 区间和金额）
# PE 32-36: 200元
# PE 36-38: 100元
# PE >= 38: 停止定投
```

### Q4: 时区如何转换？

GitHub Actions 使用 UTC 时间：

| 北京时间 | UTC 时间 | cron 表达式 |
| -------- | -------- | ----------- |
| 13:00    | 05:00    | `0 5 * * *` |
| 14:00    | 06:00    | `0 6 * * *` |
| 08:00    | 00:00    | `0 0 * * *` |

---

## 项目结构

```
NDX_strategy/
├── .github/
│   └── workflows/
│       └── run.yml           # GitHub Actions 工作流
├── data/                      # 数据目录
│   ├── yf_cache/             # yfinance 缓存
│   ├── nasdaq_history_yf.csv # 历史数据
│   └── state_yf.json        # 策略状态
├── logs/                      # 日志目录
│   └── strategy_yf.log       # 执行日志
├── docs/                      # 文档目录
├── main.py                    # 主程序 ⭐
├── QQQPE.py                   # PE 获取脚本
├── requirements.txt          # 依赖清单
└── README.md                 # 项目文档
```

---

## 技术栈

| 技术           | 用途       |
| -------------- | ---------- |
| Python 3.10    | 编程语言   |
| yfinance       | 数据获取   |
| pandas         | 数据处理   |
| GitHub Actions | 自动化部署 |
| SMTP           | 邮件通知   |

---

## 许可证

本项目采用 MIT 许可证开源。

---

## 免责声明

⚠️ **投资有风险，入市需谨慎**

本工具仅供学习和参考之用，不构成任何投资建议。投资者应根据自身风险承受能力做出投资决策，对投资结果承担全部责任。
