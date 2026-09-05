# ==============================================================================
# 项目名称: ComfyUI-Suski-Toolkit
# 文件路径: nodes/__init__.py
# 功能说明: 自动聚合各分类子模块（io, flow, logic 等）的节点映射调度器
# ==============================================================================

from .io import NODE_CLASS_MAPPINGS as IO_CLASS_MAPPINGS
from .io import NODE_DISPLAY_NAME_MAPPINGS as IO_DISPLAY_NAME_MAPPINGS

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

# 聚合 IO 类模块节点
NODE_CLASS_MAPPINGS.update(IO_CLASS_MAPPINGS)
NODE_DISPLAY_NAME_MAPPINGS.update(IO_DISPLAY_NAME_MAPPINGS)

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
