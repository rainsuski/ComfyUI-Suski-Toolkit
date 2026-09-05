# ComfyUI-Suski-Toolkit

**Suski 的个人扩展工具包（什么都可能往里面塞的大杂烩）**

---

## 💡 简介

这是一个轻量级、模块化的 ComfyUI 实用小工具集合。

在日常搭建复杂工作流、调试模型或跑图时遇到了原生节点解决起来别扭、或者缺少顺手小功能的痛点，就会被做成小组件扔进这个包里，随着使用持续添砖加瓦。

---

## 🧩 组件清单

### 1. Conditional Save Image (Suski)

* **分类目录**：`Suski/IO`
* **节点显示名**：`Conditional Save Image (Suski)`

#### 作用

带布尔开关（Boolean）的图像保存节点。

* 开关开启时：正常保存落盘，完整无损保留 ComfyUI 原生工作流与探针元数据；
* 开关关闭时：**完全静默跳过**，不写磁盘、不报异常、不生成冗余预览；
* 带有图像直通输出（Pass-Through），可以直接插在工作流中间作为中继，不影响下游继续连线。

#### 使用方式与须知

1. **开关控制 (`enabled`)**：
   * 默认为 `True`。可直接点击切换，或连接布尔变量、Switch 开关进行条件化保存。
2. **丰富的路径与命名占位符 (`filename_prefix`)**：
   * 支持多级目录直接创建（如 `staging/%date%/%model%`）；
   * **时间与尺寸**：`%date%`、`%time%`、`%date:yyyy-MM-dd_HH-mm%`、`%width%`、`%height%`；
   * **序号自动对齐**：`%count:4%`（自动递增并补零为 `0001`，数字可改）；
   * **默认参数抓取**：`%model%`（取首个底模）、`%seed%`、`%steps%`、`%cfg%`、`%sampler%`；
   * **精准抓取任意节点属性 (`%{节点标题}.属性名%`)**：
     * 可直接输入你给节点起的标题来精确读取属性。例如：
       * `%底图采样器.seed%` ➔ 获取标题为“底图采样器”节点的 seed 属性；
       * `%{主模型}.ckpt_name%` ➔ 获取主模型文件名；
       * 支持截断长度，如 `%正向词.text:20%` 截取前 20 字。
3. **探针数据对接 (`lineage_key`)**：
   * 默认为 `dataflow_lineage`。如果你的工作流配合了 `ComfyUI-Suski-Dataflow-Probe` 且自定义了注入键名，在此处填入相同键名即可完整保留多阶段时序血统。
4. **输出槽位 (`IMAGE`)**：
   * 输出原样透传的输入图像，方便保存后继续连后处理节点。

---

## 📦 安装方式

进入 ComfyUI 的插件目录，使用 Git 克隆本仓库并重启 ComfyUI：

```bash
cd ComfyUI/custom_nodes/
git clone https://github.com/rainsuski/ComfyUI-Suski-Toolkit.git
```

*无任何额外重型第三方依赖，开箱即用。*

---

## 📄 开源许可

本项目基于 [MIT License](LICENSE) 开源发布。
