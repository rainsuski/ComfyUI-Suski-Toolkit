# ==============================================================================
# 项目名称: ComfyUI-Suski-Toolkit
# 文件路径: core/path_formatter.py
# 功能说明: 动态文件路径与占位符解析引擎：
#          支持 %{节点标题}.属性名% 精确寻址、正向遍历首项兜底抓取、
#          动态时间格式化、图像尺寸与 %count:N% 批次安全序列号。
# ==============================================================================

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import folder_paths


class PathFormatter:
    """路径模板与上下文动态占位符解析引擎"""

    @staticmethod
    def sanitize_component(name: str) -> str:
        """跨平台文件名安全清洗，过滤操作系统非法保留字符"""
        cleaned = re.sub(r'[\\/:*?"<>|]', "_", str(name)).strip(". ")
        return cleaned or "unnamed"

    @classmethod
    def resolve_title_mapping(
        cls, prompt: Optional[Dict[str, Any]], extra_pnginfo: Optional[Dict[str, Any]]
    ) -> Dict[str, str]:
        """建立 节点标题(Title) -> 节点ID(node_id) 的反向映射字典"""
        title_to_id: Dict[str, str] = {}

        # 1. 优先扫描原生 workflow 拓扑中的可视化自定义标题
        if extra_pnginfo and isinstance(extra_pnginfo, dict):
            workflow = extra_pnginfo.get("workflow", {})
            if isinstance(workflow, dict):
                nodes = workflow.get("nodes", [])
                if isinstance(nodes, list):
                    for n in nodes:
                        if not isinstance(n, dict):
                            continue
                        nid = str(n.get("id", ""))
                        title = str(
                            n.get("title")
                            or n.get("properties", {}).get("Node name for S&R")
                            or ""
                        ).strip()
                        if title and nid:
                            title_to_id[title] = nid

        # 2. 兜底扫描 prompt 结构中可能携带的 _meta.title
        if prompt and isinstance(prompt, dict):
            for nid, node_data in prompt.items():
                if not isinstance(node_data, dict):
                    continue
                meta = node_data.get("_meta", {})
                if isinstance(meta, dict) and meta.get("title"):
                    title_to_id[str(meta["title"]).strip()] = str(nid)

        return title_to_id

    @classmethod
    def scan_first_model(cls, prompt: Optional[Dict[str, Any]]) -> str:
        """正向遍历抓取遇到的第一个模型加载节点的底模名称"""
        if not prompt or not isinstance(prompt, dict):
            return "unknown_model"

        model_classes = (
            "CheckpointLoaderSimple",
            "CheckpointLoader",
            "UNETLoader",
            "unCLIPCheckpointLoader",
        )

        for node in prompt.values():
            if not isinstance(node, dict):
                continue
            ctype = node.get("class_type", "")
            inputs = node.get("inputs", {})
            if not isinstance(inputs, dict):
                continue

            if ctype in model_classes or "ckpt_name" in inputs or "unet_name" in inputs:
                raw_model = inputs.get("ckpt_name") or inputs.get("unet_name")
                if raw_model:
                    return Path(str(raw_model)).stem

        return "unknown_model"

    @classmethod
    def scan_first_sampler(cls, prompt: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """正向遍历抓取遇到的第一个采样器节点的生成配置"""
        default_res = {
            "seed": -1,
            "steps": 0,
            "cfg": 0.0,
            "sampler": "unknown",
            "scheduler": "unknown",
        }
        if not prompt or not isinstance(prompt, dict):
            return default_res

        sampler_classes = (
            "KSampler",
            "KSamplerAdvanced",
            "SamplerCustom",
            "KSamplerWithRefiner",
        )

        for node in prompt.values():
            if not isinstance(node, dict):
                continue
            ctype = node.get("class_type", "")
            inputs = node.get("inputs", {})
            if not isinstance(inputs, dict):
                continue

            is_sampler = (
                ctype in sampler_classes
                or ("seed" in inputs and "steps" in inputs and "cfg" in inputs)
                or ("noise_seed" in inputs and "steps" in inputs)
            )

            if is_sampler:
                seed_val = inputs.get("seed", inputs.get("noise_seed", -1))
                steps_val = inputs.get("steps", inputs.get("start_at_step", 0))
                cfg_val = inputs.get("cfg", 0.0)
                sampler_val = inputs.get(
                    "sampler_name", inputs.get("sampler", "unknown")
                )
                scheduler_val = inputs.get("scheduler", "unknown")

                try:
                    seed_val = int(seed_val)
                except Exception:
                    seed_val = -1

                try:
                    steps_val = int(steps_val)
                except Exception:
                    steps_val = 0

                try:
                    cfg_val = round(float(cfg_val), 2)
                except Exception:
                    cfg_val = 0.0

                return {
                    "seed": seed_val,
                    "steps": steps_val,
                    "cfg": cfg_val,
                    "sampler": str(sampler_val),
                    "scheduler": str(scheduler_val),
                }

        return default_res

    @classmethod
    def get_property_by_title(
        cls,
        title: str,
        attr: str,
        title_to_id: Dict[str, str],
        prompt: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        """通过节点自定义标题定位节点并提取指定属性"""
        if not prompt or title not in title_to_id:
            return None

        nid = title_to_id[title]
        node = prompt.get(nid)
        if not isinstance(node, dict):
            return None

        inputs = node.get("inputs", {})
        if not isinstance(inputs, dict):
            return None

        if attr not in inputs:
            return None

        val = inputs[attr]
        # 解包单元素列表或模型元组连线
        if isinstance(val, (list, tuple)):
            val = val[0] if len(val) > 0 else ""

        # 若提取的值为文件路径，自动取其主干名称
        str_val = str(val)
        if any(
            str_val.lower().endswith(ext)
            for ext in (".safetensors", ".ckpt", ".pt", ".bin")
        ):
            return Path(str_val).stem

        return str_val

    @classmethod
    def calculate_count(
        cls, target_dir: Path, prefix_stem: str, default_width: int = 4
    ) -> Tuple[int, int]:
        """扫描目标目录下匹配同名模式的文件，计算自增起始序号"""
        if not target_dir.exists():
            return 1, default_width

        # 将 %count% 占位符转化为正则匹配提取数字
        pattern_str = re.escape(prefix_stem)
        count_regex = re.compile(r"\\%count(?:\\:\s*(\d+))?\\%", re.IGNORECASE)

        match = count_regex.search(pattern_str)
        if not match:
            return 1, default_width

        width = int(match.group(1)) if match.group(1) else default_width
        file_regex_str = (
            "^" + count_regex.sub(r"(\d+)", pattern_str) + r"(?:\.[a-zA-Z0-9]+)?$"
        )
        file_pattern = re.compile(file_regex_str, re.IGNORECASE)

        existing_numbers = []
        try:
            for item in target_dir.iterdir():
                if item.is_file():
                    m = file_pattern.match(item.name)
                    if m:
                        try:
                            existing_numbers.append(int(m.group(1)))
                        except Exception:
                            pass
        except Exception:
            pass

        next_val = (max(existing_numbers) + 1) if existing_numbers else 1
        return next_val, width

    @classmethod
    def format_path_and_stem(
        cls,
        template: str,
        width: int,
        height: int,
        batch_idx: int,
        prompt: Optional[Dict[str, Any]],
        extra_pnginfo: Optional[Dict[str, Any]],
        base_count: Optional[int] = None,
    ) -> Tuple[Path, str, int]:
        """完整解析路径模板，返回 (绝对目标目录, 最终文件主名, 下一可用计数)"""
        now = datetime.now()
        title_to_id = cls.resolve_title_mapping(prompt, extra_pnginfo)
        first_sampler = cls.scan_first_sampler(prompt)
        first_model = cls.scan_first_model(prompt)

        # 阶段 1: 解析精准寻址规则 %{节点标题}.属性名% 与 %节点标题.属性名% (含可选 :N 截断)
        def replace_title_prop(match: re.Match) -> str:
            title = match.group(1).strip()
            attr = match.group(2).strip()
            slice_len = match.group(3)

            raw_val = cls.get_property_by_title(title, attr, title_to_id, prompt)
            if raw_val is None:
                raw_val = "unknown"

            if slice_len is not None and slice_len.isdigit():
                raw_val = raw_val[: int(slice_len)]

            return cls.sanitize_component(raw_val)

        # 匹配 %{标题}.属性% 或 %标题.属性% (含可选冒号截断)
        resolved = re.sub(
            r"%\{?([^%.:{}]+)\}?\.([^%.:{}]+)(?::\s*(\d+))?%",
            replace_title_prop,
            template,
        )

        # 阶段 2: 解析通用基础占位符
        token_map = {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H%M%S"),
            "width": str(width),
            "height": str(height),
            "batch_idx": f"{batch_idx:02d}",
            "model": first_model,
            "seed": str(first_sampler["seed"]),
            "steps": str(first_sampler["steps"]),
            "cfg": str(first_sampler["cfg"]),
            "sampler": first_sampler["sampler"],
            "scheduler": first_sampler["scheduler"],
        }

        def replace_basic_token(match: re.Match) -> str:
            token_key = match.group(1).lower()
            param = match.group(2)

            if token_key == "count":
                return match.group(0)

            # 自定义时间格式 %date:format%
            if token_key == "date" and param:
                fmt = param.strip()
                fmt = fmt.replace("yyyy", "%Y").replace("yy", "%y")
                fmt = fmt.replace("MM", "%m").replace("dd", "%d")
                fmt = fmt.replace("HH", "%H").replace("mm", "%M").replace("ss", "%S")
                try:
                    return cls.sanitize_component(now.strftime(fmt))
                except Exception:
                    return cls.sanitize_component(now.strftime("%Y-%m-%d"))

            val = token_map.get(token_key, match.group(0))
            if param is not None and param.strip().isdigit() and token_key in token_map:
                val = val[: int(param.strip())]

            return cls.sanitize_component(str(val))

        resolved = re.sub(
            r"%([a-zA-Z0-9_]+)(?::\s*([^%]+))?%", replace_basic_token, resolved
        )
        resolved = resolved.replace("\\", "/")
        parts = [p.strip() for p in resolved.split("/") if p.strip()]

        current_output_dir = Path(folder_paths.get_output_directory()).resolve()

        if not parts:
            target_dir = current_output_dir
            prefix_stem = f"suski_{now.strftime('%Y%m%d_%H%M%S')}"
        elif len(parts) == 1:
            target_dir = current_output_dir
            prefix_stem = parts[0]
        else:
            sub_dirs = [cls.sanitize_component(p) for p in parts[:-1]]
            target_dir = current_output_dir.joinpath(*sub_dirs).resolve()
            prefix_stem = parts[-1]

        target_dir.mkdir(parents=True, exist_ok=True)

        # 阶段 3: 提取并计算 %count:N%
        count_pattern = re.compile(r"%count(?:\s*:\s*(\d+))?%", re.IGNORECASE)
        final_stem = prefix_stem
        next_count_val = base_count if base_count is not None else 1

        if count_pattern.search(prefix_stem):
            if base_count is None:
                next_count_val, _ = cls.calculate_count(
                    target_dir, prefix_stem, default_width=4
                )

            def replace_count(match: re.Match) -> str:
                width_arg = match.group(1)
                digits = (
                    int(width_arg.strip())
                    if width_arg and width_arg.strip().isdigit()
                    else 4
                )
                return f"{next_count_val:0{digits}d}"

            final_stem = count_pattern.sub(replace_count, prefix_stem)
            next_count_val += 1

        final_stem = cls.sanitize_component(final_stem)
        return target_dir, final_stem, next_count_val
