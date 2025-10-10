# Photo Watermark 2 - 高级功能拓展文档

## 概述

本文档详细说明了在现有Photo Watermark 2项目基础上，实现第二阶段高级功能开发所需的代码扩展方案。涵盖4.6-4.9节的所有功能需求，包括高级文本样式、图片水印、高级导出选项和水印旋转等功能。

## 现有代码架构分析

### 核心模块结构
1. **app/core/config_manager.py** - 配置管理器，处理WatermarkConfig数据类和模板管理
2. **app/core/image_processor.py** - 图像处理器，负责图像加载、水印合成、格式转换
3. **app/ui/main_window.py** - 主窗口UI，包含三面板布局和交互逻辑

### 现有功能特点
- **三面板布局**: 左侧图像列表、中间预览、右侧控制面板
- **水印预览**: 基于QGraphicsView的可拖拽水印预览
- **配置管理**: 支持模板保存/加载、JSON格式配置文件
- **批量处理**: 多线程导出，进度条显示

## 功能拓展需求分析

### 4.6 高级文本水印样式
**目标**: 扩展文本水印的样式选项，提供更专业的自定义能力

#### 新增功能模块
1. **字体选择**: QFontComboBox选择系统字体
2. **文本样式**: 粗体、斜体切换按钮
3. **颜色选择**: QColorDialog颜色选择对话框
4. **文本效果**: 阴影/描边效果

#### 代码修改点

##### 1. 配置数据类扩展 (config_manager.py)
```python
@dataclass
class WatermarkConfig:
    # 现有字段...
    
    # 新增高级文本样式字段
    font_family: str = "Arial"          # 字体族
    font_bold: bool = True              # 粗体
    font_italic: bool = False           # 斜体
    text_color: tuple = (255, 255, 255) # RGB颜色 
    text_shadow: bool = False           # 阴影效果
    text_stroke: bool = False           # 描边效果
    shadow_offset: tuple = (2, 2)       # 阴影偏移
    stroke_width: int = 1               # 描边宽度
    stroke_color: tuple = (0, 0, 0)     # 描边颜色
```

##### 2. UI界面扩展 (main_window.py)
在`setup_watermark_group`方法中添加新控件:
```python
def setup_watermark_group(self, parent_layout):
    # 现有控件...
    
    # 字体选择
    font_layout = QHBoxLayout()
    font_layout.addWidget(QLabel("字体:"))
    self.font_combo = QFontComboBox()
    font_layout.addWidget(self.font_combo)
    watermark_layout.addLayout(font_layout)
    
    # 文本样式
    style_layout = QHBoxLayout()
    self.bold_btn = QPushButton("粗体")
    self.bold_btn.setCheckable(True)
    self.bold_btn.setChecked(True)
    
    self.italic_btn = QPushButton("斜体") 
    self.italic_btn.setCheckable(True)
    
    style_layout.addWidget(self.bold_btn)
    style_layout.addWidget(self.italic_btn)
    watermark_layout.addLayout(style_layout)
    
    # 颜色选择
    color_layout = QHBoxLayout()
    color_layout.addWidget(QLabel("文字颜色:"))
    self.color_btn = QPushButton()
    self.color_btn.setStyleSheet("background-color: white")
    self.color_btn.clicked.connect(self.choose_text_color)
    color_layout.addWidget(self.color_btn)
    watermark_layout.addLayout(color_layout)
    
    # 文本效果
    effect_layout = QVBoxLayout()
    self.shadow_check = QCheckBox("阴影效果")
    self.stroke_check = QCheckBox("描边效果")  
    effect_layout.addWidget(self.shadow_check)
    effect_layout.addWidget(self.stroke_check)
    watermark_layout.addLayout(effect_layout)
```

##### 3. 图像处理增强 (image_processor.py)
扩展`add_text_watermark`方法支持高级样式:
```python
def add_text_watermark(self, image: Image.Image, text: str, position: Tuple[int, int],
                      opacity: int = 128, font_size: int = 36, 
                      font_family: str = "Arial", bold: bool = True, italic: bool = False,
                      color: tuple = (255, 255, 255), shadow: bool = False, 
                      stroke: bool = False, **kwargs) -> Image.Image:
    # 实现高级文本样式渲染逻辑
```

### 4.7 图片水印
**目标**: 添加图片水印功能，支持PNG/JPG水印图片

#### 新增功能模块
1. **Tab界面**: 在右侧面板添加"图片水印"标签页
2. **图片选择**: 文件选择对话框导入水印图片
3. **大小调整**: 滑块控制水印图片缩放
4. **透明度**: 滑块控制图片水印透明度

#### 代码修改点

##### 1. 配置数据类扩展
```python
@dataclass  
class WatermarkConfig:
    # 现有字段...
    
    # 图片水印字段
    watermark_type: str = "text"        # "text" 或 "image"
    image_watermark_path: str = ""      # 水印图片路径
    image_scale: float = 1.0            # 图片缩放比例
    image_opacity: int = 128            # 图片透明度
```

##### 2. UI界面重构
将水印设置区域改为QTabWidget:
```python
def setup_watermark_group(self, parent_layout):
    watermark_group = QGroupBox("水印设置")
    watermark_layout = QVBoxLayout(watermark_group)
    
    # 创建标签页
    self.watermark_tabs = QTabWidget()
    
    # 文本水印标签页
    text_tab = QWidget()
    self.setup_text_watermark_tab(text_tab)
    self.watermark_tabs.addTab(text_tab, "文本水印")
    
    # 图片水印标签页
    image_tab = QWidget() 
    self.setup_image_watermark_tab(image_tab)
    self.watermark_tabs.addTab(image_tab, "图片水印")
    
    watermark_layout.addWidget(self.watermark_tabs)
    parent_layout.addWidget(watermark_group)
```

##### 3. 图像处理扩展
添加图片水印合成方法:
```python
def add_image_watermark(self, image: Image.Image, watermark_path: str, 
                       position: Tuple[int, int], scale: float = 1.0,
                       opacity: int = 128) -> Image.Image:
    # 实现图片水印合成逻辑
```

### 4.8 高级导出选项  
**目标**: 增强导出功能，支持图片尺寸调整

#### 新增功能模块
1. **尺寸调整**: 按宽度、高度或百分比缩放
2. **高级JPEG选项**: 质量设置优化
3. **批量导出优化**: 更多格式选项

#### 代码修改点

##### 1. 配置数据类扩展
```python
@dataclass
class WatermarkConfig:
    # 现有字段...
    
    # 高级导出选项
    resize_enabled: bool = False        # 是否启用尺寸调整
    resize_method: str = "percentage"   # "width", "height", "percentage"
    resize_width: int = 800             # 目标宽度
    resize_height: int = 600            # 目标高度  
    resize_percentage: int = 100        # 缩放百分比
    keep_aspect_ratio: bool = True      # 保持宽高比
```

##### 2. UI界面扩展
在导出设置组中添加尺寸调整选项:
```python
def setup_export_group(self, parent_layout):
    # 现有导出设置...
    
    # 尺寸调整
    resize_group = QGroupBox("尺寸调整")
    resize_layout = QVBoxLayout(resize_group)
    
    self.resize_check = QCheckBox("启用尺寸调整")
    resize_layout.addWidget(self.resize_check)
    
    # 调整方式选择
    method_layout = QHBoxLayout()
    self.resize_width_radio = QRadioButton("按宽度")
    self.resize_height_radio = QRadioButton("按高度")
    self.resize_percent_radio = QRadioButton("按百分比")
    self.resize_percent_radio.setChecked(True)
    
    # 参数输入控件...
    
    export_layout.addWidget(resize_group)
```

### 4.9 其他高级功能
**目标**: 水印旋转和模板管理增强

#### 4.9.1 水印旋转

##### 配置扩展
```python
@dataclass
class WatermarkConfig:
    # 现有字段...
    rotation_angle: int = 0             # 旋转角度 (-180 to 180)
```

##### UI控件
```python
# 在水印设置中添加旋转滑块
rotation_layout = QHBoxLayout()
rotation_layout.addWidget(QLabel("旋转角度:"))
self.rotation_slider = QSlider(Qt.Horizontal)
self.rotation_slider.setRange(-180, 180)
self.rotation_slider.setValue(0)
rotation_layout.addWidget(self.rotation_slider)

self.rotation_label = QLabel("0°")
rotation_layout.addWidget(self.rotation_label)
```

#### 4.9.2 模板管理增强
当前已有基础模板功能，需要增强:
1. **模板重命名**: 右键菜单支持重命名
2. **模板导入导出**: 支持.json文件导入导出
3. **预览缩略图**: 模板选择时显示水印效果预览

## 实施优先级和依赖关系

### 阶段1: 基础扩展 (1-2天)
1. 配置数据类扩展 - 为所有新功能添加字段
2. 高级文本样式UI - 字体、颜色、样式选择
3. 水印旋转功能 - 简单旋转滑块

### 阶段2: 图片水印 (2-3天)  
1. Tab界面重构 - 文本/图片水印分离
2. 图片水印核心逻辑 - 图片加载、缩放、合成
3. 图片水印预览 - 扩展PreviewGraphicsView

### 阶段3: 导出增强 (1-2天)
1. 尺寸调整逻辑 - 图片缩放算法
2. 高级导出UI - 尺寸调整面板  
3. 批量处理优化 - 支持新的导出选项

### 阶段4: 集成测试 (1天)
1. 功能集成测试
2. 配置兼容性测试 
3. 性能优化

## 技术难点和解决方案

### 1. 复杂文本渲染
**挑战**: Pillow的文本渲染功能有限，需要实现阴影、描边效果
**解决**: 多图层合成技术，先绘制效果层再绘制文本层

### 2. 图片水印性能
**挑战**: 大图片水印会影响预览性能
**解决**: 预览使用缩略图，导出时使用原图

### 3. 配置向后兼容
**挑战**: 新增字段可能导致旧配置无法加载
**解决**: WatermarkConfig.from_dict方法中加入默认值处理

### 4. UI响应性
**挑战**: 复杂水印渲染可能阻塞UI
**解决**: 使用QTimer延迟更新和后台线程渲染

## 测试策略

### 单元测试
- 配置序列化/反序列化测试
- 图像处理算法测试  
- 文本渲染效果测试

### 集成测试
- 完整导出流程测试
- UI交互测试
- 配置兼容性测试

### 性能测试  
- 大批量图片导出测试
- 复杂水印预览性能测试
- 内存使用情况监控

## 总结

本拓展方案在保持现有架构稳定性的基础上，通过模块化的方式逐步添加高级功能。重点关注向后兼容性和用户体验，确保新功能的集成不会影响现有功能的稳定运行。预计总开发时间6-8天，能够显著提升应用程序的专业性和用户满意度。