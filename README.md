# 模型余额 / 用量悬浮小窗

Windows 桌面悬浮小窗：显示 DeepSeek 与识图（硅基流动）两个模型的费用余额；鼠标悬停某行临时切换为该模型今日 token 用量，移开恢复余额。

## 运行

```powershell
cd G:\Codex_desktop-pet
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python main.py
```

自检（不打界面，验证 Key 定位与余额接口）：

```powershell
.venv\Scripts\python main.py --selftest
```

## 底图（assets/bg.png）

- 把图片放到 `assets/bg.png`，程序启动或点顶栏「刷新」时加载，拉伸填满整个窗口（窗口大小固定，不随图片变化）。
- 推荐 640×800 的 2 倍分辨率 PNG（基准窗口 320×400），可带透明；随时替换，点刷新即生效。
- 没有图片时窗口会显示内置占位样式。

## 数据源与 Key（运行时只读，不写入项目、不打印）

| 项 | 来源 |
| --- | --- |
| DeepSeek 余额 | GET `https://api.deepseek.com/user/balance`，Key = `G:\codex-data\home\auth.json` 的 `OPENAI_API_KEY`，取 `balance_infos` 中 CNY 的 `total_balance` |
| 识图余额 | GET `https://api.siliconflow.cn/v1/user/info`，Key = `G:\codex-data\home\.env` 的 `SILICONFLOW_API_KEY` |
| DeepSeek 今日用量 | 本地解析 `G:\codex-data\home\sessions\**\rollout-*.jsonl` 中 `token_count` 事件的 `info.last_token_usage`（输入+输出），按本地日期汇总 |
| 识图今日用量 | 本地读取 `G:\codex-data\home\vision-usage.jsonl`（vision.js 每次调用成功追加一行：时间 / 模型 / 输入输出 token） |

## 配置

首次运行自动生成 `config.json`（项目根目录，已 gitignore）：窗口位置、置顶、缩放（80/100/120/150%）、刷新间隔（分钟）、底图路径。右上角按钮：刷新 / 设置 / 置顶 / 关闭。

## 安全

Key 只从上述现有文件读取，任何输出均不回显 Key；`.gitignore` 已排除 `.env`、`auth*.json`、`config.json`、`.venv` 等。
