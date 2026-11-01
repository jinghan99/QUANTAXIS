# 后续如何开发策略

策略逻辑放在 QUANTAXIS 的 Python 源码工程中；qamazing_community 用于配置服务地址、查看账户和回测结果。它是编译后的社区客户端，不是可视化策略生成器，也没有原始 Vue 工程。

## 当前可用入口

1. 编辑 `E:\PycharmProjects\QUANTAXIS\strategies` 下的 Python 文件。
2. 使用 WSL Python 3.11 虚拟环境 `/home/jinghan/.local/share/quantaxis-local/venv`。PyCharm 应选择 WSL 解释器，而不是 Windows Python。
3. JupyterLab 在 `http://localhost:8888`。使用 `local-dev\manage.ps1 -Action jupyter` 查看本机访问令牌链接。
4. 数据读取统一经过 35 上的 MongoDB。后端、脚本和 Jupyter 内核使用同一份受保护的连接配置。

## 建议的开发顺序

**数据准备**：先明确股票池、周期、时间范围、行情源和复权口径。采集后核验代码身份、交易日覆盖、OHLC、成交量、重复记录和缺失。当前数据库为新建，尚未采集行情；不要直接执行全市场 `save all`，先选单只股票和小日期窗口验证。

**信号研究**：用 `QA_fetch_stock_day_adv` 读取已经落库的日线，用 `QA.MA` 等函数生成信号。`strategies/ma_signal.py` 是只读的双均线示例；没有行情会返回 `unavailable` 并以状态码 2 退出。它不会编造数据、自动换源或生成虚假收益。

```bash
cd /mnt/e/PycharmProjects/QUANTAXIS
source /home/jinghan/.local/share/quantaxis-local/venv/bin/activate
python strategies/ma_signal.py --code 000001 --start 2025-01-01 --end 2025-12-31
```

该例使用未复权收盘价，只演示指标和信号；价格除权处理、交易日完整性与股票池 PIT 尚需完成。收盘生成的信号移到下一根 K 线使用，仍需在回测中定义真实成交价格，不能据此直接宣称可交易收益。

**回测**：把信号、仓位、成交模拟和绩效计算分开。定义初始资金、费率、滑点、买卖约束、A 股 T+1、停牌和涨跌停处理，保留参数、代码版本、数据版本、逐笔交易和资金曲线。再做样本外检验和滚动验证。

本版本存在实际源码限制：`QAStrategyCtaBase.run_backtest()` / `debug()` 仍引用未定义的 `QA_Risk`、`QA_User`，与“移除旧 QAARP”的现状不一致。官方策略文档中的部分 `BuyOpen` 等便捷接口也未在当前基类中提供。因此，事件回调入口 `user_init` / `on_bar` 可用于理解结构，但不能把文档示例直接当作已通过验收的回测系统。下一步应选择并验证 QIFI 回测路径或修复这些兼容接口，再做一条真实数据的完整回测。

**模拟运行**：回测通过后，再接入 RabbitMQ、实时行情及模拟账户；验证重连、重复信号、订单与成交回报、持仓和收盘结算。本次没有启动这些附加交易服务，也没有发出交易指令。

## dev 与 prod 的关系

开发时修改 dev 源码；prod 使用固定快照，确认策略结果后再重新发布快照。两套环境共享 `192.168.1.35:27017/quantaxis`，所以 dev 写入的行情和账户记录也会被 prod 读取。策略运行记录应包含 `environment`、`strategy_id`、`run_id`、参数和代码版本；开发策略不能复用生产账户 ID。调度控制使用同一个 `qascheduler` 库中的 `jobs_dev` 和 `jobs_prod` 集合，避免重复执行。

## 官方参考

- 安装：https://yutiansut.github.io/QUANTAXIS/getting-started/installation.html
- 策略开发：https://yutiansut.github.io/QUANTAXIS/user-guide/strategy-development.html
- 当前源码：`QUANTAXIS/QAStrategy/qactabase.py`、`QUANTAXIS/QIFI/QifiAccount.py`
