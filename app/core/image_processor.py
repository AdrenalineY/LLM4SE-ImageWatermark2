"""
图像处理模块
负责图像加载、水印合成、格式转换等核心功能
"""

import os
from typing import Tuple, Optional, Union
from PIL import Image, ImageDraw, ImageFont
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QPixmap, QImage


class ImageProcessor:
    """图像处理器类"""
    
    # 支持的图像格式
    SUPPORTED_INPUT_FORMATS = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif')
    SUPPORTED_OUTPUT_FORMATS = ['JPEG', 'PNG']
    
    def __init__(self):
        """初始化图像处理器"""
        self.images = {}  # 存储加载的图像 {file_path: PIL.Image}
        self.current_image_path = None
        
    def load_image(self, file_path: str) -> bool:
        """
        加载图像文件
        
        Args:
            file_path: 图像文件路径
            
        Returns:
            bool: 是否加载成功
        """
        try:
            if not os.path.exists(file_path):
                return False
                
            # 检查文件格式
            if not any(file_path.lower().endswith(fmt) for fmt in self.SUPPORTED_INPUT_FORMATS):
                return False
                
            # 加载图像
            image = Image.open(file_path)
            # 转换为RGBA模式以支持透明度
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
                
            self.images[file_path] = image
            if self.current_image_path is None:
                self.current_image_path = file_path
                
            return True
            
        except Exception as e:
            print(f"加载图像失败: {e}")
            return False
    
    def load_images_from_folder(self, folder_path: str) -> int:
        """
        从文件夹批量加载图像
        
        Args:
            folder_path: 文件夹路径
            
        Returns:
            int: 成功加载的图像数量
        """
        count = 0
        try:
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path) and self.load_image(file_path):
                    count += 1
        except Exception as e:
            print(f"批量加载图像失败: {e}")
            
        return count
    
    def get_image_list(self) -> list:
        """获取已加载的图像列表"""
        return list(self.images.keys())
    
    def set_current_image(self, file_path: str) -> bool:
        """
        设置当前预览的图像
        
        Args:
            file_path: 图像文件路径
            
        Returns:
            bool: 是否设置成功
        """
        if file_path in self.images:
            self.current_image_path = file_path
            return True
        return False
    
    def get_current_image(self) -> Optional[Image.Image]:
        """获取当前图像"""
        if self.current_image_path and self.current_image_path in self.images:
            return self.images[self.current_image_path]
        return None
    
    def create_thumbnail(self, file_path: str, size: Tuple[int, int] = (150, 150)) -> Optional[QPixmap]:
        """
        创建缩略图
        
        Args:
            file_path: 图像文件路径
            size: 缩略图尺寸
            
        Returns:
            QPixmap: 缩略图pixmap对象
        """
        if file_path not in self.images:
            return None
            
        try:
            image = self.images[file_path].copy()
            
            # 确保图像是RGB模式，避免透明度和调色板问题
            if image.mode == 'RGBA':
                # 对于RGBA图像，创建白色背景并合成
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])  # 使用alpha通道作为mask
                image = background
            elif image.mode in ('P', 'L', 'LA'):
                # 转换调色板和灰度图像为RGB
                image = image.convert('RGB')
            elif image.mode not in ('RGB', 'YCbCr'):
                # 其他模式也转换为RGB
                image = image.convert('RGB')
            
            # 创建缩略图，保持宽高比
            image.thumbnail(size, Image.Resampling.LANCZOS)
            
            # 转换为QPixmap
            return self.pil_to_qpixmap(image)
            
        except Exception as e:
            print(f"创建缩略图失败: {e}")
            return None
    
    def add_text_watermark(self, image: Image.Image, text: str, position: Tuple[int, int], 
                          opacity: int = 128, font_size: int = 36) -> Image.Image:
        """
        添加文本水印
        
        Args:
            image: 原始图像
            text: 水印文本
            position: 水印位置 (x, y)
            opacity: 透明度 (0-255)
            font_size: 字体大小
            
        Returns:
            Image.Image: 添加水印后的图像
        """
        try:
            # 创建图像副本
            watermarked = image.copy()
            
            # 创建透明图层
            overlay = Image.new('RGBA', watermarked.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            
            # 尝试加载字体（使用系统默认字体）
            try:
                # Windows系统字体
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                try:
                    # macOS系统字体
                    font = ImageFont.truetype("Helvetica.ttc", font_size)
                except:
                    # 使用默认字体
                    font = ImageFont.load_default()
            
            # 绘制文本
            draw.text(position, text, font=font, fill=(255, 255, 255, opacity))
            
            # 合成图像
            watermarked = Image.alpha_composite(watermarked, overlay)
            
            return watermarked
            
        except Exception as e:
            print(f"添加文本水印失败: {e}")
            return image
    
    def calculate_position(self, image_size: Tuple[int, int], text: str, 
                          position_type: str, font_size: int = 36) -> Tuple[int, int]:
        """
        根据位置类型计算水印位置
        
        Args:
            image_size: 图像尺寸 (width, height)
            text: 水印文本
            position_type: 位置类型 ('top-left', 'top-center', 'top-right', 
                         'middle-left', 'center', 'middle-right',
                         'bottom-left', 'bottom-center', 'bottom-right')
            font_size: 字体大小
            
        Returns:
            Tuple[int, int]: 计算得出的位置坐标
        """
        img_width, img_height = image_size
        
        # 估算文本尺寸（简单估算）
        text_width = len(text) * font_size * 0.6
        text_height = font_size
        
        # 边距
        margin = 20
        
        positions = {
            'top-left': (margin, margin),
            'top-center': (img_width // 2 - text_width // 2, margin),
            'top-right': (img_width - text_width - margin, margin),
            'middle-left': (margin, img_height // 2 - text_height // 2),
            'center': (img_width // 2 - text_width // 2, img_height // 2 - text_height // 2),
            'middle-right': (img_width - text_width - margin, img_height // 2 - text_height // 2),
            'bottom-left': (margin, img_height - text_height - margin),
            'bottom-center': (img_width // 2 - text_width // 2, img_height - text_height - margin),
            'bottom-right': (img_width - text_width - margin, img_height - text_height - margin)
        }
        
        return positions.get(position_type, positions['bottom-right'])
    
    def export_image(self, file_path: str, output_path: str, format: str = 'PNG', 
                    quality: int = 95) -> bool:
        """
        导出图像
        
        Args:
            file_path: 原始图像路径
            output_path: 输出路径
            format: 输出格式 ('JPEG' 或 'PNG')
            quality: JPEG质量 (1-100)
            
        Returns:
            bool: 是否导出成功
        """
        if file_path not in self.images:
            return False
            
        try:
            image = self.images[file_path]
            
            # 如果导出为JPEG，需要转换为RGB模式
            if format.upper() == 'JPEG':
                if image.mode == 'RGBA':
                    # 创建白色背景
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    background.paste(image, mask=image.split()[-1])  # 使用alpha通道作为mask
                    image = background
                image.save(output_path, format=format, quality=quality)
            else:
                image.save(output_path, format=format)
                
            return True
            
        except Exception as e:
            print(f"导出图像失败: {e}")
            return False
    
    def pil_to_qpixmap(self, pil_image: Image.Image) -> QPixmap:
        """
        将PIL图像转换为QPixmap
        
        Args:
            pil_image: PIL图像对象
            
        Returns:
            QPixmap: Qt pixmap对象
        """
        try:
            # 确保图像是RGB模式
            if pil_image.mode == 'RGBA':
                # 创建白色背景并合成RGBA图像
                background = Image.new('RGB', pil_image.size, (255, 255, 255))
                background.paste(pil_image, mask=pil_image.split()[-1])
                pil_image = background
            elif pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # 获取图像数据
            width, height = pil_image.size
            
            # 使用正确的字节顺序和步长
            rgb_image = pil_image.tobytes('raw', 'RGB')
            bytes_per_line = width * 3  # RGB每像素3字节
            
            # 创建QImage，确保字节顺序正确
            qimage = QImage(rgb_image, width, height, bytes_per_line, QImage.Format_RGB888)
            
            # 转换为QPixmap
            if qimage.isNull():
                print("警告: 创建的QImage为空")
                return QPixmap()
                
            pixmap = QPixmap.fromImage(qimage)
            if pixmap.isNull():
                print("警告: 创建的QPixmap为空")
                return QPixmap()
                
            return pixmap
            
        except Exception as e:
            print(f"PIL转QPixmap失败: {e}")
            import traceback
            traceback.print_exc()
            return QPixmap()
    
    def remove_image(self, file_path: str) -> bool:
        """
        移除图像
        
        Args:
            file_path: 图像文件路径
            
        Returns:
            bool: 是否移除成功
        """
        if file_path in self.images:
            del self.images[file_path]
            if self.current_image_path == file_path:
                # 设置新的当前图像
                if self.images:
                    self.current_image_path = list(self.images.keys())[0]
                else:
                    self.current_image_path = None
            return True
        return False
    
    def clear_images(self):
        """清空所有图像"""
        self.images.clear()
        self.current_image_path = None
