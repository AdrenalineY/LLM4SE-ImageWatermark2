"""
测试脚本 - 验证核心功能
"""

import os
import sys
from PIL import Image, ImageDraw

# 添加应用根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.image_processor import ImageProcessor
from app.core.config_manager import ConfigManager


def create_test_image():
    """创建测试图片"""
    # 创建一个简单的测试图片
    img = Image.new('RGB', (800, 600), color='lightblue')
    draw = ImageDraw.Draw(img)
    
    # 绘制一些简单的图形
    draw.rectangle([100, 100, 700, 500], outline='darkblue', width=3)
    draw.text((400, 300), "Test Image", fill='darkblue', anchor='mm')
    
    # 保存测试图片
    test_image_path = "test_image.jpg"
    img.save(test_image_path, "JPEG")
    print(f"测试图片已创建: {test_image_path}")
    return test_image_path


def test_image_processor():
    """测试图像处理功能"""
    print("测试图像处理功能...")
    
    processor = ImageProcessor()
    
    # 创建测试图片
    test_image_path = create_test_image()
    
    # 测试加载图片
    success = processor.load_image(test_image_path)
    print(f"加载图片: {'成功' if success else '失败'}")
    
    # 测试获取图片列表
    image_list = processor.get_image_list()
    print(f"图片列表: {len(image_list)} 张图片")
    
    # 测试设置当前图片
    processor.set_current_image(test_image_path)
    current_image = processor.get_current_image()
    print(f"当前图片: {current_image.size if current_image else None}")
    
    # 测试添加水印
    if current_image:
        position = processor.calculate_position(
            current_image.size, 
            "Test Watermark", 
            "bottom-right"
        )
        watermarked = processor.add_text_watermark(
            current_image,
            "Test Watermark",
            position,
            128,
            36
        )
        print(f"水印添加: {'成功' if watermarked else '失败'}")
        
        # 测试导出
        output_path = "test_output.png"
        export_success = processor.export_image(
            test_image_path,
            output_path,
            "PNG"
        )
        print(f"导出图片: {'成功' if export_success else '失败'}")
        
        if export_success and os.path.exists(output_path):
            print(f"导出文件大小: {os.path.getsize(output_path)} 字节")
    
    print("图像处理功能测试完成\n")


def test_config_manager():
    """测试配置管理功能"""
    print("测试配置管理功能...")
    
    config_manager = ConfigManager()
    
    # 测试获取默认配置
    config = config_manager.get_config()
    print(f"默认水印文字: {config.text}")
    print(f"默认字体大小: {config.font_size}")
    print(f"默认透明度: {config.opacity}")
    
    # 测试更新配置
    config_manager.update_config(
        text="New Watermark",
        font_size=48,
        opacity=200
    )
    
    updated_config = config_manager.get_config()
    print(f"更新后水印文字: {updated_config.text}")
    print(f"更新后字体大小: {updated_config.font_size}")
    print(f"更新后透明度: {updated_config.opacity}")
    
    # 测试保存配置
    save_success = config_manager.save_config()
    print(f"保存配置: {'成功' if save_success else '失败'}")
    
    # 测试加载配置
    load_success = config_manager.load_config()
    print(f"加载配置: {'成功' if load_success else '失败'}")
    
    # 测试模板功能
    template_save_success = config_manager.save_template("测试模板")
    print(f"保存模板: {'成功' if template_save_success else '失败'}")
    
    template_names = config_manager.get_template_names()
    print(f"模板列表: {template_names}")
    
    print("配置管理功能测试完成\n")


def cleanup():
    """清理测试文件"""
    test_files = ["test_image.jpg", "test_output.png"]
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"已删除测试文件: {file}")


if __name__ == "__main__":
    print("开始核心功能测试...\n")
    
    try:
        test_image_processor()
        test_config_manager()
        print("所有测试完成！")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        cleanup()