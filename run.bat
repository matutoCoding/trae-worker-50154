@echo off
chcp 65001 > nul
echo ========================================
echo   实验动物房预约管理系统 - 启动脚本
echo ========================================
echo.
echo 正在启动Tkinter版本...
echo (如果已安装PyQt6，也可以运行: python main.py)
echo.
python app_tkinter.py
pause
