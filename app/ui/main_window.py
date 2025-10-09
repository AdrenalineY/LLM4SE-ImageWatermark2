"""
主窗口UI模块
实现应用程序的主要用户界面和交互逻辑
"""

import os
from typing import Optional, List
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsTextItem, QGraphicsItem, QPushButton, 
    QLabel, QLineEdit, QSlider, QComboBox, QGroupBox, QGridLayout, 
    QFileDialog, QMessageBox, QProgressBar, QApplication, QFrame, 
    QScrollArea, QButtonGroup, QRadioButton, QSpinBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer, QRectF
from PyQt5.QtGui import QPixmap, QIcon, QFont, QPainter, QPen, QColor

from ..core.image_processor import ImageProcessor
from ..core.config_manager import ConfigManager, WatermarkConfig


class ImageListWidget(QListWidget):
    """自定义图像列表控件，支持拖拽"""
    
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setAcceptDrops(True)
        # 设置为接受拖拽模式，而不是内部移动模式
        self.setDragDropMode(QListWidget.DropOnly)
        
    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        try:
            if event.mimeData().hasUrls():
                # 检查是否有有效的文件URL
                urls = event.mimeData().urls()
                valid_files = []
                for url in urls:
                    file_path = url.toLocalFile()
                    if file_path and (os.path.isfile(file_path) or os.path.isdir(file_path)):
                        valid_files.append(file_path)
                
                if valid_files:
                    event.acceptProposedAction()
                    return
            
            event.ignore()
        except Exception as e:
            print(f"拖拽进入事件错误: {e}")
            event.ignore()
            
    def dragMoveEvent(self, event):
        """拖拽移动事件"""
        try:
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
            else:
                event.ignore()
        except Exception as e:
            print(f"拖拽移动事件错误: {e}")
            event.ignore()
            
    def dropEvent(self, event):
        """拖拽放下事件"""
        try:
            if event.mimeData().hasUrls():
                urls = event.mimeData().urls()
                files = [url.toLocalFile() for url in urls if url.toLocalFile()]
                
                if files:
                    print(f"收到拖拽文件: {files}")
                    self.main_window.load_dropped_files(files)
                    event.acceptProposedAction()
                    return
            
            event.ignore()
        except Exception as e:
            print(f"拖拽放下事件错误: {e}")
            event.ignore()


class DraggableWatermarkItem(QGraphicsTextItem):
    """可拖拽的水印文本项"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        
        # 设置样式
        self.setDefaultTextColor(QColor(255, 255, 255, 180))
        font = QFont()
        font.setPointSize(36)
        font.setBold(True)
        self.setFont(font)
        
        # 水印边界
        self.image_bounds = QRectF()
        
    def set_image_bounds(self, bounds: QRectF):
        """设置图像边界，限制水印移动范围"""
        self.image_bounds = bounds
        
    def itemChange(self, change, value):
        """项目变化时的处理"""
        if change == QGraphicsItem.ItemPositionChange and self.image_bounds.isValid():
            # 限制水印在图像范围内移动
            new_pos = value
            item_rect = self.boundingRect()
            
            # 计算限制后的位置
            if new_pos.x() < self.image_bounds.left():
                new_pos.setX(self.image_bounds.left())
            elif new_pos.x() + item_rect.width() > self.image_bounds.right():
                new_pos.setX(self.image_bounds.right() - item_rect.width())
                
            if new_pos.y() < self.image_bounds.top():
                new_pos.setY(self.image_bounds.top())
            elif new_pos.y() + item_rect.height() > self.image_bounds.bottom():
                new_pos.setY(self.image_bounds.bottom() - item_rect.height())
                
            return new_pos
            
        return super().itemChange(change, value)


class PreviewGraphicsView(QGraphicsView):
    """预览图像的GraphicsView，支持水印拖拽"""
    
    # 添加自定义信号
    watermark_position_changed = pyqtSignal(tuple)  # 发射新的水印位置 (x, y)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.NoDrag)  # 禁用默认拖拽，使用自定义拖拽
        
        # 当前显示的图像项和水印项
        self.image_item = None
        self.watermark_item = None
        
        # 图像原始尺寸（用于位置计算）
        self.original_image_size = (0, 0)
        
    def set_image(self, pixmap: QPixmap):
        """设置要显示的图像"""
        self.scene.clear()
        self.image_item = None  # 清空引用
        self.watermark_item = None
        
        if pixmap and not pixmap.isNull():
            self.image_item = QGraphicsPixmapItem(pixmap)
            self.scene.addItem(self.image_item)
            self.fitInView(self.image_item, Qt.KeepAspectRatio)
            
            # 记录原始图像尺寸
            self.original_image_size = (pixmap.width(), pixmap.height())
    
    def add_watermark_preview(self, text: str, font_size: int = 36, opacity: int = 180, position: tuple = None):
        """添加可拖拽的水印预览"""
        if not self.image_item:
            return
            
        # 移除旧的水印项
        if self.watermark_item:
            self.scene.removeItem(self.watermark_item)
            
        # 创建新的水印项
        self.watermark_item = DraggableWatermarkItem(text)
        
        # 设置字体和样式
        font = QFont()
        font.setPointSize(font_size)
        font.setBold(True)
        self.watermark_item.setFont(font)
        self.watermark_item.setDefaultTextColor(QColor(255, 255, 255, opacity))
        
        # 设置图像边界
        image_rect = self.image_item.boundingRect()
        self.watermark_item.set_image_bounds(image_rect)
        
        # 设置初始位置
        if position:
            # 将原始图像坐标转换为场景坐标
            scale_x = image_rect.width() / self.original_image_size[0]
            scale_y = image_rect.height() / self.original_image_size[1]
            scene_x = image_rect.left() + position[0] * scale_x
            scene_y = image_rect.top() + position[1] * scale_y
            self.watermark_item.setPos(scene_x, scene_y)
        else:
            # 默认位置：右下角
            watermark_rect = self.watermark_item.boundingRect()
            default_x = image_rect.right() - watermark_rect.width() - 20
            default_y = image_rect.bottom() - watermark_rect.height() - 20
            self.watermark_item.setPos(default_x, default_y)
        
        # 添加到场景
        self.scene.addItem(self.watermark_item)
        
        # 连接位置变化信号
        self.watermark_item.itemChange = self._on_watermark_position_change
        
    def _on_watermark_position_change(self, change, value):
        """水印位置变化处理"""
        result = DraggableWatermarkItem.itemChange(self.watermark_item, change, value)
        
        if change == QGraphicsItem.ItemPositionHasChanged and self.image_item:
            # 将场景坐标转换回原始图像坐标
            image_rect = self.image_item.boundingRect()
            scene_pos = self.watermark_item.pos()
            
            # 计算相对于图像的位置
            relative_x = scene_pos.x() - image_rect.left()
            relative_y = scene_pos.y() - image_rect.top()
            
            # 转换为原始图像坐标
            scale_x = self.original_image_size[0] / image_rect.width()
            scale_y = self.original_image_size[1] / image_rect.height()
            
            original_x = int(relative_x * scale_x)
            original_y = int(relative_y * scale_y)
            
            # 发射位置变化信号
            self.watermark_position_changed.emit((original_x, original_y))
            
        return result
    
    def get_watermark_position(self):
        """获取当前水印在原始图像中的位置"""
        if not self.watermark_item or not self.image_item:
            return None
            
        image_rect = self.image_item.boundingRect()
        scene_pos = self.watermark_item.pos()
        
        # 计算相对于图像的位置
        relative_x = scene_pos.x() - image_rect.left()
        relative_y = scene_pos.y() - image_rect.top()
        
        # 转换为原始图像坐标
        scale_x = self.original_image_size[0] / image_rect.width()
        scale_y = self.original_image_size[1] / image_rect.height()
        
        original_x = int(relative_x * scale_x)
        original_y = int(relative_y * scale_y)
        
        return (original_x, original_y)
    
    def resizeEvent(self, event):
        """窗口大小改变时重新调整图像"""
        super().resizeEvent(event)
        if self.image_item and self.image_item.scene():
            self.fitInView(self.image_item, Qt.KeepAspectRatio)
            
            # 重新调整水印边界
            if self.watermark_item:
                image_rect = self.image_item.boundingRect()
                self.watermark_item.set_image_bounds(image_rect)


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
        
        # 启用主窗口的拖拽支持
        self.setAcceptDrops(True)
        
        # 初始化核心组件
        self.image_processor = ImageProcessor()
        self.config_manager = ConfigManager()
        
        # 当前水印预览
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.update_preview)
        
        # 自定义位置跟踪
        self.custom_watermark_position = None
        self.use_custom_position = False
        
        # 设置界面
        self.setup_ui()
        self.connect_signals()
        
        # 初始化模板列表
        self.refresh_template_list()
        
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
        self.image_list.setIconSize(QSize(100, 100))
        self.image_list.setResizeMode(QListWidget.Adjust)
        self.image_list.setViewMode(QListWidget.IconMode)
        self.image_list.setMovement(QListWidget.Static)
        self.image_list.setSpacing(5)
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
        
        # 模板管理组
        self.setup_template_group(scroll_layout)
        
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
        
    def setup_template_group(self, parent_layout):
        """设置模板管理组"""
        template_group = QGroupBox("配置模板")
        template_layout = QVBoxLayout(template_group)
        
        # 模板选择下拉框
        template_select_layout = QHBoxLayout()
        template_select_layout.addWidget(QLabel("选择模板:"))
        self.template_combo = QComboBox()
        self.template_combo.setMinimumWidth(120)
        template_select_layout.addWidget(self.template_combo)
        template_layout.addLayout(template_select_layout)
        
        # 模板操作按钮
        template_buttons_layout = QHBoxLayout()
        
        self.load_template_btn = QPushButton("加载")
        self.load_template_btn.setMaximumWidth(60)
        template_buttons_layout.addWidget(self.load_template_btn)
        
        self.save_template_btn = QPushButton("保存为模板")
        template_buttons_layout.addWidget(self.save_template_btn)
        
        self.delete_template_btn = QPushButton("删除")
        self.delete_template_btn.setMaximumWidth(60)
        template_buttons_layout.addWidget(self.delete_template_btn)
        
        template_layout.addLayout(template_buttons_layout)
        
        # 重置按钮
        reset_layout = QHBoxLayout()
        self.reset_config_btn = QPushButton("重置为默认设置")
        reset_layout.addWidget(self.reset_config_btn)
        template_layout.addLayout(reset_layout)
        
        parent_layout.addWidget(template_group)
        
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
        
        # 文件名规则设置
        self.filename_original.toggled.connect(self.on_filename_rule_changed)
        self.filename_prefix.toggled.connect(self.on_filename_rule_changed)
        self.filename_suffix.toggled.connect(self.on_filename_rule_changed)
        
        # 预览视图水印拖拽
        self.preview_view.watermark_position_changed.connect(self.on_watermark_position_changed)
        
        # 模板管理
        self.load_template_btn.clicked.connect(self.load_template)
        self.save_template_btn.clicked.connect(self.save_template)
        self.delete_template_btn.clicked.connect(self.delete_template)
        self.reset_config_btn.clicked.connect(self.reset_config)
        self.template_combo.currentTextChanged.connect(self.on_template_selection_changed)
        
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
        # 如果是位置按钮触发的变化，重置自定义位置
        sender = self.sender()
        if sender in self.position_buttons.buttons():
            self.use_custom_position = False
            self.custom_watermark_position = None
        
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
    
    def on_filename_rule_changed(self):
        """文件名规则改变事件"""
        # 根据选择的规则启用/禁用对应的输入框
        if self.filename_original.isChecked():
            # 保持原名 - 禁用所有输入框
            self.prefix_input.setEnabled(False)
            self.suffix_input.setEnabled(False)
        elif self.filename_prefix.isChecked():
            # 添加前缀 - 只启用前缀输入框
            self.prefix_input.setEnabled(True)
            self.suffix_input.setEnabled(False)
            # 将焦点设置到前缀输入框
            self.prefix_input.setFocus()
        elif self.filename_suffix.isChecked():
            # 添加后缀 - 只启用后缀输入框
            self.prefix_input.setEnabled(False)
            self.suffix_input.setEnabled(True)
            # 将焦点设置到后缀输入框
            self.suffix_input.setFocus()
    
    def on_watermark_position_changed(self, position):
        """水印位置变化事件"""
        # 更新自定义位置
        self.custom_watermark_position = position
        self.use_custom_position = True
        
        # 取消位置按钮的选择（因为现在是自定义位置）
        for button in self.position_buttons.buttons():
            button.setChecked(False)
        
        print(f"水印位置已更新为: {position}")  # 调试信息
    
    def refresh_template_list(self):
        """刷新模板列表"""
        self.template_combo.clear()
        template_names = self.config_manager.get_template_names()
        if template_names:
            self.template_combo.addItems(template_names)
        
        # 更新按钮状态
        has_templates = len(template_names) > 0
        self.load_template_btn.setEnabled(has_templates)
        self.delete_template_btn.setEnabled(has_templates)
    
    def load_template(self):
        """加载选中的模板（显式加载，带确认提示）"""
        template_name = self.template_combo.currentText()
        if not template_name:
            QMessageBox.warning(self, "警告", "请选择要加载的模板")
            return
        
        # 显式加载时提供确认提示
        if self.config_manager.load_template(template_name):
            self.load_config_to_ui_silent()  # 静默加载，不触发预览更新
            self.update_preview()
            self.statusBar().showMessage(f"已加载模板: {template_name}")
            QMessageBox.information(self, "成功", f"模板 '{template_name}' 已成功加载！")
        else:
            QMessageBox.critical(self, "错误", f"加载模板失败: {template_name}")
    
    def save_template(self):
        """保存当前设置为模板"""
        from PyQt5.QtWidgets import QInputDialog
        
        template_name, ok = QInputDialog.getText(
            self, "保存模板", "请输入模板名称:", 
            text="我的水印模板"
        )
        
        if ok and template_name.strip():
            template_name = template_name.strip()
            
            # 检查模板是否已存在
            existing_templates = self.config_manager.get_template_names()
            if template_name in existing_templates:
                reply = QMessageBox.question(
                    self, "确认覆盖", 
                    f"模板 '{template_name}' 已存在，是否覆盖？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
            
            # 获取当前配置并保存为模板
            current_config = self.get_current_config()
            if self.config_manager.save_template(template_name, current_config):
                self.refresh_template_list()
                self.template_combo.setCurrentText(template_name)
                self.statusBar().showMessage(f"已保存模板: {template_name}")
                QMessageBox.information(self, "成功", f"模板 '{template_name}' 保存成功！")
            else:
                QMessageBox.critical(self, "错误", f"保存模板失败: {template_name}")
    
    def delete_template(self):
        """删除选中的模板"""
        template_name = self.template_combo.currentText()
        if not template_name:
            QMessageBox.warning(self, "警告", "请选择要删除的模板")
            return
        
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除模板 '{template_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.config_manager.delete_template(template_name):
                self.refresh_template_list()
                self.statusBar().showMessage(f"已删除模板: {template_name}")
                QMessageBox.information(self, "成功", f"模板 '{template_name}' 删除成功！")
            else:
                QMessageBox.critical(self, "错误", f"删除模板失败: {template_name}")
    
    def reset_config(self):
        """重置为默认配置"""
        reply = QMessageBox.question(
            self, "确认重置", 
            "确定要重置为默认设置吗？所有当前设置将被清除。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.config_manager.reset_to_default()
            self.use_custom_position = False
            self.custom_watermark_position = None
            self.load_config_to_ui_silent()
            self.update_preview()
            self.statusBar().showMessage("已重置为默认设置")
            QMessageBox.information(self, "成功", "已重置为默认设置")
    
    def refresh_template_list(self):
        """刷新模板列表"""
        # 保存当前选择
        current_selection = self.template_combo.currentText()
        
        # 临时阻塞信号，避免在重新填充时触发模板加载
        self.template_combo.blockSignals(True)
        
        try:
            # 清空并重新填充
            self.template_combo.clear()
            templates = self.config_manager.get_template_names()
            
            if templates:
                self.template_combo.addItems(templates)
                # 尝试恢复之前的选择
                if current_selection in templates:
                    index = self.template_combo.findText(current_selection)
                    if index >= 0:
                        self.template_combo.setCurrentIndex(index)
        finally:
            # 恢复信号
            self.template_combo.blockSignals(False)
        
        # 手动触发模板选择变化事件，确保当前选择的模板被加载
        self.on_template_selection_changed(self.template_combo.currentText())
    
    def on_template_selection_changed(self, template_name):
        """模板选择变化事件 - 自动加载选中的模板"""
        # 更新按钮状态
        has_selection = bool(template_name)
        self.load_template_btn.setEnabled(has_selection)
        self.delete_template_btn.setEnabled(has_selection)
        
        # 自动加载选中的模板（如果有选择的话）
        if template_name and template_name.strip():
            if self.config_manager.load_template(template_name):
                self.load_config_to_ui_silent()  # 静默加载，不触发预览更新
                self.update_preview()
                self.statusBar().showMessage(f"已自动加载模板: {template_name}")
            else:
                self.statusBar().showMessage(f"加载模板失败: {template_name}")
        else:
            # 如果没有选择模板，清空状态栏消息
            self.statusBar().clearMessage()
    
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
        
        # 显示原始图像（不添加水印）
        pixmap = self.image_processor.pil_to_qpixmap(current_image)
        self.preview_view.set_image(pixmap)
        
        # 添加可拖拽的水印预览
        if config.text.strip():  # 只有在有文本时才显示水印
            self.preview_view.add_watermark_preview(
                config.text,
                config.font_size,
                config.opacity,
                position
            )
    
    def get_current_config(self) -> WatermarkConfig:
        """获取当前UI配置"""
        config = WatermarkConfig()
        
        # 水印设置
        config.text = self.watermark_text.text()
        config.font_size = self.font_size_spin.value()
        config.opacity = self.opacity_slider.value()
        
        # 位置设置
        if self.use_custom_position and self.custom_watermark_position:
            config.use_custom_position = True
            config.custom_position = self.custom_watermark_position
        else:
            config.use_custom_position = False
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
        
        # 处理自定义位置
        if config.use_custom_position and config.custom_position:
            # 加载自定义位置
            self.use_custom_position = True
            self.custom_watermark_position = config.custom_position
            # 取消所有位置按钮的选择
            for button in self.position_buttons.buttons():
                button.setChecked(False)
        else:
            # 使用九宫格位置
            self.use_custom_position = False
            self.custom_watermark_position = None
        
        # 初始化文件名规则状态
        self.on_filename_rule_changed()
        
        self.on_format_changed()
    
    def load_config_to_ui_silent(self):
        """静默加载配置到UI（不触发信号和预览更新）"""
        config = self.config_manager.get_config()
        
        # 临时阻塞信号
        self.watermark_text.blockSignals(True)
        self.font_size_spin.blockSignals(True)
        self.opacity_slider.blockSignals(True)
        self.format_combo.blockSignals(True)
        self.jpeg_quality_slider.blockSignals(True)
        self.prefix_input.blockSignals(True)
        self.suffix_input.blockSignals(True)
        
        try:
            # 设置水印配置
            self.watermark_text.setText(config.text)
            self.font_size_spin.setValue(config.font_size)
            self.opacity_slider.setValue(config.opacity)
            
            # 设置位置
            for button in self.position_buttons.buttons():
                button.blockSignals(True)
                if button.property("position") == config.position_type:
                    button.setChecked(True)
                else:
                    button.setChecked(False)
                button.blockSignals(False)
            
            # 设置导出配置
            self.format_combo.setCurrentText(config.output_format)
            self.jpeg_quality_slider.setValue(config.jpeg_quality)
            
            # 设置文件名规则
            self.filename_original.blockSignals(True)
            self.filename_prefix.blockSignals(True)
            self.filename_suffix.blockSignals(True)
            
            if config.filename_rule == "original":
                self.filename_original.setChecked(True)
                self.filename_prefix.setChecked(False)
                self.filename_suffix.setChecked(False)
            elif config.filename_rule == "prefix":
                self.filename_original.setChecked(False)
                self.filename_prefix.setChecked(True)
                self.filename_suffix.setChecked(False)
            else:
                self.filename_original.setChecked(False)
                self.filename_prefix.setChecked(False)
                self.filename_suffix.setChecked(True)
            
            self.filename_original.blockSignals(False)
            self.filename_prefix.blockSignals(False)
            self.filename_suffix.blockSignals(False)
            
            self.prefix_input.setText(config.filename_prefix)
            self.suffix_input.setText(config.filename_suffix)
            
            # 处理自定义位置
            if config.use_custom_position and config.custom_position:
                # 加载自定义位置
                self.use_custom_position = True
                self.custom_watermark_position = config.custom_position
                # 取消所有位置按钮的选择
                for button in self.position_buttons.buttons():
                    button.blockSignals(True)
                    button.setChecked(False)
                    button.blockSignals(False)
            else:
                # 使用九宫格位置
                self.use_custom_position = False
                self.custom_watermark_position = None
            
            # 更新UI状态
            self.on_filename_rule_changed()
            self.on_format_changed()
            self.on_opacity_changed()
            self.on_jpeg_quality_changed()
            
        finally:
            # 恢复信号
            self.watermark_text.blockSignals(False)
            self.font_size_spin.blockSignals(False)
            self.opacity_slider.blockSignals(False)
            self.format_combo.blockSignals(False)
            self.jpeg_quality_slider.blockSignals(False)
            self.prefix_input.blockSignals(False)
            self.suffix_input.blockSignals(False)
    
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
    
    def dragEnterEvent(self, event):
        """主窗口拖拽进入事件"""
        try:
            if event.mimeData().hasUrls():
                # 检查是否有有效的文件URL
                urls = event.mimeData().urls()
                valid_files = []
                for url in urls:
                    file_path = url.toLocalFile()
                    if file_path and (os.path.isfile(file_path) or os.path.isdir(file_path)):
                        valid_files.append(file_path)
                
                if valid_files:
                    print(f"主窗口接受拖拽: {valid_files}")
                    event.acceptProposedAction()
                    return
            
            event.ignore()
        except Exception as e:
            print(f"主窗口拖拽进入事件错误: {e}")
            event.ignore()
    
    def dragMoveEvent(self, event):
        """主窗口拖拽移动事件"""
        try:
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
            else:
                event.ignore()
        except Exception as e:
            print(f"主窗口拖拽移动事件错误: {e}")
            event.ignore()
    
    def dropEvent(self, event):
        """主窗口拖拽放下事件"""
        try:
            if event.mimeData().hasUrls():
                urls = event.mimeData().urls()
                files = [url.toLocalFile() for url in urls if url.toLocalFile()]
                
                if files:
                    print(f"主窗口收到拖拽文件: {files}")
                    self.load_dropped_files(files)
                    event.acceptProposedAction()
                    return
            
            event.ignore()
        except Exception as e:
            print(f"主窗口拖拽放下事件错误: {e}")
            event.ignore()