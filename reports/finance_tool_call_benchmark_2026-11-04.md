# 财经新闻 Tool 真实调用记录

- 测试日期：2026-11-04
- 时区：Asia/Shanghai（北京时间，UTC+8）
- 工具：`collect_latest_news`
- 测试方式：直接调用 Tool，不包含 DeepSeek 生成最终回答的时间

| 调用 | 参数 | 开始时间 | 结束时间 | 耗时 | 返回条数 |
|---|---|---|---|---:|---:|
| 近24小时财经快讯 | `limit=3, max_age_hours=24` | 21:14:01 | 21:15:33 | 92.545秒 | 3 |
| 近72小时财经早报 | `limit=5, max_age_hours=72` | 21:15:33 | 21:17:06 | 92.773秒 | 5 |
| 近7天财经周览 | `limit=8, max_age_hours=168` | 21:17:06 | 21:18:38 | 92.406秒 | 8 |

## 汇总

- 总耗时：277.724秒
- 平均耗时：92.575秒/次
- 三次调用全部成功，没有抛出未处理异常。
- 返回条数分别符合3、5、8条的请求。
- 本次返回新闻全部来自 `WSJ Markets`。

## 观察结论

1. 三次耗时几乎相同，说明瓶颈主要来自逐个请求 RSS 和网络超时，而不是最终返回条数。
2. 当前同步采集方式会累加各来源的等待时间，用户可能需要等待约一分半钟。
3. 结果来源集中在 WSJ，说明其他财经来源可能超时、无符合时效的数据，或没有成功提供可解析条目。
4. 后续应将多来源采集改为异步并发，并记录每个来源的成功、失败与耗时。

## 部分真实结果

- Index Funds Are Better When They’re Lucky and Smart — WSJ Markets
- How Beer Companies Stole Happy Hour From Liquor Brands — WSJ Markets
- Stock Market Today: Stock Futures Rebound as Investors Weigh Democratic Sweep — WSJ Markets
- Bitcoin Miners Pivoted to AI—Only to Find It’s Just as Turbulent as Crypto — WSJ Markets
- Apple Shares Slip, Meta Debt Costs Rise — WSJ Markets
