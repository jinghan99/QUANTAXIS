# 行情数据初始化

安装依赖和启动前后端不会自动下载行情。当前 MongoDB 在 `192.168.1.35:27017`，dev / prod 共用 `quantaxis` 库；初始化一次，两套环境都能读取。前端本身不负责行情采集。

## 进入命令行

依赖安装及 `configure_windows.py` 配置完成后，在 PyCharm Terminal / Anaconda Prompt 执行：

```powershell
conda activate quantaxis
cd E:\PycharmProjects\QUANTAXIS
python local-dev\cli.py
```

先用 `save` 查看当前源码支持的子命令。以下是 QUANTAXIS 提示符中的命令，不是 PowerShell 命令。

## 先验证一只股票

```text
save stock_list
save single_stock_day 000001
```

`single_stock_day` 只限制股票代码，不提供起止日期参数，首次会尝试获取其可获得的历史日线。需要限定日期窗口时，须另行使用数据获取 API 加校验、入库流程，不能向这个 CLI 命令追加日期并假设生效。

目前这些保存功能使用 TDX。股票列表获取的内部逻辑还可能尝试旧缓存 / Tushare；实际采集时要保留来源日志，不能把回退或空结果当作成功。TDX 服务器是否连通、历史能覆盖多久，仍需首次真实采集验证。本次未执行任何行情初始化。

下载后检查数据库，不以命令结束或“SUCCESS”字样代替验收：

```python
from QUANTAXIS.QAUtil import DATABASE
query = {'code': '000001'}
print('rows:', DATABASE.stock_day.count_documents(query))
print('first:', DATABASE.stock_day.find_one(query, {'_id': 0}, sort=[('date', 1)]))
print('last:', DATABASE.stock_day.find_one(query, {'_id': 0}, sort=[('date', -1)]))
```

还需核验日期顺序、重复记录、交易日覆盖、价格和成交量字段，以及代码对应证券身份。空数据、连接失败、缺失日期应明确报告，不能补造行情。

## 扩展为日线研究库

单股采集及读回通过后，再按需求执行：

```text
save stock_day
save stock_xdxr
save index_list
save index_day
save stock_block
```

- `stock_day`：股票日线；已有数据时按保存函数实现尝试增量更新。
- `stock_xdxr`：除权除息资料，使用前复权 / 后复权前需要核验。
- `index_list` / `index_day`：指数及基准日线。
- `stock_block`：板块分类，只有策略使用时才需要。

`save stock_min` / `save index_min` 涉及更多数据量，只在分钟级策略需要时执行。当前版本的默认抓取边界、增量排序与复权质量均应通过实际数据检查，不能视为完整历史覆盖保证。

`save all` 会组合执行多项保存任务，且当前源码会顺带创建旧式默认 Web 用户。建议先按上述分项命令初始化，保留来源、失败清单、行数与日期覆盖证据。

数据准备完成后，再运行 `strategies\ma_signal.py` 做只读指标研究。完整策略回测路径仍需按 `STRATEGY_GUIDE.md` 处理当前 alpha 版本的兼容限制。
