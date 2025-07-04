# MiniMax 反推打标工具

一个高效的**图形界面**批量图片提示词生成工具，利用 MiniMax AI 的视觉理解能力为图片生成英文/中文提示词，并**自动生成同名 TXT 文件**，即刻可用于 LoRA / SD 训练。

## ✨ 更新亮点 0.8.9（2025-07-04）
1. **🆕 完整工作流程优化**：批量处理结束不再立即生成 TXT，全部写入 `manifest.csv`，导出阶段一次性生成 TXT。
2. **🆕 批量重新生成**：支持选定多张图片一次性重新生成提示词，便于对比和批量修正。
3. **🆕 UI 体验全面升级**：
   - 列表项使用 Qt 内置高亮 + CSS，彻底解决黑底闪烁问题
   - 当前图片文件名在预览面板顶端突出显示
   - 全选 / 复选框三态逻辑完善，防止部分选中状态下无法全选
4. **✅ 操作按钮逻辑修复**：无需重复选图即可保存/通过/拒绝当前图片。
5. **✅ 稳定性提升**：线程清理、错误处理更健壮，防止 UI 卡死。

> 0.8.9 已完成全部核心流程和 UI 交互测试，推荐升级！

## ⚠️ 重要说明

**当前状态**：经过测试发现，MiniMax 官方 API 中的 `abab6.5s-chat` 模型**暂时不支持图片理解功能**。虽然 MiniMax 已经发布了 `MiniMax-VL-01` 视觉模型，但该模型目前仅通过 Hugging Face 开源提供，尚未集成到官方 API 服务中。

**✅ 立即可用的解决方案 - OpenRouter**：
我们已集成 OpenRouter 代理服务支持，您可以立即使用具备图片理解功能的 MiniMax-01 模型：

1. **注册 OpenRouter**：访问 [OpenRouter](https://openrouter.ai) 获取 API Key
2. **配置环境变量**：
   ```bash
   export OPENROUTER_API_KEY="your_openrouter_key"
   export OPENROUTER_MODEL_NAME="minimax/minimax-01"  # 可选，默认值
   ```
3. **正常使用**：程序会自动检测并使用 OpenRouter 服务

**其他解决方案**：
1. **等待官方支持**：MiniMax 可能会在未来将 Vision 功能集成到 API 中
2. **本地部署**：下载 MiniMax-VL-01 模型进行本地部署（需要大量计算资源）

## 功能特性

- 🚀 **批量处理**：支持批量处理大量图片文件
- 🎯 **智能分块**：根据文件大小自动分批，优化 API 调用效率  
- 🔄 **错误重试**：内置重试机制，确保处理成功率
- 📊 **进度追踪**：实时显示处理进度和状态
- 💾 **结果导出**：自动生成 CSV 格式的处理结果
- ⚙️ **灵活配置**：支持多种配置方式和参数调整
- GUI 批量处理 | 直观的图形界面，零命令行门槛
- OpenRouter 模型 | 默认使用 `minimax/minimax-01`（视觉+文本）
- 图片预览 | 列表点击即显示高清预览
- 自动 TXT 导出 | 成功处理后立即写出同名 txt
- 逐张顺序调用 | 完全符合一次上传一张、等待返回的业务需求
- 进度/日志 | 实时进度条 + 详细日志输出
- 重试与速率限制 | 指数退避自动重试，避免 429/500 导致中断
- 多语言提示词 | 默认英文，可扩展中文/多语种

## 安装指南

### 环境要求

- **Python 3.8+ (✅ 完全兼容您的Python 3.10)**
- 有效的 MiniMax API Key（需要支持视觉功能的模型）

### 快速安装

```bash
# 克隆项目
git clone <repository-url>
cd MINIMAX反推打标

# 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 依赖安装
```bash
pip install -r requirements.txt  # 包含 PySide6、aiohttp 等依赖
```

## 🚀 图形界面 (GUI) 快速上手
1. **启动 GUI**
   ```bash
   python -m minimax_tagger.gui
   ```
2. **操作流程**
   1. 选择图片文件夹 → `创建Manifest` → 自动扫描生成 `manifest.csv`
   2. 点击图片列表项 → 右侧预览面板显示真实图片 + 生成的提示词
   3. 点击`批量处理图片` → 程序逐张调用 OpenRouter API
   4. 处理完成后，同目录生成 `.txt` 文件，可直接用于训练

> 提示：API Key 会自动从 `~/.minimax_tagger.toml` 或环境变量读取。

## API Key 获取

### 1. 注册 MiniMax 账号
访问 [MiniMax 开放平台](https://api.minimax.chat/) 注册账号

### 2. 获取 API Key
1. 登录后进入控制台
2. 在"应用管理"中创建新应用
3. 复制生成的 API Key

### 3. 配置 API Key

选择以下任一方式配置：

**方法1：环境变量（推荐）**
```bash
export MINIMAX_API_KEY="your_api_key_here"
export MINIMAX_GROUP_ID="your_group_id"  # 企业用户需要
```

**方法2：配置文件**
创建 `~/.minimax_tagger.toml` 文件：
```toml
[minimax]
api_key = "your_api_key_here"
group_id = "your_group_id"  # 可选
model_name = "abab6.5s-chat"
```

## 使用方法

### 验证配置
```bash
python -m minimax_tagger --check-config
```

### 批量处理图片
```bash
# 处理单个目录
python -m minimax_tagger /path/to/images --prompt "Generate detailed English prompts for this image"

# 自定义参数
python -m minimax_tagger /path/to/images \
    --prompt "Create professional photography prompts" \
    --concurrency 2 \
    --retry 5
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `input_path` | 图片文件或目录路径 | 必需 |
| `--prompt` | 主提示词模板 | 默认模板 |
| `--system-prompt` | 系统提示词 | 无 |
| `--concurrency` | 并发数量 | 1 |
| `--retry` | 重试次数 | 3 |
| `--check-config` | 验证配置 | False |

## 输出格式

处理完成后会在输入目录生成 `manifest.csv` 文件：

```csv
filepath,prompt_en,prompt_cn,status,retry_cnt
image1.jpg,"A beautiful sunset...",,"success",0
image2.png,"Modern architecture...",,"success",1
```

## 配置说明

### 支持的图片格式
- JPG/JPEG
- PNG  
- WebP
- BMP
- TIFF

### 性能优化
- **并发控制**：根据 API 限制调整并发数
- **批量大小**：自动根据图片大小分批处理
- **重试机制**：失败自动重试，提高成功率

## 故障排除

### 常见问题

**1. SSL 证书错误**
```bash
# macOS 系统可能遇到证书问题，代码已内置解决方案
```

**2. API 配置错误**
```bash
# 使用配置验证
python -m minimax_tagger --check-config
```

**3. 模型不支持图片**
```
错误：模型回复"无法查看图片"
原因：当前 abab6.5s-chat 模型不支持图片理解
解决：等待 MiniMax 官方支持或使用其他服务
```

### 日志查看
程序运行时会显示详细日志，包括：
- API 调用状态
- 处理进度
- 错误信息

## 项目完成度评估

| 功能模块 | 完成度 | 说明 |
|----------|--------|------|
| OpenRouter 集成 | **100%** | 已默认启用，支持 Vision 模型 |
| GUI & 预览 | **90%** | 预览、进度、状态完善 |
| TXT 自动导出 | **100%** | 同名 txt 即时生成 |
| 批量处理核心 | **95%** | 逐张顺序 + 重试机制 |
| 文档 & 示例 | **80%** | README 已更新，待补充更多示例 |
| **整体完成度** | **≈ 85-90%** | 可稳定使用，尚有边缘功能待实现 |

## 技术特性

- ✅ **异步处理**：使用 asyncio 提高处理效率
- ✅ **SSL 绕过**：解决 macOS 证书问题  
- ✅ **智能分块**：根据文件大小优化批次
- ✅ **配置验证**：完整的配置和连接测试
- ✅ **错误重试**：指数退避重试策略
- ✅ **进度追踪**：实时状态更新

## 开发计划

- [x] OpenRouter Vision 模型接入
- [x] GUI 图片预览
- [x] 自动 TXT 导出
- [ ] 中文提示词自动生成
- [ ] 批量任务取消 / 暂停恢复
- [ ] 多模型切换（Qwen-VL 等）
- [ ] Docker 一键部署脚本

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！ 