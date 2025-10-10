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
    QScrollArea, QButtonGroup, QRadioButton, QSpinBox, QFontComboBox,
    QColorDialog, QCheckBox, QTabWidget, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer, QRectF, QPointF
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
            half_w = item_rect.width() / 2
            half_h = item_rect.height() / 2

            center_x = new_pos.x() + half_w
            center_y = new_pos.y() + half_h

            left_limit = self.image_bounds.left() + half_w
            right_limit = self.image_bounds.right() - half_w
            top_limit = self.image_bounds.top() + half_h
            bottom_limit = self.image_bounds.bottom() - half_h

            if left_limit > right_limit:
                left_limit = right_limit = (self.image_bounds.left() + self.image_bounds.right()) / 2
            if top_limit > bottom_limit:
                top_limit = bottom_limit = (self.image_bounds.top() + self.image_bounds.bottom()) / 2

            if center_x < left_limit:
                new_pos.setX(left_limit - half_w)
            elif center_x > right_limit:
                new_pos.setX(right_limit - half_w)

            if center_y < top_limit:
                new_pos.setY(top_limit - half_h)
            elif center_y > bottom_limit:
                new_pos.setY(bottom_limit - half_h)
                
            return new_pos
            
        return super().itemChange(change, value)


class DraggablePixmapItem(QGraphicsPixmapItem):
    """可拖拽的水印图片项"""

    def __init__(self, pixmap=None, parent=None):
        super().__init__(pixmap, parent)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.image_bounds = QRectF()

    def set_image_bounds(self, bounds: QRectF):
        self.image_bounds = bounds

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.image_bounds.isValid():
            new_pos = value
            item_rect = self.boundingRect()
            half_w = item_rect.width() / 2
            half_h = item_rect.height() / 2

            center_x = new_pos.x() + half_w
            center_y = new_pos.y() + half_h

            left_limit = self.image_bounds.left() + half_w
            right_limit = self.image_bounds.right() - half_w
            top_limit = self.image_bounds.top() + half_h
            bottom_limit = self.image_bounds.bottom() - half_h

            if left_limit > right_limit:
                left_limit = right_limit = (self.image_bounds.left() + self.image_bounds.right()) / 2
            if top_limit > bottom_limit:
                top_limit = bottom_limit = (self.image_bounds.top() + self.image_bounds.bottom()) / 2

            if center_x < left_limit:
                new_pos.setX(left_limit - half_w)
            elif center_x > right_limit:
                new_pos.setX(right_limit - half_w)

            if center_y < top_limit:
                new_pos.setY(top_limit - half_h)
            elif center_y > bottom_limit:
                new_pos.setY(bottom_limit - half_h)

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
        self._suspend_position_emission = False
        
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
    
    def add_watermark_preview(self, text: str = None, font: QFont = None,
                              color: QColor = None, opacity: int = 180,
                              position: tuple = None, rotation: int = 0,
                              pixmap: QPixmap = None) -> None:
        """添加可拖拽的水印预览（文本或图片）"""
        if not self.image_item:
            return

        # 移除旧的水印项
        if self.watermark_item:
            self.scene.removeItem(self.watermark_item)
            self.watermark_item = None

        image_rect = self.image_item.boundingRect()
        self._suspend_position_emission = True

        if pixmap is not None:
            self.watermark_item = DraggablePixmapItem(pixmap)
            self.watermark_item.setOpacity(opacity / 255.0)
        else:
            display_text = text or ""
            self.watermark_item = DraggableWatermarkItem(display_text)
            if font:
                self.watermark_item.setFont(font)
            if color:
                qcolor = QColor(color)
                qcolor.setAlpha(opacity)
                self.watermark_item.setDefaultTextColor(qcolor)
            else:
                self.watermark_item.setDefaultTextColor(QColor(255, 255, 255, opacity))

        self.watermark_item.set_image_bounds(image_rect)

        # 计算期望中心点
        if position:
            scale_x = image_rect.width() / self.original_image_size[0]
            scale_y = image_rect.height() / self.original_image_size[1]
            desired_center = QPointF(
                image_rect.left() + position[0] * scale_x,
                image_rect.top() + position[1] * scale_y
            )
        else:
            desired_center = image_rect.center()

        # 设置旋转中心并同步角度（逆时针为正）
        bounds = self.watermark_item.boundingRect()
        center_local = bounds.center()
        self.watermark_item.setTransformOriginPoint(center_local)
        setattr(self.watermark_item, "_ignore_next_bound", True)
        self.watermark_item.setRotation(-rotation)
        self.watermark_item.setPos(
            desired_center.x() - center_local.x(),
            desired_center.y() - center_local.y()
        )

        # 文本阴影效果
        if isinstance(self.watermark_item, DraggableWatermarkItem):
            effect = getattr(self.watermark_item, "_shadow_effect", None)
            if effect:
                self.watermark_item.setGraphicsEffect(None)

        # 添加到场景
        self.scene.addItem(self.watermark_item)

        original_item_change = self.watermark_item.itemChange

        def handler(change, value, original_handler=original_item_change):
            return self._on_watermark_position_change(change, value, original_handler)

        self.watermark_item.itemChange = handler
        QTimer.singleShot(0, self._resume_position_emission)
        
    def _on_watermark_position_change(self, change, value, original_handler):
        """水印位置变化处理"""
        if change == QGraphicsItem.ItemPositionChange and getattr(self.watermark_item, "_ignore_next_bound", False):
            setattr(self.watermark_item, "_ignore_next_bound", False)
            return value

        result = original_handler(change, value)
        
        if change == QGraphicsItem.ItemPositionHasChanged and self.image_item:
            if self._suspend_position_emission:
                return result
            # 将场景坐标转换回原始图像坐标
            image_rect = self.image_item.boundingRect()
            scene_rect = self.watermark_item.mapRectToScene(self.watermark_item.boundingRect())
            center_scene = scene_rect.center()

            relative_x = center_scene.x() - image_rect.left()
            relative_y = center_scene.y() - image_rect.top()

            scale_x = self.original_image_size[0] / image_rect.width()
            scale_y = self.original_image_size[1] / image_rect.height()

            original_x = int(round(relative_x * scale_x))
            original_y = int(round(relative_y * scale_y))

            # 发射位置变化信号
            self.watermark_position_changed.emit((original_x, original_y))
            
        return result

    def _resume_position_emission(self):
        self._suspend_position_emission = False
    
    def get_watermark_position(self):
        """获取当前水印在原始图像中的位置"""
        if not self.watermark_item or not self.image_item:
            return None
            
        image_rect = self.image_item.boundingRect()
        scene_rect = self.watermark_item.mapRectToScene(self.watermark_item.boundingRect())
        center_scene = scene_rect.center()

        relative_x = center_scene.x() - image_rect.left()
        relative_y = center_scene.y() - image_rect.top()

        scale_x = self.original_image_size[0] / image_rect.width()
        scale_y = self.original_image_size[1] / image_rect.height()

        original_x = int(round(relative_x * scale_x))
        original_y = int(round(relative_y * scale_y))

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
                
                # 创建带水印的图像（包含尺寸调整）
                source_image = self.processor.images.get(file_path)
                if source_image is None:
                    raise ValueError("源图像不可用")

                watermarked_image = self.processor.apply_watermark(
                    source_image,
                    self.config
                )

                # 保存图像
                if self.config.output_format.upper() == "JPEG":
                    image_to_save = watermarked_image
                    if image_to_save.mode != 'RGB':
                        image_to_save = image_to_save.convert('RGB')
                    image_to_save.save(
                        output_path,
                        format="JPEG",
                        quality=self.config.jpeg_quality
                    )
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
        self._suppress_watermark_position_signal = False
        self._pending_preset_position = False
        self.text_color = QColor(255, 255, 255)
        self.stroke_color = QColor(0, 0, 0)
        self.shadow_offset = (2, 2)
        self.current_watermark_type = "text"
        self.image_watermark_path = ""
        
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

        self.watermark_tabs = QTabWidget()

        self.text_watermark_tab = QWidget()
        self.setup_text_watermark_tab(self.text_watermark_tab)
        self.watermark_tabs.addTab(self.text_watermark_tab, "文本水印")

        self.image_watermark_tab = QWidget()
        self.setup_image_watermark_tab(self.image_watermark_tab)
        self.watermark_tabs.addTab(self.image_watermark_tab, "图片水印")

        watermark_layout.addWidget(self.watermark_tabs)

        rotation_layout = QHBoxLayout()
        rotation_layout.addWidget(QLabel("旋转角度 (逆时针为正):"))
        self.rotation_slider = QSlider(Qt.Horizontal)
        self.rotation_slider.setRange(-180, 180)
        self.rotation_slider.setValue(0)
        rotation_layout.addWidget(self.rotation_slider)
        self.rotation_spin = QSpinBox()
        self.rotation_spin.setRange(-180, 180)
        self.rotation_spin.setValue(0)
        self.rotation_spin.setFixedWidth(60)
        rotation_layout.addWidget(self.rotation_spin)
        self.rotation_label = QLabel("0°")
        self.rotation_label.setFixedWidth(50)
        rotation_layout.addWidget(self.rotation_label)
        watermark_layout.addLayout(rotation_layout)

        position_group = QGroupBox("位置设置")
        position_layout = QGridLayout(position_group)

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

    def setup_text_watermark_tab(self, widget):
        layout = QVBoxLayout(widget)

        text_layout = QHBoxLayout()
        text_layout.addWidget(QLabel("水印文字:"))
        self.watermark_text = QLineEdit("Sample Watermark")
        text_layout.addWidget(self.watermark_text)
        layout.addLayout(text_layout)

        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("字体:"))
        self.font_combo = QFontComboBox()
        font_row.addWidget(self.font_combo)

        font_row.addWidget(QLabel("大小:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(12, 200)
        self.font_size_spin.setValue(36)
        font_row.addWidget(self.font_size_spin)
        layout.addLayout(font_row)

        style_layout = QHBoxLayout()
        self.bold_btn = QPushButton("粗体")
        self.bold_btn.setCheckable(True)
        self.bold_btn.setChecked(True)
        style_layout.addWidget(self.bold_btn)

        self.italic_btn = QPushButton("斜体")
        self.italic_btn.setCheckable(True)
        style_layout.addWidget(self.italic_btn)
        layout.addLayout(style_layout)

        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("文字颜色:"))
        self.text_color_btn = QPushButton()
        self.text_color_btn.setFixedSize(36, 24)
        self._update_color_button(self.text_color_btn, self.text_color)
        color_layout.addWidget(self.text_color_btn)

        color_layout.addWidget(QLabel("描边颜色:"))
        self.stroke_color_btn = QPushButton()
        self.stroke_color_btn.setFixedSize(36, 24)
        self._update_color_button(self.stroke_color_btn, self.stroke_color)
        color_layout.addWidget(self.stroke_color_btn)
        layout.addLayout(color_layout)

        effect_layout = QGridLayout()
        self.shadow_check = QCheckBox("启用阴影")
        effect_layout.addWidget(self.shadow_check, 0, 0, 1, 2)
        effect_layout.addWidget(QLabel("阴影偏移X:"), 1, 0)
        self.shadow_offset_x_spin = QSpinBox()
        self.shadow_offset_x_spin.setRange(-50, 50)
        self.shadow_offset_x_spin.setValue(self.shadow_offset[0])
        effect_layout.addWidget(self.shadow_offset_x_spin, 1, 1)
        effect_layout.addWidget(QLabel("阴影偏移Y:"), 1, 2)
        self.shadow_offset_y_spin = QSpinBox()
        self.shadow_offset_y_spin.setRange(-50, 50)
        self.shadow_offset_y_spin.setValue(self.shadow_offset[1])
        effect_layout.addWidget(self.shadow_offset_y_spin, 1, 3)

        self.stroke_check = QCheckBox("启用描边")
        effect_layout.addWidget(self.stroke_check, 2, 0, 1, 2)
        effect_layout.addWidget(QLabel("描边宽度:"), 2, 2)
        self.stroke_width_spin = QSpinBox()
        self.stroke_width_spin.setRange(0, 10)
        self.stroke_width_spin.setValue(1)
        effect_layout.addWidget(self.stroke_width_spin, 2, 3)

        layout.addLayout(effect_layout)

        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("透明度:"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 255)
        self.opacity_slider.setValue(128)
        opacity_layout.addWidget(self.opacity_slider)
        self.opacity_label = QLabel("50%")
        self.opacity_label.setFixedWidth(50)
        opacity_layout.addWidget(self.opacity_label)
        layout.addLayout(opacity_layout)
        layout.addStretch()

    def setup_image_watermark_tab(self, widget):
        layout = QVBoxLayout(widget)

        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("水印图片:"))
        self.image_path_edit = QLineEdit()
        self.image_path_edit.setReadOnly(True)
        path_layout.addWidget(self.image_path_edit)
        self.image_select_btn = QPushButton("选择图片")
        path_layout.addWidget(self.image_select_btn)
        layout.addLayout(path_layout)

        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("缩放比例:"))
        self.image_scale_slider = QSlider(Qt.Horizontal)
        self.image_scale_slider.setRange(10, 300)
        self.image_scale_slider.setValue(100)
        scale_layout.addWidget(self.image_scale_slider)
        self.image_scale_label = QLabel("100%")
        self.image_scale_label.setFixedWidth(60)
        scale_layout.addWidget(self.image_scale_label)
        self._update_image_scale_label(self.image_scale_slider.value())
        layout.addLayout(scale_layout)

        image_opacity_layout = QHBoxLayout()
        image_opacity_layout.addWidget(QLabel("透明度:"))
        self.image_opacity_slider = QSlider(Qt.Horizontal)
        self.image_opacity_slider.setRange(0, 255)
        self.image_opacity_slider.setValue(180)
        image_opacity_layout.addWidget(self.image_opacity_slider)
        self.image_opacity_label = QLabel("71%")
        self.image_opacity_label.setFixedWidth(60)
        image_opacity_layout.addWidget(self.image_opacity_label)
        self._update_image_opacity_label(self.image_opacity_slider.value())
        layout.addLayout(image_opacity_layout)

        layout.addStretch()
        
    def _update_color_button(self, button: QPushButton, color) -> None:
        if not isinstance(color, QColor):
            if isinstance(color, tuple) and len(color) >= 3:
                color = QColor(color[0], color[1], color[2])
            else:
                color = QColor(0, 0, 0)
        rgba = f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha() if color.alpha() else 255})"
        button.setStyleSheet(
            "QPushButton {"
            f"background-color: {rgba};"
            "border: 1px solid #666;"
            "border-radius: 4px;"
            "}"
        )

    def _update_image_scale_label(self, value: int) -> None:
        self.image_scale_label.setText(f"{value}%")

    def _update_image_opacity_label(self, value: int) -> None:
        percent = int(value * 100 / 255) if value <= 255 else 100
        self.image_opacity_label.setText(f"{percent}%")

    def _update_rotation_label(self, value: int) -> None:
        self.rotation_label.setText(f"{value}°")

    def _current_resize_method(self) -> str:
        if hasattr(self, "resize_width_radio") and self.resize_width_radio.isChecked():
            return "width"
        if hasattr(self, "resize_height_radio") and self.resize_height_radio.isChecked():
            return "height"
        return "percentage"

    def _update_resize_controls(self) -> None:
        enabled = self.resize_check.isChecked()
        method = self._current_resize_method() if enabled else None

        control_widgets = [
            self.resize_width_radio,
            self.resize_height_radio,
            self.resize_percent_radio,
            self.resize_width_spin,
            self.resize_height_spin,
            self.resize_percent_spin,
            self.keep_aspect_check
        ]

        for widget in control_widgets:
            widget.setEnabled(enabled)

        if not enabled:
            return

        percentage_enabled = method == "percentage"
        width_enabled = method == "width"
        height_enabled = method == "height"

        self.resize_percent_spin.setEnabled(percentage_enabled)

        keep_aspect_applicable = width_enabled or height_enabled
        self.keep_aspect_check.setEnabled(keep_aspect_applicable)

        if percentage_enabled:
            self.resize_width_spin.setEnabled(False)
            self.resize_height_spin.setEnabled(False)
            return

        keep_aspect = self.keep_aspect_check.isChecked() if keep_aspect_applicable else True

        self.resize_width_spin.setEnabled(width_enabled or (not keep_aspect and height_enabled))
        self.resize_height_spin.setEnabled(height_enabled or (not keep_aspect and width_enabled))

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

        resize_group = QGroupBox("尺寸调整")
        resize_layout = QVBoxLayout(resize_group)

        self.resize_check = QCheckBox("启用尺寸调整")
        resize_layout.addWidget(self.resize_check)

        method_layout = QHBoxLayout()
        self.resize_width_radio = QRadioButton("按宽度")
        self.resize_height_radio = QRadioButton("按高度")
        self.resize_percent_radio = QRadioButton("按百分比")
        self.resize_percent_radio.setChecked(True)
        method_layout.addWidget(self.resize_width_radio)
        method_layout.addWidget(self.resize_height_radio)
        method_layout.addWidget(self.resize_percent_radio)
        resize_layout.addLayout(method_layout)

        resize_params_layout = QGridLayout()
        resize_params_layout.addWidget(QLabel("宽度(px):"), 0, 0)
        self.resize_width_spin = QSpinBox()
        self.resize_width_spin.setRange(10, 10000)
        self.resize_width_spin.setValue(1920)
        resize_params_layout.addWidget(self.resize_width_spin, 0, 1)

        resize_params_layout.addWidget(QLabel("高度(px):"), 0, 2)
        self.resize_height_spin = QSpinBox()
        self.resize_height_spin.setRange(10, 10000)
        self.resize_height_spin.setValue(1080)
        resize_params_layout.addWidget(self.resize_height_spin, 0, 3)

        resize_params_layout.addWidget(QLabel("百分比(%):"), 1, 0)
        self.resize_percent_spin = QSpinBox()
        self.resize_percent_spin.setRange(10, 400)
        self.resize_percent_spin.setValue(100)
        resize_params_layout.addWidget(self.resize_percent_spin, 1, 1)

        self.keep_aspect_check = QCheckBox("保持宽高比")
        self.keep_aspect_check.setChecked(True)
        resize_params_layout.addWidget(self.keep_aspect_check, 1, 2, 1, 2)
        resize_layout.addLayout(resize_params_layout)

        export_layout.addWidget(resize_group)
        self._update_resize_controls()
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
        self.position_buttons.buttonClicked.connect(self.on_position_button_clicked)
        self.font_combo.currentFontChanged.connect(self.on_watermark_changed)
        self.bold_btn.toggled.connect(self.on_watermark_changed)
        self.italic_btn.toggled.connect(self.on_watermark_changed)
        self.text_color_btn.clicked.connect(self.on_choose_text_color)
        self.stroke_color_btn.clicked.connect(self.on_choose_stroke_color)
        self.shadow_check.toggled.connect(self.on_watermark_changed)
        self.shadow_offset_x_spin.valueChanged.connect(self.on_shadow_offset_changed)
        self.shadow_offset_y_spin.valueChanged.connect(self.on_shadow_offset_changed)
        self.stroke_check.toggled.connect(self.on_watermark_changed)
        self.stroke_width_spin.valueChanged.connect(self.on_watermark_changed)
        self.rotation_slider.valueChanged.connect(self.on_rotation_changed)
        self.rotation_spin.valueChanged.connect(self.on_rotation_spin_changed)
        self.watermark_tabs.currentChanged.connect(self.on_watermark_tab_changed)
        self.image_select_btn.clicked.connect(self.on_choose_image_watermark)
        self.image_scale_slider.valueChanged.connect(self.on_image_scale_changed)
        self.image_opacity_slider.valueChanged.connect(self.on_image_opacity_changed)
        
        # 导出设置
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        self.jpeg_quality_slider.valueChanged.connect(self.on_jpeg_quality_changed)
        
        # 文件名规则设置
        self.filename_original.toggled.connect(self.on_filename_rule_changed)
        self.filename_prefix.toggled.connect(self.on_filename_rule_changed)
        self.filename_suffix.toggled.connect(self.on_filename_rule_changed)

        # 尺寸调整设置
        self.resize_check.toggled.connect(self.on_resize_settings_changed)
        self.resize_width_radio.toggled.connect(self.on_resize_settings_changed)
        self.resize_height_radio.toggled.connect(self.on_resize_settings_changed)
        self.resize_percent_radio.toggled.connect(self.on_resize_settings_changed)
        self.keep_aspect_check.toggled.connect(self.on_resize_settings_changed)
        self.resize_width_spin.valueChanged.connect(self.on_resize_settings_changed)
        self.resize_height_spin.valueChanged.connect(self.on_resize_settings_changed)
        self.resize_percent_spin.valueChanged.connect(self.on_resize_settings_changed)

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
        # 延迟更新预览以避免频繁刷新
        self.preview_timer.stop()
        self.preview_timer.start(300)  # 300ms 延迟
    
    def on_opacity_changed(self):
        """透明度改变事件"""
        value = self.opacity_slider.value()
        percent = int(value * 100 / 255)
        self.opacity_label.setText(f"{percent}%")
        self.on_watermark_changed()

    def on_choose_text_color(self):
        color = QColorDialog.getColor(self.text_color, self, "选择文字颜色")
        if color.isValid():
            self.text_color = color
            self._update_color_button(self.text_color_btn, color)
            self.on_watermark_changed()

    def on_choose_stroke_color(self):
        color = QColorDialog.getColor(self.stroke_color, self, "选择描边颜色")
        if color.isValid():
            self.stroke_color = color
            self._update_color_button(self.stroke_color_btn, color)
            self.on_watermark_changed()

    def on_shadow_offset_changed(self, _value=None):
        self.shadow_offset = (
            self.shadow_offset_x_spin.value(),
            self.shadow_offset_y_spin.value()
        )
        self.on_watermark_changed()

    def on_rotation_changed(self, value: int):
        self._update_rotation_label(value)
        if hasattr(self, "rotation_spin") and self.rotation_spin.value() != value:
            self.rotation_spin.blockSignals(True)
            self.rotation_spin.setValue(value)
            self.rotation_spin.blockSignals(False)
        self.on_watermark_changed()

    def on_rotation_spin_changed(self, value: int):
        if self.rotation_slider.value() != value:
            self.rotation_slider.blockSignals(True)
            self.rotation_slider.setValue(value)
            self.rotation_slider.blockSignals(False)
        self.on_rotation_changed(value)

    def on_watermark_tab_changed(self, index: int):
        self.current_watermark_type = "text" if index == 0 else "image"
        self.on_watermark_changed()

    def on_choose_image_watermark(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择水印图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.tiff *.tif)"
        )
        if file_path:
            self.image_path_edit.setText(file_path)
            self.image_watermark_path = file_path
            self.on_watermark_changed()

    def on_image_scale_changed(self, value: int):
        self._update_image_scale_label(value)
        self.on_watermark_changed()

    def on_image_opacity_changed(self, value: int):
        self._update_image_opacity_label(value)
        self.on_watermark_changed()

    def on_resize_settings_changed(self, *_args):
        self._update_resize_controls()
        self.on_watermark_changed()

    def on_position_button_clicked(self, button):
        """九宫格位置按钮点击事件"""
        if button not in self.position_buttons.buttons():
            return
        self.use_custom_position = False
        self.custom_watermark_position = None
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
        if self._pending_preset_position:
            self._pending_preset_position = False
            self.custom_watermark_position = None
            self.use_custom_position = False
            return
        if self._suppress_watermark_position_signal:
            return
        # 更新自定义位置
        self.custom_watermark_position = position
        self.use_custom_position = True
        
        # 取消位置按钮的选择（因为现在是自定义位置）
        for button in self.position_buttons.buttons():
            button.setChecked(False)
        
        print(f"水印位置已更新为: {position}")  # 调试信息
    
    def _clear_watermark_position_suppression(self):
        """在事件循环空闲时恢复位置同步"""
        self._suppress_watermark_position_signal = False

    def _clear_pending_preset_position(self):
        self._pending_preset_position = False

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

        config = self.get_current_config()
        display_image = current_image.copy()

        if config.resize_enabled:
            display_image = self.image_processor.resize_image(
                display_image,
                config.resize_method,
                config.resize_width,
                config.resize_height,
                config.resize_percentage,
                config.keep_aspect_ratio
            )

        image_size = display_image.size
        base_pixmap = self.image_processor.pil_to_qpixmap(display_image)
        self.preview_view.set_image(base_pixmap)

        watermark_size = (0, 0)
        text_font = None
        text_color = None
        watermark_pixmap = None

        if config.watermark_type == "image":
            watermark_path = config.image_watermark_path or self.image_watermark_path
            if not watermark_path or not os.path.exists(watermark_path):
                self._pending_preset_position = False
                QTimer.singleShot(0, self._clear_watermark_position_suppression)
                return

            source_pixmap = QPixmap(watermark_path)
            if source_pixmap.isNull():
                self._pending_preset_position = False
                QTimer.singleShot(0, self._clear_watermark_position_suppression)
                return

            self.image_watermark_path = watermark_path
            scale = max(0.05, config.image_scale)
            width = max(1, int(source_pixmap.width() * scale))
            height = max(1, int(source_pixmap.height() * scale))
            watermark_pixmap = source_pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            watermark_size = (watermark_pixmap.width(), watermark_pixmap.height())
        else:
            if not config.text.strip():
                self._pending_preset_position = False
                QTimer.singleShot(0, self._clear_watermark_position_suppression)
                return

            text_font = QFont(config.font_family, config.font_size)
            text_font.setBold(config.font_bold)
            text_font.setItalic(config.font_italic)
            text_color = QColor(*config.text_color)
            text_color.setAlpha(config.opacity)
            watermark_size = self._estimate_text_size(config)

        if config.use_custom_position and config.custom_position:
            position = self._clamp_position_to_image(
                config.custom_position,
                image_size,
                watermark_size
            )
        else:
            position = self._calculate_default_watermark_position(
                image_size,
                watermark_size,
                config.position_type
            )

        self._pending_preset_position = not config.use_custom_position
        self._suppress_watermark_position_signal = True

        if config.watermark_type == "image" and watermark_pixmap:
            self.preview_view.add_watermark_preview(
                opacity=config.image_opacity,
                position=position,
                rotation=config.rotation_angle,
                pixmap=watermark_pixmap
            )
        elif config.watermark_type == "text":
            self.preview_view.add_watermark_preview(
                text=config.text,
                font=text_font,
                color=text_color,
                opacity=config.opacity,
                position=position,
                rotation=config.rotation_angle
            )
            self._apply_text_shadow_effect(config)

        QTimer.singleShot(0, self._clear_watermark_position_suppression)

        if self._pending_preset_position:
            QTimer.singleShot(0, self._clear_pending_preset_position)
    
    def _estimate_text_size(self, config: WatermarkConfig) -> tuple:
        return self.image_processor.measure_text(
            config.text or "",
            config.font_family,
            config.font_size,
            config.font_bold,
            config.font_italic,
            config.text_stroke,
            config.stroke_width,
            config.text_shadow,
            tuple(config.shadow_offset),
            config.rotation_angle,
            config.font_path or None,
            config.font_index
        )

    @staticmethod
    def _clamp_position_to_image(position: tuple, image_size: tuple, watermark_size: tuple) -> tuple:
        img_w, img_h = image_size
        wm_w, wm_h = watermark_size or (0, 0)

        half_w = wm_w / 2
        half_h = wm_h / 2

        min_x = half_w
        max_x = img_w - half_w
        min_y = half_h
        max_y = img_h - half_h

        if min_x > max_x:
            min_x = max_x = img_w / 2
        if min_y > max_y:
            min_y = max_y = img_h / 2

        if not position:
            return int(round(min_x)), int(round(min_y))

        x = max(min_x, min(position[0], max_x))
        y = max(min_y, min(position[1], max_y))
        return int(round(x)), int(round(y))

    def _calculate_default_watermark_position(self, image_size: tuple, watermark_size: tuple,
                                              position_type: str) -> tuple:
        img_width, img_height = image_size
        wm_width, wm_height = watermark_size
        margin = 20

        wm_width = min(wm_width, img_width)
        wm_height = min(wm_height, img_height)

        half_w = wm_width / 2
        half_h = wm_height / 2

        left_x = margin + half_w
        right_x = max(margin + half_w, img_width - margin - half_w)
        center_x = img_width / 2

        top_y = margin + half_h
        bottom_y = max(margin + half_h, img_height - margin - half_h)
        center_y = img_height / 2

        positions = {
            'top-left': (left_x, top_y),
            'top-center': (center_x, top_y),
            'top-right': (right_x, top_y),
            'middle-left': (left_x, center_y),
            'center': (center_x, center_y),
            'middle-right': (right_x, center_y),
            'bottom-left': (left_x, bottom_y),
            'bottom-center': (center_x, bottom_y),
            'bottom-right': (right_x, bottom_y)
        }

        chosen = positions.get(position_type, positions['bottom-right'])
        return int(round(chosen[0])), int(round(chosen[1]))

    def _apply_text_shadow_effect(self, config: WatermarkConfig) -> None:
        if not isinstance(self.preview_view.watermark_item, DraggableWatermarkItem):
            return

        item = self.preview_view.watermark_item
        if config.text_shadow:
            effect = QGraphicsDropShadowEffect()
            effect.setBlurRadius(20)
            offset_x, offset_y = config.shadow_offset
            effect.setOffset(offset_x, offset_y)
            effect.setColor(QColor(0, 0, 0, min(255, config.opacity)))
            item.setGraphicsEffect(effect)
            item._shadow_effect = effect
        else:
            item.setGraphicsEffect(None)
            item._shadow_effect = None

    def get_current_config(self) -> WatermarkConfig:
        """获取当前UI配置"""
        config = WatermarkConfig()
        
        # 水印设置
        config.text = self.watermark_text.text()
        config.font_size = self.font_size_spin.value()
        current_font = self.font_combo.currentFont()
        config.font_family = current_font.family()
        config.font_bold = self.bold_btn.isChecked()
        config.font_italic = self.italic_btn.isChecked()
        config.opacity = self.opacity_slider.value()
        config.text_color = (
            self.text_color.red(),
            self.text_color.green(),
            self.text_color.blue()
        )
        config.text_shadow = self.shadow_check.isChecked()
        config.shadow_offset = (
            self.shadow_offset_x_spin.value(),
            self.shadow_offset_y_spin.value()
        )
        config.text_stroke = self.stroke_check.isChecked()
        config.stroke_width = self.stroke_width_spin.value()
        config.stroke_color = (
            self.stroke_color.red(),
            self.stroke_color.green(),
            self.stroke_color.blue()
        )
        config.rotation_angle = self.rotation_slider.value()
        config.watermark_type = self.current_watermark_type
        config.image_watermark_path = self.image_path_edit.text()
        config.image_scale = max(0.05, self.image_scale_slider.value() / 100.0)
        config.image_opacity = self.image_opacity_slider.value()
        config.custom_position = self.custom_watermark_position or (0, 0)
        
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

        config.resize_enabled = self.resize_check.isChecked()
        config.resize_method = self._current_resize_method()
        config.resize_width = self.resize_width_spin.value()
        config.resize_height = self.resize_height_spin.value()
        config.resize_percentage = self.resize_percent_spin.value()
        config.keep_aspect_ratio = self.keep_aspect_check.isChecked()

        resolved_font = self.image_processor.resolve_font_face(
            config.font_family,
            config.font_bold,
            config.font_italic
        )
        if resolved_font:
            config.font_path, config.font_index = resolved_font
        else:
            config.font_path = ""
            config.font_index = 0
        
        return config
    
    def load_config_to_ui(self):
        """加载配置到UI"""
        config = self.config_manager.get_config()
        
        # 设置水印配置
        self.current_watermark_type = config.watermark_type
        self.watermark_tabs.blockSignals(True)
        self.watermark_tabs.setCurrentIndex(0 if config.watermark_type == "text" else 1)
        self.watermark_tabs.blockSignals(False)
        self.watermark_text.setText(config.text)
        self.font_size_spin.setValue(config.font_size)
        font = QFont(config.font_family, config.font_size)
        self.font_combo.setCurrentFont(font)
        self.bold_btn.setChecked(config.font_bold)
        self.italic_btn.setChecked(config.font_italic)
        self.text_color = QColor(*config.text_color)
        self._update_color_button(self.text_color_btn, self.text_color)
        self.stroke_color = QColor(*config.stroke_color)
        self._update_color_button(self.stroke_color_btn, self.stroke_color)
        self.shadow_check.setChecked(config.text_shadow)
        self.shadow_offset_x_spin.setValue(config.shadow_offset[0])
        self.shadow_offset_y_spin.setValue(config.shadow_offset[1])
        self.shadow_offset = tuple(config.shadow_offset)
        self.stroke_check.setChecked(config.text_stroke)
        self.stroke_width_spin.setValue(config.stroke_width)
        self.opacity_slider.setValue(config.opacity)
        self.on_opacity_changed()
        self.rotation_spin.setValue(config.rotation_angle)
        self.rotation_slider.setValue(config.rotation_angle)
        self._update_rotation_label(config.rotation_angle)
        self.image_path_edit.setText(config.image_watermark_path)
        self.image_watermark_path = config.image_watermark_path
        scale_value = int(config.image_scale * 100)
        scale_value = max(self.image_scale_slider.minimum(), min(self.image_scale_slider.maximum(), scale_value))
        self.image_scale_slider.setValue(scale_value)
        self._update_image_scale_label(scale_value)
        self.image_opacity_slider.setValue(config.image_opacity)
        self._update_image_opacity_label(config.image_opacity)
        self.resize_check.setChecked(config.resize_enabled)
        if config.resize_method == "width":
            self.resize_width_radio.setChecked(True)
        elif config.resize_method == "height":
            self.resize_height_radio.setChecked(True)
        else:
            self.resize_percent_radio.setChecked(True)
        self.resize_width_spin.setValue(config.resize_width)
        self.resize_height_spin.setValue(config.resize_height)
        self.resize_percent_spin.setValue(config.resize_percentage)
        self.keep_aspect_check.setChecked(config.keep_aspect_ratio)
        self._update_resize_controls()
        
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
        
        widgets_to_block = [
            self.watermark_tabs,
            self.watermark_text,
            self.font_size_spin,
            self.font_combo,
            self.bold_btn,
            self.italic_btn,
            self.opacity_slider,
            self.shadow_check,
            self.shadow_offset_x_spin,
            self.shadow_offset_y_spin,
            self.stroke_check,
            self.stroke_width_spin,
            self.rotation_slider,
            self.rotation_spin,
            self.image_scale_slider,
            self.image_opacity_slider,
            self.resize_check,
            self.resize_width_radio,
            self.resize_height_radio,
            self.resize_percent_radio,
            self.resize_width_spin,
            self.resize_height_spin,
            self.resize_percent_spin,
            self.keep_aspect_check,
            self.format_combo,
            self.jpeg_quality_slider,
            self.filename_original,
            self.filename_prefix,
            self.filename_suffix,
            self.prefix_input,
            self.suffix_input
        ]

        for widget in widgets_to_block:
            widget.blockSignals(True)

        try:
            self.current_watermark_type = config.watermark_type
            self.watermark_tabs.setCurrentIndex(0 if config.watermark_type == "text" else 1)
            self.watermark_text.setText(config.text)
            self.font_size_spin.setValue(config.font_size)
            self.font_combo.setCurrentFont(QFont(config.font_family, config.font_size))
            self.bold_btn.setChecked(config.font_bold)
            self.italic_btn.setChecked(config.font_italic)
            self.text_color = QColor(*config.text_color)
            self._update_color_button(self.text_color_btn, self.text_color)
            self.stroke_color = QColor(*config.stroke_color)
            self._update_color_button(self.stroke_color_btn, self.stroke_color)
            self.shadow_check.setChecked(config.text_shadow)
            self.shadow_offset_x_spin.setValue(config.shadow_offset[0])
            self.shadow_offset_y_spin.setValue(config.shadow_offset[1])
            self.shadow_offset = tuple(config.shadow_offset)
            self.stroke_check.setChecked(config.text_stroke)
            self.stroke_width_spin.setValue(config.stroke_width)
            self.opacity_slider.setValue(config.opacity)
            self.rotation_spin.setValue(config.rotation_angle)
            self.rotation_slider.setValue(config.rotation_angle)
            self._update_rotation_label(config.rotation_angle)
            self.image_path_edit.setText(config.image_watermark_path)
            self.image_watermark_path = config.image_watermark_path
            scale_value = int(config.image_scale * 100)
            scale_value = max(self.image_scale_slider.minimum(), min(self.image_scale_slider.maximum(), scale_value))
            self.image_scale_slider.setValue(scale_value)
            self._update_image_scale_label(scale_value)
            self.image_opacity_slider.setValue(config.image_opacity)
            self._update_image_opacity_label(config.image_opacity)
            self.resize_check.setChecked(config.resize_enabled)
            if config.resize_method == "width":
                self.resize_width_radio.setChecked(True)
            elif config.resize_method == "height":
                self.resize_height_radio.setChecked(True)
            else:
                self.resize_percent_radio.setChecked(True)
            self.resize_width_spin.setValue(config.resize_width)
            self.resize_height_spin.setValue(config.resize_height)
            self.resize_percent_spin.setValue(config.resize_percentage)
            self.keep_aspect_check.setChecked(config.keep_aspect_ratio)
            self._update_resize_controls()

            for button in self.position_buttons.buttons():
                button.blockSignals(True)
                button.setChecked(button.property("position") == config.position_type)
                button.blockSignals(False)

            self.format_combo.setCurrentText(config.output_format)
            self.jpeg_quality_slider.setValue(config.jpeg_quality)

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

            self.prefix_input.setText(config.filename_prefix)
            self.suffix_input.setText(config.filename_suffix)

            if config.use_custom_position and config.custom_position:
                self.use_custom_position = True
                self.custom_watermark_position = config.custom_position
                for button in self.position_buttons.buttons():
                    button.blockSignals(True)
                    button.setChecked(False)
                    button.blockSignals(False)
            else:
                self.use_custom_position = False
                self.custom_watermark_position = None

            self.on_filename_rule_changed()
            self.on_format_changed()
            self.on_opacity_changed()
            self.on_jpeg_quality_changed()

        finally:
            for widget in widgets_to_block:
                widget.blockSignals(False)
    
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