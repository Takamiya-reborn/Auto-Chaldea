def _show_startup_error(error):
    """在无控制台打包模式下保留启动失败信息。"""
    import ctypes
    import sys
    import traceback
    from pathlib import Path

    executable_dir = Path(sys.executable).resolve().parent
    log_path = executable_dir / "startup-error.log"
    details = "".join(traceback.format_exception(error))
    try:
        log_path.write_text(details, encoding="utf-8")
    except OSError:
        log_path = Path.cwd() / "startup-error.log"
        try:
            log_path.write_text(details, encoding="utf-8")
        except OSError:
            pass

    ctypes.windll.user32.MessageBoxW(
        0,
        f"Auto-Chaldea 启动失败。\n\n{details}\n错误详情已保存到：\n{log_path}",
        "Auto-Chaldea",
        0x10,
    )


if __name__ == "__main__":
    try:
        from auto_chaldea import main

        main()
    except Exception as error:
        _show_startup_error(error)
