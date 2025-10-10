"""
配置管理模块
负责水印设置的保存、加载和模板管理
"""

import json
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict


@dataclass
class WatermarkConfig:
    """水印配置数据类"""
    # 基础文本水印设置
    text: str = "Sample Watermark"
    font_size: int = 36
    opacity: int = 128  # 0-255
    position_type: str = "bottom-right"  # 九宫格位置
    custom_position: tuple = (0, 0)  # 自定义位置 (x, y)
    use_custom_position: bool = False

    # 高级文本样式 (4.6)
    font_family: str = "Arial"
    font_bold: bool = True
    font_italic: bool = False
    text_color: tuple = (255, 255, 255)
    text_shadow: bool = False
    text_stroke: bool = False
    shadow_offset: tuple = (2, 2)
    stroke_width: int = 1
    stroke_color: tuple = (0, 0, 0)
    font_path: str = ""
    font_index: int = 0

    # 图片水印 (4.7)
    watermark_type: str = "text"  # text 或 image
    image_watermark_path: str = ""
    image_scale: float = 1.0
    image_opacity: int = 128

    # 水印旋转 (4.9)
    rotation_angle: int = 0

    # 导出设置
    output_format: str = "PNG"  # JPEG 或 PNG
    jpeg_quality: int = 95  # 1-100
    filename_rule: str = "suffix"  # original, prefix, suffix
    filename_prefix: str = "wm_"
    filename_suffix: str = "_watermarked"

    # 高级导出选项 (4.8)
    resize_enabled: bool = False
    resize_method: str = "percentage"  # width, height, percentage
    resize_width: int = 800
    resize_height: int = 600
    resize_percentage: int = 100
    keep_aspect_ratio: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，并确保JSON兼容"""
        data = asdict(self)
        tuple_keys = {
            "custom_position",
            "text_color",
            "shadow_offset",
            "stroke_color",
        }
        for key in tuple_keys:
            if key in data and isinstance(data[key], tuple):
                data[key] = list(data[key])
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WatermarkConfig':
        """从字典创建配置对象，兼容旧配置文件"""
        config = cls()
        tuple_fields = {
            "custom_position",
            "text_color",
            "shadow_offset",
            "stroke_color",
        }
        for key, value in data.items():
            if hasattr(config, key):
                if key in tuple_fields and isinstance(value, list):
                    value = tuple(value)
                setattr(config, key, value)
        return config


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录，默认为用户目录下的.photo_watermark
        """
        if config_dir is None:
            self.config_dir = os.path.expanduser("~/.photo_watermark")
        else:
            self.config_dir = config_dir
            
        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)
        
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.templates_file = os.path.join(self.config_dir, "templates.json")
        
        # 当前配置
        self.current_config = WatermarkConfig()
        
        # 加载配置
        self.load_config()
    
    def save_config(self) -> bool:
        """
        保存当前配置到文件
        
        Returns:
            bool: 是否保存成功
        """
        try:
            config_data = {
                "version": "1.0",
                "watermark": self.current_config.to_dict()
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
                
            return True
            
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    def load_config(self) -> bool:
        """
        从文件加载配置
        
        Returns:
            bool: 是否加载成功
        """
        try:
            if not os.path.exists(self.config_file):
                # 使用默认配置
                return self.save_config()
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            if "watermark" in config_data:
                self.current_config = WatermarkConfig.from_dict(config_data["watermark"])
            
            return True
            
        except Exception as e:
            print(f"加载配置失败: {e}")
            # 使用默认配置
            self.current_config = WatermarkConfig()
            return False
    
    def get_config(self) -> WatermarkConfig:
        """获取当前配置"""
        return self.current_config
    
    def update_config(self, **kwargs) -> None:
        """
        更新配置
        
        Args:
            **kwargs: 要更新的配置项
        """
        for key, value in kwargs.items():
            if hasattr(self.current_config, key):
                setattr(self.current_config, key, value)
    
    def save_template(self, name: str, config: WatermarkConfig = None) -> bool:
        """
        保存水印模板
        
        Args:
            name: 模板名称
            config: 要保存的配置，如果为None则使用当前配置
            
        Returns:
            bool: 是否保存成功
        """
        try:
            if config is None:
                config = self.current_config
            
            # 加载现有模板
            templates = self.load_templates()
            
            # 添加新模板
            templates[name] = config.to_dict()
            
            # 保存模板文件
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                json.dump(templates, f, indent=2, ensure_ascii=False)
                
            return True
            
        except Exception as e:
            print(f"保存模板失败: {e}")
            return False
    
    def load_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        加载所有模板
        
        Returns:
            Dict: 模板字典 {name: config_dict}
        """
        try:
            if not os.path.exists(self.templates_file):
                return {}
            
            with open(self.templates_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            print(f"加载模板失败: {e}")
            return {}
    
    def get_template_names(self) -> List[str]:
        """获取所有模板名称"""
        templates = self.load_templates()
        return list(templates.keys())
    
    def load_template(self, name: str) -> bool:
        """
        加载指定模板到当前配置
        
        Args:
            name: 模板名称
            
        Returns:
            bool: 是否加载成功
        """
        try:
            templates = self.load_templates()
            if name not in templates:
                return False
            
            self.current_config = WatermarkConfig.from_dict(templates[name])
            return True
            
        except Exception as e:
            print(f"加载模板失败: {e}")
            return False
    
    def delete_template(self, name: str) -> bool:
        """
        删除指定模板
        
        Args:
            name: 模板名称
            
        Returns:
            bool: 是否删除成功
        """
        try:
            templates = self.load_templates()
            if name not in templates:
                return False
            
            del templates[name]
            
            # 保存更新后的模板文件
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                json.dump(templates, f, indent=2, ensure_ascii=False)
                
            return True
            
        except Exception as e:
            print(f"删除模板失败: {e}")
            return False
    
    def reset_to_default(self) -> None:
        """重置为默认配置"""
        self.current_config = WatermarkConfig()
    
    def get_recent_output_folder(self) -> Optional[str]:
        """获取最近使用的输出文件夹"""
        try:
            if not os.path.exists(self.config_file):
                return None
                
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                
            return config_data.get("recent_output_folder")
            
        except Exception:
            return None
    
    def save_recent_output_folder(self, folder_path: str) -> bool:
        """
        保存最近使用的输出文件夹
        
        Args:
            folder_path: 文件夹路径
            
        Returns:
            bool: 是否保存成功
        """
        try:
            config_data = {
                "version": "1.0",
                "watermark": self.current_config.to_dict(),
                "recent_output_folder": folder_path
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
                
            return True
            
        except Exception as e:
            print(f"保存输出文件夹失败: {e}")
            return False
