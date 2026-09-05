# ==============================================================================
# 项目名称: ComfyUI-Suski-Toolkit
# 文件路径: nodes/io/__init__.py
# 功能说明: IO 与持久化模块节点集中导出
# ==============================================================================

from .conditional_save import SuskiConditionalSaveImage

NODE_CLASS_MAPPINGS = {
    "SuskiConditionalSaveImage": SuskiConditionalSaveImage,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SuskiConditionalSaveImage": "Conditional Save Image (Suski)",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
