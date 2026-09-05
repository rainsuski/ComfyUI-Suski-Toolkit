# ==============================================================================
# 项目名称: ComfyUI-Suski-Toolkit
# 文件路径: nodes/io/conditional_save.py
# 功能说明: 条件图像保存节点：
#          - 支持通过 Boolean 开关控制落盘保存与静默跳过 (Silent Skip)；
#          - 100% 完整保留与透传 extra_pnginfo (含 DataflowProbe 血统探针) 与原生工作流；
#          - 完整集成 PathFormatter 动态占位符解析；
#          - 原样透传 IMAGE 图像张量，支持无缝作为中继管道节点。
# ==============================================================================

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import torch
from PIL import Image, PngImagePlugin

import folder_paths

from ...core.path_formatter import PathFormatter

logger = logging.getLogger("SuskiToolkit.ConditionalSave")


class SuskiConditionalSaveImage:
    """条件图像保存节点 (Probe-Safe & Pipeline Pass-Through)"""

    def __init__(self):
        self.output_dir = Path(folder_paths.get_output_directory()).resolve()
        self.type = "output"
        self.prefix_append = ""

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "images": ("IMAGE",),
                "enabled": (
                    "BOOLEAN",
                    {"default": True, "label_on": "Enabled", "label_off": "Disabled"},
                ),
                "filename_prefix": ("STRING", {"default": "staging/ComfyUI"}),
                "lineage_key": ("STRING", {"default": "dataflow_lineage"}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("IMAGE",)
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "Suski/IO"

    def save_images(
        self,
        images: torch.Tensor,
        enabled: bool = True,
        filename_prefix: str = "staging/ComfyUI",
        lineage_key: str = "dataflow_lineage",
        prompt: Any = None,
        extra_pnginfo: Any = None,
    ) -> Dict[str, Any]:
        """核心保存与路由分发逻辑"""
        # 分支 1: 未启用时安全阻断，静默跳过，原样透传张量且不产生磁盘与UI冗余
        if not enabled:
            logger.info("ConditionalSave: 当前处于禁用状态 (Disabled)，静默跳过落盘")
            return {"ui": {"images": []}, "result": (images,)}

        # 分支 2: 启用保存，执行无损元数据封装与动态占位符落盘
        results: List[Dict[str, Any]] = []
        base_count: Any = None

        for batch_number, image_tensor in enumerate(images):
            # 将 PyTorch 张量转换为标准 8-bit RGB PIL Image
            i = 255.0 * image_tensor.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))

            # 1. 解析目标目录、文件名与批次自增序号
            target_dir, stem, base_count = PathFormatter.format_path_and_stem(
                template=filename_prefix,
                width=img.width,
                height=img.height,
                batch_idx=batch_number,
                prompt=prompt,
                extra_pnginfo=extra_pnginfo,
                base_count=base_count,
            )

            target_filename = f"{stem}.png"
            target_filepath = target_dir / target_filename

            # 2. 构造 100% 原生级 PNG 元数据文本块 (Metadata Preservation)
            metadata = PngImagePlugin.PngInfo()

            if prompt is not None:
                metadata.add_text("prompt", json.dumps(prompt, ensure_ascii=False))

            if extra_pnginfo is not None and isinstance(extra_pnginfo, dict):
                # 遍历并继承 extra_pnginfo 下的所有键（包含 workflow、自定义键等）
                for key, val in extra_pnginfo.items():
                    if key == lineage_key:
                        # 确保探针数据被标准序列化
                        lineage_str = (
                            json.dumps(val, ensure_ascii=False)
                            if not isinstance(val, str)
                            else val
                        )
                        metadata.add_text(key, lineage_str)
                    else:
                        metadata.add_text(
                            key,
                            json.dumps(val, ensure_ascii=False)
                            if not isinstance(val, str)
                            else val,
                        )

            # 3. 落盘写入文件
            try:
                img.save(
                    target_filepath,
                    pnginfo=metadata,
                    compress_level=4,
                )
            except Exception as e:
                logger.error(
                    f"保存图像文件失败 [{target_filepath}]: {e}", exc_info=True
                )
                continue

            # 4. 计算相对于 ComfyUI output 的子目录用于前端响应
            try:
                rel_path = target_dir.relative_to(self.output_dir)
                subfolder = str(rel_path) if str(rel_path) != "." else ""
            except Exception:
                subfolder = ""

            results.append(
                {
                    "filename": target_filename,
                    "subfolder": subfolder,
                    "type": self.type,
                }
            )

        return {"ui": {"images": results}, "result": (images,)}
