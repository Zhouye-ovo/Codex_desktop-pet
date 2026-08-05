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

## 外观

- 深色圆角卡片，紧凑三段式：顶栏（刷新 / 设置 / 置顶 / 关闭）+ DeepSeek 行 + 识图行。
- 宽度基准 320，高度随内容自适应；缩放档位 80/100/120/150%。
- `assets/bg.png` 保留在仓库中但程序不再加载，可自行删除。

## 数据源与 Key（运行时只读，不写入项目、不打印）

| 项 | 来源 |
| --- | --- |
| DeepSeek 余额 | GET `https://api.deepseek.com/user/balance`，Key = `G:\codex-data\home\auth.json` 的 `OPENAI_API_KEY`，取 `balance_infos` 中 CNY 的 `total_balance` |
| 识图余额 | GET `https://api.siliconflow.cn/v1/user/info`，Key = `G:\codex-data\home\.env` 的 `SILICONFLOW_API_KEY` |
| DeepSeek 今日用量 | 本地解析 `G:\codex-data\home\sessions\**\rollout-*.jsonl` 中 `token_count` 事件的 `info.last_token_usage`（输入+输出），按本地日期汇总 |
| 识图今日用量 | 本地读取 `G:\codex-data\home\vision-usage.jsonl`（vision.js 每次调用成功追加一行：时间 / 模型 / 输入输出 token） |

## 配置

首次运行自动生成 `config.json`（项目根目录，已 gitignore）：窗口位置、置顶、缩放（80/100/120/150%）、刷新间隔（分钟）。右上角按钮：刷新 / 设置 / 置顶 / 关闭。

## 安全

Key 只从上述现有文件读取，任何输出均不回显 Key；`.gitignore` 已排除 `.env`、`auth*.json`、`config.json`、`.venv` 等。
