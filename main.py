"""模型余额 / 用量悬浮小窗入口。"""
import sys

from src import keys, providers, usage


def selftest() -> int:
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    print("== 余额/用量自检 ==")
    st = keys.key_status()
    if st["deepseek"][0]:
        print(f"DeepSeek Key: 已找到（长度 {st['deepseek'][1]}）")
    else:
        print("DeepSeek Key: 未找到（auth.json 的 OPENAI_API_KEY）")
    if st["siliconflow"][0]:
        print(f"硅基流动 Key: 已找到（长度 {st['siliconflow'][1]}）")
    else:
        print("硅基流动 Key: 未找到（.env 的 SILICONFLOW_API_KEY）")

    r1 = providers.DeepSeekProvider().fetch()
    if r1.error:
        print(f"DeepSeek 余额: 失败 - {r1.error}")
    else:
        print(f"DeepSeek 余额: {'可用' if r1.available else '不可用'} CNY {r1.amount:.2f} ({r1.currency})")

    r2 = providers.SiliconFlowProvider().fetch()
    if r2.error:
        print(f"硅基流动余额: 失败 - {r2.error}")
    else:
        print(f"硅基流动余额: CNY {r2.amount:.2f} ({r2.currency})")

    print(f"DeepSeek 今日 tokens: {usage.deepseek_today_tokens():,}")
    print(f"识图今日 tokens: {usage.vision_today_tokens():,}")
    return 0 if not (r1.error or r2.error) else 1


def main() -> None:
    if "--selftest" in sys.argv:
        sys.exit(selftest())

    from PySide6.QtWidgets import QApplication

    from src.config import Config
    from src.window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("ModelBalanceWidget")
    cfg = Config.load()
    win = MainWindow(cfg)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
