"""
主窗口UI模块
实现应用程序的主要用户界面和交互逻辑
"""

import os
from typing import Optional, List
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QPushButton, QLabel, QLineEdit, QSlider,
    QComboBox, QGroupBox, QGridLayout, QFileDialog, QMessageBox,
    QProgressBar, QApplication, QFrame, QScrollArea, QButtonGroup,
    QRadioButton, QSpinBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QPixmap, QIcon, QFont, QPainter, QPen

from ..core.image_processor import ImageProcessor
from ..core.config_manager import ConfigManager, WatermarkConfig


class ImageListWidget(QListWidget):
    """自定义图像列表控件，支持拖拽"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.InternalMove)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
            
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            files = [url.toLocalFile() for url in urls]
            self.parent().load_dropped_files(files)
            event.accept()
        else:
            event.ignore()


class PreviewGraphicsView(QGraphicsView):
    """预览图像的GraphicsView"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        
        # 当前显示的图像项
        self.image_item = None
        
    def set_image(self, pixmap: QPixmap):
        """设置要显示的图像"""
        self.scene.clear()
        if pixmap and not pixmap.isNull():
            self.image_item = QGraphicsPixmapItem(pixmap)
            self.scene.addItem(self.image_item)
            self.fitInView(self.image_item, Qt.KeepAspectRatio)
    
    def resizeEvent(self, event):
        """窗口大小改变时重新调整图像"""
        super().resizeEvent(event)
        if self.image_item:
            self.fitInView(self.image_item, Qt.KeepAspectRatio)


class ExportThread(QThread):
    """导出线程"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(int, int)  # 成功数量, 总数量
    error = pyqtSignal(str)
    
    def __init__(self, processor, file_paths, output_folder, config):
        super().__init__()
        self.processor = processor
        self.file_paths = file_paths
        self.output_folder = output_folder
        self.config = config
        
    def run(self):
        """执行导出"""
        success_count = 0
        total_count = len(self.file_paths)
        
        for i, file_path in enumerate(self.file_paths):
            try:
                # 生成输出文件名
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                
                if self.config.filename_rule == "prefix":
                    output_name = f"{self.config.filename_prefix}{base_name}"
                elif self.config.filename_rule == "suffix":
                    output_name = f"{base_name}{self.config.filename_suffix}"
                else:  # original
                    output_name = base_name
                
                # 添加扩展名
                if self.config.output_format.upper() == "JPEG":
                    output_name += ".jpg"
                else:
                    output_name += ".png"
                
                output_path = os.path.join(self.output_folder, output_name)
                
                # 创建带水印的图像
                original_image = self.processor.images[file_path]
                if self.config.use_custom_position:
                    position = self.config.custom_position
                else:
                    position = self.processor.calculate_position(
                        original_image.size, 
                        self.config.text, 
                        self.config.position_type,
                        self.config.font_size
                    )
                
                watermarked_image = self.processor.add_text_watermark(
                    original_image,
                    self.config.text,
                    position,
                    self.config.opacity,
                    self.config.font_size
                )
                
                # 保存图像
                if self.config.output_format.upper() == "JPEG":
                    # 转换为RGB模式
                    if watermarked_image.mode == 'RGBA':
                        background = watermarked_image.convert('RGB')
                        watermarked_image = background
                    watermarked_image.save(output_path, 
                                         format="JPEG", 
                                         quality=self.config.jpeg_quality)
                else:
                    watermarked_image.save(output_path, format="PNG")
                
                success_count += 1
                
            except Exception as e:
                self.error.emit(f"导出 {os.path.basename(file_path)} 失败: {str(e)}")
            
            # 更新进度
            progress = int((i + 1) * 100 / total_count)
            self.progress.emit(progress)
        
        self.finished.emit(success_count, total_count)


class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photo Watermark 2")
        self.setGeometry(100, 100, 1200, 800)
        
        # 初始化核心组件
        self.image_processor = ImageProcessor()
        self.config_manager = ConfigManager()
        
        # 当前水印预览
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.update_preview)
        
        # 设置界面
        self.setup_ui()
        self.connect_signals()
        
        # 加载配置
        self.load_config_to_ui()
        
    def setup_ui(self):
        """设置用户界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧面板 - 图像列表
        self.setup_left_panel(splitter)
        
        # 中间面板 - 预览区域
        self.setup_center_panel(splitter)
        
        # 右侧面板 - 控制面板
        self.setup_right_panel(splitter)
        
        # 设置分割器比例
        splitter.setSizes([250, 500, 350])
        
        # 底部状态栏
        self.statusBar().showMessage("就绪")
        
    def setup_left_panel(self, parent):
        """设置左侧图像列表面板"""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 标题
        title_label = QLabel("图像列表")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        left_layout.addWidget(title_label)
        
        # 导入按钮组
        import_layout = QHBoxLayout()
        self.import_files_btn = QPushButton("导入图片")
        self.import_folder_btn = QPushButton("导入文件夹")
        import_layout.addWidget(self.import_files_btn)
        import_layout.addWidget(self.import_folder_btn)
        left_layout.addLayout(import_layout)
        
        # 图像列表
        self.image_list = ImageListWidget(self)
        self.image_list.setIconSize(QSize(120, 120))
        left_layout.addWidget(self.image_list)
        
        # 清空按钮
        self.clear_images_btn = QPushButton("清空列表")
        left_layout.addWidget(self.clear_images_btn)
        
        parent.addWidget(left_widget)
        
    def setup_center_panel(self, parent):
        """设置中间预览面板"""
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        
        # 标题
        title_label = QLabel("预览")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        center_layout.addWidget(title_label)
        
        # 预览区域
        self.preview_view = PreviewGraphicsView()
        self.preview_view.setMinimumSize(400, 300)
        center_layout.addWidget(self.preview_view)
        
        # 提示标签
        self.preview_hint = QLabel("请导入图片文件")
        self.preview_hint.setAlignment(Qt.AlignCenter)
        self.preview_hint.setStyleSheet("color: gray; font-size: 14px;")
        center_layout.addWidget(self.preview_hint)
        
        parent.addWidget(center_widget)
        
    def setup_right_panel(self, parent):
        """设置右侧控制面板"""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # 水印设置组
        self.setup_watermark_group(scroll_layout)
        
        # 导出设置组
        self.setup_export_group(scroll_layout)
        
        # 操作按钮组
        self.setup_action_group(scroll_layout)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        right_layout.addWidget(scroll)
        
        parent.addWidget(right_widget)
        
    def setup_watermark_group(self, parent_layout):
        """设置水印配置组"""
        watermark_group = QGroupBox("水印设置")
        watermark_layout = QVBoxLayout(watermark_group)
        
        # 文本输入
        text_layout = QHBoxLayout()
        text_layout.addWidget(QLabel("水印文字:"))
        self.watermark_text = QLineEdit("Sample Watermark")
        text_layout.addWidget(self.watermark_text)
        watermark_layout.addLayout(text_layout)
        
        # 字体大小
        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("字体大小:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(12, 200)
        self.font_size_spin.setValue(36)
        font_size_layout.addWidget(self.font_size_spin)
        watermark_layout.addLayout(font_size_layout)
        
        # 透明度
        opacity_layout = QVBoxLayout()
        opacity_layout.addWidget(QLabel("透明度:"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 255)
        self.opacity_slider.setValue(128)
        opacity_layout.addWidget(self.opacity_slider)
        
        self.opacity_label = QLabel("50%")
        self.opacity_label.setAlignment(Qt.AlignCenter)
        opacity_layout.addWidget(self.opacity_label)
        watermark_layout.addLayout(opacity_layout)
        
        # 位置设置
        position_group = QGroupBox("位置设置")
        position_layout = QGridLayout(position_group)
        
        # 九宫格按钮
        self.position_buttons = QButtonGroup()
        positions = [
            ("左上", "top-left", 0, 0),
            ("上中", "top-center", 0, 1),
            ("右上", "top-right", 0, 2),
            ("左中", "middle-left", 1, 0),
            ("正中", "center", 1, 1),
            ("右中", "middle-right", 1, 2),
            ("左下", "bottom-left", 2, 0),
            ("下中", "bottom-center", 2, 1),
            ("右下", "bottom-right", 2, 2)
        ]
        
        for text, value, row, col in positions:
            btn = QRadioButton(text)
            btn.setProperty("position", value)
            self.position_buttons.addButton(btn)
            position_layout.addWidget(btn, row, col)
            if value == "bottom-right":
                btn.setChecked(True)
        
        watermark_layout.addWidget(position_group)
        parent_layout.addWidget(watermark_group)
        
    def setup_export_group(self, parent_layout):
        """设置导出配置组"""
        export_group = QGroupBox("导出设置")
        export_layout = QVBoxLayout(export_group)
        
        # 输出格式
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("输出格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "JPEG"])
        format_layout.addWidget(self.format_combo)
        export_layout.addLayout(format_layout)
        
        # JPEG质量
        self.jpeg_quality_layout = QVBoxLayout()
        self.jpeg_quality_layout.addWidget(QLabel("JPEG质量:"))
        self.jpeg_quality_slider = QSlider(Qt.Horizontal)
        self.jpeg_quality_slider.setRange(1, 100)
        self.jpeg_quality_slider.setValue(95)
        self.jpeg_quality_layout.addWidget(self.jpeg_quality_slider)
        
        self.jpeg_quality_label = QLabel("95%")
        self.jpeg_quality_label.setAlignment(Qt.AlignCenter)
        self.jpeg_quality_layout.addWidget(self.jpeg_quality_label)
        
        for i in range(self.jpeg_quality_layout.count()):
            widget = self.jpeg_quality_layout.itemAt(i).widget()
            if widget:
                widget.hide()
        
        export_layout.addLayout(self.jpeg_quality_layout)
        
        # 文件名规则
        filename_layout = QVBoxLayout()
        filename_layout.addWidget(QLabel("文件名规则:"))
        
        self.filename_original = QRadioButton("保持原名")
        self.filename_prefix = QRadioButton("添加前缀")
        self.filename_suffix = QRadioButton("添加后缀")
        self.filename_suffix.setChecked(True)
        
        filename_layout.addWidget(self.filename_original)
        filename_layout.addWidget(self.filename_prefix)
        filename_layout.addWidget(self.filename_suffix)
        
        # 前缀/后缀输入
        self.prefix_input = QLineEdit("wm_")
        self.suffix_input = QLineEdit("_watermarked")
        
        prefix_layout = QHBoxLayout()
        prefix_layout.addWidget(QLabel("前缀:"))
        prefix_layout.addWidget(self.prefix_input)
        filename_layout.addLayout(prefix_layout)
        
        suffix_layout = QHBoxLayout()
        suffix_layout.addWidget(QLabel("后缀:"))
        suffix_layout.addWidget(self.suffix_input)
        filename_layout.addLayout(suffix_layout)
        
        export_layout.addLayout(filename_layout)
        parent_layout.addWidget(export_group)
        
    def setup_action_group(self, parent_layout):
        """设置操作按钮组"""
        action_group = QGroupBox("操作")
        action_layout = QVBoxLayout(action_group)
        
        # 导出按钮
        self.export_btn = QPushButton("批量导出")
        self.export_btn.setStyleSheet("QPushButton { font-size: 14px; padding: 10px; }")
        action_layout.addWidget(self.export_btn)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        action_layout.addWidget(self.progress_bar)
        
        parent_layout.addWidget(action_group)
    
    def connect_signals(self):
        """连接信号和槽"""
        # 导入按钮
        self.import_files_btn.clicked.connect(self.import_files)
        self.import_folder_btn.clicked.connect(self.import_folder)
        self.clear_images_btn.clicked.connect(self.clear_images)
        
        # 图像列表
        self.image_list.itemClicked.connect(self.on_image_selected)
        
        # 水印设置
        self.watermark_text.textChanged.connect(self.on_watermark_changed)
        self.font_size_spin.valueChanged.connect(self.on_watermark_changed)
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)
        self.position_buttons.buttonClicked.connect(self.on_watermark_changed)
        
        # 导出设置
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        self.jpeg_quality_slider.valueChanged.connect(self.on_jpeg_quality_changed)
        
        # 导出按钮
        self.export_btn.clicked.connect(self.export_images)
    
    def import_files(self):
        """导入图片文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择图片文件",
            "",
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff *.tif)"
        )
        
        if files:
            self.load_files(files)
    
    def import_folder(self):
        """导入文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            count = self.image_processor.load_images_from_folder(folder)
            if count > 0:
                self.update_image_list()
                self.statusBar().showMessage(f"成功导入 {count} 张图片")
            else:
                QMessageBox.information(self, "提示", "该文件夹中没有找到支持的图片文件")
    
    def load_dropped_files(self, files):
        """处理拖拽的文件"""
        image_files = []
        folders = []
        
        for file_path in files:
            if os.path.isfile(file_path):
                if any(file_path.lower().endswith(fmt) for fmt in self.image_processor.SUPPORTED_INPUT_FORMATS):
                    image_files.append(file_path)
            elif os.path.isdir(file_path):
                folders.append(file_path)
        
        # 加载图片文件
        if image_files:
            self.load_files(image_files)
        
        # 加载文件夹
        total_count = 0
        for folder in folders:
            count = self.image_processor.load_images_from_folder(folder)
            total_count += count
        
        if total_count > 0:
            self.update_image_list()
            self.statusBar().showMessage(f"从文件夹成功导入 {total_count} 张图片")
    
    def load_files(self, files):
        """加载文件列表"""
        success_count = 0
        for file_path in files:
            if self.image_processor.load_image(file_path):
                success_count += 1
        
        if success_count > 0:
            self.update_image_list()
            self.statusBar().showMessage(f"成功导入 {success_count} 张图片")
        else:
            QMessageBox.warning(self, "警告", "没有成功导入任何图片文件")
    
    def update_image_list(self):
        """更新图像列表显示"""
        self.image_list.clear()
        
        for file_path in self.image_processor.get_image_list():
            # 创建列表项
            item = QListWidgetItem()
            item.setData(Qt.UserRole, file_path)
            
            # 设置缩略图
            thumbnail = self.image_processor.create_thumbnail(file_path)
            if thumbnail:
                item.setIcon(QIcon(thumbnail))
            
            # 设置文件名
            filename = os.path.basename(file_path)
            item.setText(filename)
            item.setToolTip(file_path)
            
            self.image_list.addItem(item)
        
        # 如果有图像，选择第一个
        if self.image_list.count() > 0:
            self.image_list.setCurrentRow(0)
            self.on_image_selected(self.image_list.item(0))
            self.preview_hint.hide()
        else:
            self.preview_view.set_image(QPixmap())
            self.preview_hint.show()
    
    def clear_images(self):
        """清空图像列表"""
        self.image_processor.clear_images()
        self.image_list.clear()
        self.preview_view.set_image(QPixmap())
        self.preview_hint.show()
        self.statusBar().showMessage("已清空图像列表")
    
    def on_image_selected(self, item):
        """图像选择事件"""
        if item:
            file_path = item.data(Qt.UserRole)
            self.image_processor.set_current_image(file_path)
            self.update_preview()
    
    def on_watermark_changed(self):
        """水印设置改变事件"""
        # 延迟更新预览以避免频繁刷新
        self.preview_timer.stop()
        self.preview_timer.start(300)  # 300ms 延迟
    
    def on_opacity_changed(self):
        """透明度改变事件"""
        value = self.opacity_slider.value()
        percent = int(value * 100 / 255)
        self.opacity_label.setText(f"{percent}%")
        self.on_watermark_changed()
    
    def on_format_changed(self):
        """格式改变事件"""
        format_text = self.format_combo.currentText()
        # 显示/隐藏JPEG质量设置
        for i in range(self.jpeg_quality_layout.count()):
            widget = self.jpeg_quality_layout.itemAt(i).widget()
            if widget:
                if format_text == "JPEG":
                    widget.show()
                else:
                    widget.hide()
    
    def on_jpeg_quality_changed(self):
        """JPEG质量改变事件"""
        value = self.jpeg_quality_slider.value()
        self.jpeg_quality_label.setText(f"{value}%")
    
    def update_preview(self):
        """更新预览"""
        current_image = self.image_processor.get_current_image()
        if not current_image:
            return
        
        # 获取当前水印设置
        config = self.get_current_config()
        
        # 计算位置
        if config.use_custom_position:
            position = config.custom_position
        else:
            position = self.image_processor.calculate_position(
                current_image.size,
                config.text,
                config.position_type,
                config.font_size
            )
        
        # 添加水印
        watermarked_image = self.image_processor.add_text_watermark(
            current_image,
            config.text,
            position,
            config.opacity,
            config.font_size
        )
        
        # 转换为QPixmap并显示
        pixmap = self.image_processor.pil_to_qpixmap(watermarked_image)
        self.preview_view.set_image(pixmap)
    
    def get_current_config(self) -> WatermarkConfig:
        """获取当前UI配置"""
        config = WatermarkConfig()
        
        # 水印设置
        config.text = self.watermark_text.text()
        config.font_size = self.font_size_spin.value()
        config.opacity = self.opacity_slider.value()
        
        # 位置设置
        for button in self.position_buttons.buttons():
            if button.isChecked():
                config.position_type = button.property("position")
                break
        
        # 导出设置
        config.output_format = self.format_combo.currentText()
        config.jpeg_quality = self.jpeg_quality_slider.value()
        
        if self.filename_original.isChecked():
            config.filename_rule = "original"
        elif self.filename_prefix.isChecked():
            config.filename_rule = "prefix"
        else:
            config.filename_rule = "suffix"
        
        config.filename_prefix = self.prefix_input.text()
        config.filename_suffix = self.suffix_input.text()
        
        return config
    
    def load_config_to_ui(self):
        """加载配置到UI"""
        config = self.config_manager.get_config()
        
        # 设置水印配置
        self.watermark_text.setText(config.text)
        self.font_size_spin.setValue(config.font_size)
        self.opacity_slider.setValue(config.opacity)
        self.on_opacity_changed()
        
        # 设置位置
        for button in self.position_buttons.buttons():
            if button.property("position") == config.position_type:
                button.setChecked(True)
                break
        
        # 设置导出配置
        self.format_combo.setCurrentText(config.output_format)
        self.jpeg_quality_slider.setValue(config.jpeg_quality)
        self.on_jpeg_quality_changed()
        
        # 设置文件名规则
        if config.filename_rule == "original":
            self.filename_original.setChecked(True)
        elif config.filename_rule == "prefix":
            self.filename_prefix.setChecked(True)
        else:
            self.filename_suffix.setChecked(True)
        
        self.prefix_input.setText(config.filename_prefix)
        self.suffix_input.setText(config.filename_suffix)
        
        self.on_format_changed()
    
    def export_images(self):
        """导出图像"""
        if not self.image_processor.get_image_list():
            QMessageBox.warning(self, "警告", "请先导入图片文件")
            return
        
        # 选择输出文件夹
        output_folder = QFileDialog.getExistingDirectory(
            self, 
            "选择输出文件夹",
            self.config_manager.get_recent_output_folder() or ""
        )
        
        if not output_folder:
            return
        
        # 检查是否与源文件夹相同
        image_folders = set()
        for file_path in self.image_processor.get_image_list():
            image_folders.add(os.path.dirname(file_path))
        
        if output_folder in image_folders:
            reply = QMessageBox.question(
                self,
                "确认",
                "输出文件夹与源文件夹相同，可能会覆盖原文件。是否继续？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # 保存输出文件夹到配置
        self.config_manager.save_recent_output_folder(output_folder)
        
        # 获取当前配置并保存
        current_config = self.get_current_config()
        self.config_manager.current_config = current_config
        self.config_manager.save_config()
        
        # 开始导出
        self.export_btn.setEnabled(False)
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        
        # 创建导出线程
        self.export_thread = ExportThread(
            self.image_processor,
            self.image_processor.get_image_list(),
            output_folder,
            current_config
        )
        
        self.export_thread.progress.connect(self.progress_bar.setValue)
        self.export_thread.finished.connect(self.on_export_finished)
        self.export_thread.error.connect(self.on_export_error)
        
        self.export_thread.start()
        self.statusBar().showMessage("正在导出...")
    
    def on_export_finished(self, success_count, total_count):
        """导出完成"""
        self.export_btn.setEnabled(True)
        self.progress_bar.hide()
        
        if success_count == total_count:
            QMessageBox.information(
                self, 
                "完成", 
                f"成功导出 {success_count} 张图片"
            )
            self.statusBar().showMessage(f"导出完成: {success_count}/{total_count}")
        else:
            QMessageBox.warning(
                self, 
                "部分成功", 
                f"成功导出 {success_count}/{total_count} 张图片"
            )
            self.statusBar().showMessage(f"导出完成: {success_count}/{total_count}")
    
    def on_export_error(self, error_msg):
        """导出错误"""
        print(f"导出错误: {error_msg}")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 保存当前配置
        current_config = self.get_current_config()
        self.config_manager.current_config = current_config
        self.config_manager.save_config()
        
        event.accept()