# TODO_获取纳指100PE

## 1. 待办事项
- [ ] **自动化运行**: 设置每日定时任务 (Windows Task Scheduler 或 GitHub Actions)。
- [ ] **通知增强**: 目前仅支持命令行和日志，建议接入 Server酱、PushDeer 或钉钉机器人实现手机端实时提醒。
- [ ] **历史高点校准**: 脚本初始运行时将当前点位设为最高点。建议手动修改 `data/state.json` 中的 `max_value` 为过去一年的实际最高点 (约 29663.89，根据雪球数据)，以获得更准确的回撤计算。

## 2. 操作指引
### 如何校准历史高点？
打开 `data/state.json`，将 `max_value` 修改为您认为的“近期高点”值。例如：
```json
{
    "max_value": 29663.89,
    "is_sold_out": false,
    "buy_back_triggered": false
}
```
保存后再次运行 `python nasdaq_strategy.py` 即可看到最新的回撤数据。
