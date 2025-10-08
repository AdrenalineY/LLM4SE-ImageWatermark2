"""
Photo Watermark 2 - 应用程序入口
"""

import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

# 添加应用根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ui.main_window import MainWindow


def main():
    """主函数"""
    # 支持高DPI显示（必须在创建QApplication之前设置）
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("Photo Watermark 2")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Photo Watermark Team")
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    # 启动应用程序事件循环
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
