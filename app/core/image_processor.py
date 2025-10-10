"""
图像处理模块
负责图像加载、水印合成、格式转换等核心功能
"""

import os
import sys
import math
from dataclasses import dataclass
from typing import Tuple, Optional, Union, Dict, TYPE_CHECKING, List
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from .config_manager import WatermarkConfig
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QPixmap, QImage


@dataclass(frozen=True)
class FontEntry:
    path: str
    style: str
    index: int = 0


class FontResolver:
    def __init__(self):
        self._fonts_by_family: Dict[str, list[FontEntry]] = defaultdict(list)
        self._cache: Dict[Tuple[str, bool, bool, str], Optional[Tuple[str, int]]] = {}
        self._indexed = False

    def resolve(self, family: str, bold: bool, italic: bool, style_name: str = "") -> Optional[Tuple[str, int]]:
        if not family:
            return None
        target_style = (style_name or "").lower().strip()
        key = (family.lower(), bool(bold), bool(italic), target_style)
        if key in self._cache:
            return self._cache[key]

        self._ensure_index()
        entries = self._fonts_by_family.get(family.lower())
        if not entries:
            normalized = self._normalize_family(family)
            if normalized:
                entries = self._fonts_by_family.get(normalized)
        if not entries:
            self._cache[key] = None
            return None

        best_entry = None
        best_score = -1

        for entry in entries:
            score = self._score_entry(entry.style, bold, italic)
            style_lower = (entry.style or "").lower()
            if target_style:
                if style_lower == target_style:
                    score += 5
                elif target_style in style_lower:
                    score += 3
            if score > best_score:
                best_entry = entry
                best_score = score

        if best_entry is None:
            best_entry = entries[0]

        result = (best_entry.path, best_entry.index)
        self._cache[key] = result
        return result

    def _font_directories(self) -> list[str]:
        dirs: list[str] = []
        if sys.platform.startswith("win"):
            windir = os.environ.get("WINDIR", "C:\\Windows")
            dirs.append(os.path.join(windir, "Fonts"))
        elif sys.platform == "darwin":
            dirs.extend([
                "/System/Library/Fonts",
                "/Library/Fonts",
                os.path.expanduser("~/Library/Fonts")
            ])
        else:
            dirs.extend([
                "/usr/share/fonts",
                "/usr/local/share/fonts",
                os.path.expanduser("~/.fonts"),
                os.path.expanduser("~/.local/share/fonts")
            ])

        return [path for path in dirs if os.path.isdir(path)]

    def _ensure_index(self) -> None:
        if self._indexed:
            return

        seen_entries = set()
        for directory in self._font_directories():
            try:
                for entry in os.scandir(directory):
                    if not entry.is_file():
                        continue
                    lower = entry.name.lower()
                    if not lower.endswith((".ttf", ".otf", ".ttc")):
                        continue
                    path = entry.path
                    if lower.endswith(".ttc"):
                        self._index_collection(path, seen_entries)
                    else:
                        self._index_font_file(path, 0, seen_entries)
            except PermissionError:
                continue
        self._indexed = True

    def _store_entry(self, family: str, entry: FontEntry) -> None:
        key = family.lower()
        self._fonts_by_family[key].append(entry)
        normalized = self._normalize_family(family)
        if normalized and normalized != key:
            self._fonts_by_family[normalized].append(entry)

    @staticmethod
    def _normalize_family(name: str) -> str:
        if not name:
            return ""
        return "".join(ch for ch in name.lower() if ch.isalnum())

    def _index_collection(self, path: str, seen_entries: set[Tuple[str, int]]) -> None:
        for index in range(10):
            if (path, index) in seen_entries:
                continue
            try:
                font = ImageFont.truetype(path, size=32, index=index)
            except OSError:
                break
            family, style = font.getname()
            if family:
                entry = FontEntry(path=path, style=style or "", index=index)
                self._store_entry(family, entry)
                seen_entries.add((path, index))

    def _index_font_file(self, path: str, index: int, seen_entries: set[Tuple[str, int]]) -> None:
        if (path, index) in seen_entries:
            return
        try:
            font = ImageFont.truetype(path, size=32, index=index)
        except OSError:
            return
        family, style = font.getname()
        if family:
            entry = FontEntry(path=path, style=style or "", index=index)
            self._store_entry(family, entry)
            seen_entries.add((path, index))

    @staticmethod
    def _score_entry(style: str, bold: bool, italic: bool) -> int:
        style_lower = (style or "").lower()
        bold_tokens = ("bold", "black", "heavy", "demi", "semi", "semibold", "medium")
        italic_tokens = ("italic", "oblique", "slant", "slanted")

        has_bold = any(token in style_lower for token in bold_tokens)
        has_italic = any(token in style_lower for token in italic_tokens)

        score = 0
        if bold == has_bold:
            score += 2
        if italic == has_italic:
            score += 2
        if bold and has_bold:
            score += 1
        if italic and has_italic:
            score += 1
        if not bold and not italic and ("regular" in style_lower or style_lower.strip() == ""):
            score += 1
        return score


class ImageProcessor:
    """图像处理器类"""
    
    # 支持的图像格式
    SUPPORTED_INPUT_FORMATS = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif')
    SUPPORTED_OUTPUT_FORMATS = ['JPEG', 'PNG']
    
    def __init__(self):
        """初始化图像处理器"""
        self.images = {}  # 存储加载的图像 {file_path: PIL.Image}
        self.current_image_path = None
        self._watermark_cache: Dict[str, Image.Image] = {}
        self._font_resolver = FontResolver()

    def apply_watermark(self, image: Image.Image, config: "WatermarkConfig") -> Image.Image:
        working = image.copy()
        original_width, original_height = working.size

        if getattr(config, "resize_enabled", False):
            resized = self.resize_image(
                working,
                getattr(config, "resize_method", "percentage"),
                getattr(config, "resize_width", original_width),
                getattr(config, "resize_height", original_height),
                getattr(config, "resize_percentage", 100),
                getattr(config, "keep_aspect_ratio", True)
            )
            if resized:
                working = resized

        image_size = working.size
        watermark_type = getattr(config, "watermark_type", "text")

        if watermark_type == "image":
            watermark_path = getattr(config, "image_watermark_path", "")
            wm_size = self._get_image_watermark_size(
                watermark_path,
                getattr(config, "image_scale", 1.0),
                getattr(config, "rotation_angle", 0)
            )

            if getattr(config, "use_custom_position", False) and getattr(config, "custom_position", None):
                position = self._clamp_position(
                    config.custom_position,
                    image_size,
                    wm_size
                )
            else:
                position = self._calculate_grid_position(
                    image_size,
                    wm_size,
                    getattr(config, "position_type", "bottom-right")
                )

            if watermark_path and os.path.exists(watermark_path):
                return self.add_image_watermark(
                    working,
                    watermark_path,
                    position,
                    getattr(config, "image_scale", 1.0),
                    getattr(config, "image_opacity", 128),
                    getattr(config, "rotation_angle", 0)
                )
            return working

        text = getattr(config, "text", "")
        if not text:
            return working

        font_path = getattr(config, "font_path", "")
        font_index = getattr(config, "font_index", 0)
        if not font_path:
            families: list[str] = []
            primary_family = getattr(config, "font_family", "")
            if primary_family:
                families.append(primary_family)
            aliases = getattr(config, "font_family_aliases", []) or []
            for alias in aliases:
                if alias and alias not in families:
                    families.append(alias)
            resolved_family, resolved = self.resolve_font_with_aliases(
                families or ["Arial"],
                getattr(config, "font_bold", True),
                getattr(config, "font_italic", False),
                getattr(config, "font_style_name", "")
            )
            if resolved:
                font_path, font_index = resolved
                if hasattr(config, "font_family") and resolved_family:
                    setattr(config, "font_family", resolved_family)
                if hasattr(config, "font_path"):
                    setattr(config, "font_path", font_path)
                if hasattr(config, "font_index"):
                    setattr(config, "font_index", font_index)

        wm_size = self._measure_text(
            text,
            getattr(config, "font_family", "Arial"),
            getattr(config, "font_size", 36),
            getattr(config, "font_bold", True),
            getattr(config, "font_italic", False),
            getattr(config, "text_stroke", False),
            getattr(config, "stroke_width", 0),
            getattr(config, "text_shadow", False),
            tuple(getattr(config, "shadow_offset", (0, 0))),
            getattr(config, "rotation_angle", 0),
            font_path,
            font_index,
            getattr(config, "font_style_name", "")
        )

        if getattr(config, "use_custom_position", False) and getattr(config, "custom_position", None):
            position = self._clamp_position(
                config.custom_position,
                image_size,
                wm_size
            )
        else:
            position = self._calculate_grid_position(
                image_size,
                wm_size,
                getattr(config, "position_type", "bottom-right")
            )

        text_color = tuple(getattr(config, "text_color", (255, 255, 255)))
        stroke_color = tuple(getattr(config, "stroke_color", (0, 0, 0)))
        shadow_offset = tuple(getattr(config, "shadow_offset", (0, 0)))

        return self.add_text_watermark(
            working,
            text,
            position,
            getattr(config, "opacity", 128),
            getattr(config, "font_size", 36),
            getattr(config, "font_family", "Arial"),
            getattr(config, "font_bold", True),
            getattr(config, "font_italic", False),
            text_color,
            getattr(config, "text_shadow", False),
            getattr(config, "text_stroke", False),
            getattr(config, "rotation_angle", 0),
            shadow_offset,
            getattr(config, "stroke_width", 0),
            stroke_color,
            font_path,
            font_index,
            getattr(config, "font_style_name", "")
        )

    @staticmethod
    def _rotated_bounds(width: int, height: int, rotation: int) -> Tuple[int, int]:
        if rotation % 360 == 0:
            return width, height
        theta = math.radians(rotation)
        cos_t = abs(math.cos(theta))
        sin_t = abs(math.sin(theta))
        rotated_width = width * cos_t + height * sin_t
        rotated_height = width * sin_t + height * cos_t
        return int(math.ceil(rotated_width)), int(math.ceil(rotated_height))

    def _measure_text(self, text: str, font_family: str, font_size: int,
                      bold: bool, italic: bool, stroke: bool,
                      stroke_width: int, shadow: bool,
                      shadow_offset: Tuple[int, int], rotation: int,
                      font_path: Optional[str] = None, font_index: int = 0,
                      style_name: str = "") -> Tuple[int, int]:
        if not text:
            return 0, 0

        font = self._load_font(font_family, font_size, bold, italic, font_path, font_index, style_name)
        dummy = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
        draw = ImageDraw.Draw(dummy)

        bbox = None
        stroke_padding = 0
        if stroke and stroke_width > 0:
            try:
                bbox = draw.textbbox(
                    (0, 0),
                    text,
                    font=font,
                    stroke_width=stroke_width,
                    stroke_fill=(0, 0, 0, 255)
                )
            except TypeError:
                try:
                    bbox = draw.textbbox(
                        (0, 0),
                        text,
                        font=font,
                        stroke_width=stroke_width
                    )
                    stroke_padding = stroke_width * 2
                except TypeError:
                    stroke_padding = stroke_width * 2
        if bbox is None:
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
            except AttributeError:
                size = draw.textsize(text, font=font)
                bbox = (0, 0, size[0], size[1])

        text_width = bbox[2] - bbox[0] + stroke_padding
        text_height = bbox[3] - bbox[1] + stroke_padding

        offset_x, offset_y = shadow_offset if shadow else (0, 0)
        extra_left = max(0, -offset_x)
        extra_top = max(0, -offset_y)
        extra_right = max(0, offset_x)
        extra_bottom = max(0, offset_y)

        canvas_width = text_width + extra_left + extra_right
        canvas_height = text_height + extra_top + extra_bottom

        return self._rotated_bounds(canvas_width, canvas_height, rotation)

    def _get_image_watermark_size(self, watermark_path: str, scale: float,
                                  rotation: int) -> Tuple[int, int]:
        if not watermark_path or not os.path.exists(watermark_path):
            return 0, 0

        if watermark_path not in self._watermark_cache:
            try:
                self._watermark_cache[watermark_path] = Image.open(watermark_path).convert('RGBA')
            except Exception:
                return 0, 0

        wm_img = self._watermark_cache[watermark_path]
        scale = max(0.05, min(scale, 10.0))
        width = max(1, int(wm_img.width * scale))
        height = max(1, int(wm_img.height * scale))
        return self._rotated_bounds(width, height, rotation)

    @staticmethod
    def _rotated_corners(anchor_x: float, anchor_y: float, width: int, height: int,
                         position: Tuple[int, int], rotation: int) -> Tuple[Tuple[float, float], ...]:
        cx = position[0]
        cy = position[1]

        left = -anchor_x
        top = -anchor_y
        right = left + width
        bottom = top + height

        corners = [
            (left, top),
            (right, top),
            (right, bottom),
            (left, bottom)
        ]

        if rotation % 360 == 0:
            return tuple((cx + x, cy + y) for x, y in corners)

        theta = math.radians(rotation)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        rotated = []
        for x, y in corners:
            rotated_x = x * cos_t - y * sin_t
            rotated_y = x * sin_t + y * cos_t
            rotated.append((cx + rotated_x, cy + rotated_y))

        return tuple(rotated)

    @staticmethod
    def _calculate_grid_position(image_size: Tuple[int, int], watermark_size: Tuple[int, int],
                                 position_type: str, margin: int = 20) -> Tuple[int, int]:
        img_width, img_height = image_size
        wm_width, wm_height = watermark_size

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

    @staticmethod
    def _clamp_position(position: Union[Tuple[float, float], Tuple[int, int]],
                        image_size: Tuple[int, int],
                        watermark_size: Tuple[int, int]) -> Tuple[int, int]:
        if not position:
            img_w, img_h = image_size
            return img_w // 2, img_h // 2

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

        x = max(min_x, min(position[0], max_x))
        y = max(min_y, min(position[1], max_y))
        return int(round(x)), int(round(y))
        
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
    
    def _load_font(self, font_family: str, font_size: int, bold: bool, italic: bool,
                   font_path: Optional[str] = None, font_index: int = 0,
                   style_name: str = "") -> ImageFont.FreeTypeFont:
        """尝试根据字体族和样式加载字体，失败时回退到系统字体"""
        index = max(0, int(font_index or 0))

        # 如果提供了字体路径，先验证它是否匹配所需样式
        if font_path:
            try:
                test_font = ImageFont.truetype(font_path, 32, index=index)
                actual_family, actual_style = test_font.getname()
                actual_style_lower = (actual_style or "").lower()
                
                # 检查加载的字体是否真的包含所需样式
                has_bold = any(token in actual_style_lower for token in ("bold", "black", "heavy", "gras", "fett"))
                has_italic = any(token in actual_style_lower for token in ("italic", "oblique", "slant", "italique", "kursiv"))
                
                style_matches = True
                if bold and not has_bold:
                    style_matches = False
                    print(f"Warning: Font path {font_path} does not contain Bold style (found: {actual_style})")
                if italic and not has_italic:
                    style_matches = False
                    print(f"Warning: Font path {font_path} does not contain Italic style (found: {actual_style})")
                
                # 如果样式匹配或者不需要特殊样式，使用该字体
                if style_matches or (not bold and not italic):
                    return ImageFont.truetype(font_path, font_size, index=index)
                else:
                    print(f"Font path {font_path} style mismatch, re-resolving for bold={bold}, italic={italic}")
            except Exception as e:
                print(f"Failed to load font from path {font_path}: {e}")

        # 重新解析或首次解析字体
        resolved = self._font_resolver.resolve(font_family, bold, italic, style_name)
        if resolved:
            path, resolved_index = resolved
            try:
                loaded = ImageFont.truetype(path, font_size, index=resolved_index)
                print(f"Loaded font: {path} (index={resolved_index}) for {font_family} bold={bold} italic={italic}")
                return loaded
            except Exception as e:
                print(f"Failed to load resolved font {path}: {e}")

        base = font_family or "Arial"
        styled_variants = []
        if bold and italic:
            styled_variants.extend([f"{base} Bold Italic", f"{base}-BoldItalic", f"{base}BI"])
        if bold and not italic:
            styled_variants.extend([f"{base} Bold", f"{base}-Bold", f"{base}B"])
        if italic and not bold:
            styled_variants.extend([f"{base} Italic", f"{base}-Italic", f"{base}I"])
        styled_variants.append(base)

        for variant in styled_variants:
            for suffix in ("", ".ttf", ".otf", ".ttc"):
                try:
                    return ImageFont.truetype(variant + suffix, font_size)
                except Exception:
                    continue

        for fallback in ("arial.ttf", "Helvetica.ttc"):
            try:
                return ImageFont.truetype(fallback, font_size)
            except Exception:
                continue

        return ImageFont.load_default()

    def resolve_font_face(self, font_family: str, bold: bool, italic: bool,
                          style_name: str = "") -> Optional[Tuple[str, int]]:
        """解析字体的真实路径和索引，若无法解析则返回None"""
        return self._font_resolver.resolve(font_family, bold, italic, style_name)

    def resolve_font_with_aliases(self, families: Union[str, List[str]], bold: bool, italic: bool,
                                  style_name: str = "") -> Tuple[Optional[str], Optional[Tuple[str, int]]]:
        """尝试使用多个字体别名解析字体，返回成功的家族名与路径索引"""
        seen: set[str] = set()
        if isinstance(families, str):
            candidates = [families]
        else:
            candidates = list(families)

        for name in candidates:
            if not name:
                continue
            if name.lower() in seen:
                continue
            seen.add(name.lower())
            result = self._font_resolver.resolve(name, bold, italic, style_name)
            if result:
                return name, result

            normalized = self._normalize_family_name(name)
            if normalized and normalized not in seen:
                seen.add(normalized)
                result = self._font_resolver.resolve(normalized, bold, italic, style_name)
                if result:
                    return name, result

        return None, None

    @staticmethod
    def _normalize_family_name(name: str) -> str:
        return "".join(ch for ch in name.lower() if ch.isalnum())

    def measure_text(self, text: str, font_family: str, font_size: int,
                     bold: bool, italic: bool, stroke: bool, stroke_width: int,
                     shadow: bool, shadow_offset: Tuple[int, int], rotation: int,
                     font_path: Optional[str] = None, font_index: int = 0,
                     style_name: str = "") -> Tuple[int, int]:
        """公开的文本尺寸测量接口，便于UI复用相同逻辑"""
        return self._measure_text(
            text,
            font_family,
            font_size,
            bold,
            italic,
            stroke,
            stroke_width,
            shadow,
            shadow_offset,
            rotation,
            font_path,
            font_index,
            style_name
        )

    def add_text_watermark(self, image: Image.Image, text: str, position: Tuple[int, int],
                          opacity: int = 128, font_size: int = 36, font_family: str = "Arial",
                          bold: bool = True, italic: bool = False, color: tuple = (255, 255, 255),
                          shadow: bool = False, stroke: bool = False, rotation: int = 0,
                          shadow_offset: Tuple[int, int] = (2, 2), stroke_width: int = 1,
                          stroke_color: tuple = (0, 0, 0), font_path: Optional[str] = None,
                          font_index: int = 0, style_name: str = "") -> Image.Image:
        """添加高级文本水印"""
        try:
            base_image = image.convert('RGBA') if image.mode != 'RGBA' else image.copy()
            font = self._load_font(font_family, font_size, bold, italic, font_path, font_index, style_name)

            dummy = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
            dummy_draw = ImageDraw.Draw(dummy)

            bbox = None
            padding = 0
            if stroke and stroke_width > 0:
                try:
                    bbox = dummy_draw.textbbox(
                        (0, 0),
                        text,
                        font=font,
                        stroke_width=stroke_width,
                        stroke_fill=(*stroke_color[:3], opacity)
                    )
                except TypeError:
                    try:
                        bbox = dummy_draw.textbbox(
                            (0, 0),
                            text,
                            font=font,
                            stroke_width=stroke_width
                        )
                        padding = stroke_width * 2
                    except TypeError:
                        padding = stroke_width * 2
            if bbox is None:
                try:
                    bbox = dummy_draw.textbbox((0, 0), text, font=font)
                except AttributeError:
                    size = dummy_draw.textsize(text, font=font)
                    bbox = (0, 0, size[0], size[1])

            text_width = (bbox[2] - bbox[0]) + padding
            text_height = (bbox[3] - bbox[1]) + padding

            offset_from_origin_x = -bbox[0]
            offset_from_origin_y = -bbox[1]

            offset_x, offset_y = shadow_offset if shadow else (0, 0)
            extra_left = max(0, -offset_x)
            extra_top = max(0, -offset_y)
            extra_right = max(0, offset_x)
            extra_bottom = max(0, offset_y)

            canvas_width = text_width + extra_left + extra_right
            canvas_height = text_height + extra_top + extra_bottom

            canvas = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(canvas)
            text_pos = (
                extra_left + offset_from_origin_x,
                extra_top + offset_from_origin_y
            )

            def manual_stroke(target_draw, base_position, alpha):
                if not (stroke and stroke_width > 0):
                    return
                stroke_rgba = (*stroke_color[:3], alpha)
                radius = max(1, stroke_width)
                for dx in range(-radius, radius + 1):
                    for dy in range(-radius, radius + 1):
                        if dx == 0 and dy == 0:
                            continue
                        target_draw.text(
                            (base_position[0] + dx, base_position[1] + dy),
                            text,
                            font=font,
                            fill=stroke_rgba
                        )

            def render_text(target_draw, base_position, fill_color, apply_stroke):
                if apply_stroke and stroke and stroke_width > 0:
                    try:
                        target_draw.text(
                            base_position,
                            text,
                            font=font,
                            fill=fill_color,
                            stroke_width=stroke_width,
                            stroke_fill=(*stroke_color[:3], fill_color[3])
                        )
                        return
                    except TypeError:
                        try:
                            target_draw.text(
                                base_position,
                                text,
                                font=font,
                                fill=fill_color,
                                stroke_width=stroke_width
                            )
                            return
                        except TypeError:
                            manual_stroke(target_draw, base_position, fill_color[3])
                            target_draw.text(base_position, text, font=font, fill=fill_color)
                            return
                target_draw.text(base_position, text, font=font, fill=fill_color)

            if shadow:
                shadow_color_rgba = (0, 0, 0, min(255, opacity))
                render_text(
                    draw,
                    (text_pos[0] + offset_x, text_pos[1] + offset_y),
                    shadow_color_rgba,
                    apply_stroke=False
                )

            text_color_rgba = (*color[:3], opacity)
            render_text(draw, text_pos, text_color_rgba, apply_stroke=True)

            if rotation:
                canvas = canvas.rotate(rotation, resample=Image.BICUBIC, expand=True)

            dest_x = int(round(position[0] - canvas.width / 2))
            dest_y = int(round(position[1] - canvas.height / 2))

            src_left = max(0, -dest_x)
            src_top = max(0, -dest_y)
            src_right = min(canvas.width, base_image.width - dest_x)
            src_bottom = min(canvas.height, base_image.height - dest_y)

            if src_left >= src_right or src_top >= src_bottom:
                return base_image

            cropped = canvas.crop((src_left, src_top, src_right, src_bottom))

            overlay = Image.new('RGBA', base_image.size, (0, 0, 0, 0))
            overlay.alpha_composite(
                cropped,
                dest=(max(dest_x, 0), max(dest_y, 0))
            )

            return Image.alpha_composite(base_image, overlay)

        except Exception as e:
            print(f"添加文本水印失败: {e}")
            return image

    def add_image_watermark(self, image: Image.Image, watermark_path: str,
                            position: Tuple[int, int], scale: float = 1.0,
                            opacity: int = 128, rotation: int = 0) -> Image.Image:
        """添加图片水印"""
        try:
            if not watermark_path or not os.path.exists(watermark_path):
                return image

            if watermark_path not in self._watermark_cache:
                wm_img = Image.open(watermark_path).convert('RGBA')
                self._watermark_cache[watermark_path] = wm_img
            else:
                wm_img = self._watermark_cache[watermark_path]

            watermark = wm_img.copy()
            scale = max(0.05, min(scale, 10.0))
            new_size = (max(1, int(watermark.width * scale)),
                        max(1, int(watermark.height * scale)))
            watermark = watermark.resize(new_size, Image.Resampling.LANCZOS)

            if opacity < 255:
                alpha = watermark.split()[-1]
                alpha = alpha.point(lambda p: int(p * (opacity / 255)))
                watermark.putalpha(alpha)

            if rotation:
                watermark = watermark.rotate(rotation, resample=Image.BICUBIC, expand=True)

            base_image = image.convert('RGBA') if image.mode != 'RGBA' else image.copy()
            overlay = Image.new('RGBA', base_image.size, (0, 0, 0, 0))

            dest_x = int(round(position[0] - watermark.width / 2))
            dest_y = int(round(position[1] - watermark.height / 2))
            overlay.alpha_composite(watermark, dest=(dest_x, dest_y))

            return Image.alpha_composite(base_image, overlay)

        except Exception as e:
            print(f"添加图片水印失败: {e}")
            return image
    
    def calculate_position(self, image_size: Tuple[int, int], text: str,
                          position_type: str, font_size: int = 36,
                          font_family: str = "Arial", bold: bool = True,
                          italic: bool = False, stroke: bool = False,
                          stroke_width: int = 0, shadow: bool = False,
                          shadow_offset: Tuple[int, int] = (0, 0),
                          rotation: int = 0, style_name: str = "") -> Tuple[int, int]:
        watermark_size = self._measure_text(
            text or "",
            font_family,
            font_size,
            bold,
            italic,
            stroke,
            stroke_width,
            shadow,
            shadow_offset,
            rotation,
            style_name=style_name
        )
        return self._calculate_grid_position(image_size, watermark_size, position_type)
    
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

    def resize_image(self, image: Image.Image, method: str, target_width: int,
                     target_height: int, percentage: int, keep_aspect: bool) -> Image.Image:
        """按照指定方式调整图像大小"""
        try:
            current_width, current_height = image.size

            if method == "percentage":
                scale = max(1, percentage) / 100.0
                new_width = max(1, int(current_width * scale))
                new_height = max(1, int(current_height * scale))
            elif method == "width":
                new_width = max(1, target_width)
                if keep_aspect:
                    ratio = new_width / current_width
                    new_height = max(1, int(current_height * ratio))
                else:
                    new_height = max(1, target_height if target_height > 0 else current_height)
            elif method == "height":
                new_height = max(1, target_height)
                if keep_aspect:
                    ratio = new_height / current_height
                    new_width = max(1, int(current_width * ratio))
                else:
                    new_width = max(1, target_width if target_width > 0 else current_width)
            else:
                return image

            if new_width == current_width and new_height == current_height:
                return image

            return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        except Exception as e:
            print(f"调整图像尺寸失败: {e}")
            return image
            
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
