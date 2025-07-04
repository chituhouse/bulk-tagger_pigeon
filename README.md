# MiniMax Tagger GUI 0.8.9

> 一个专注 **LoRA / Stable-Diffusion** 训练数据集制作的开源图形界面工具。支持批量上传图片到 MiniMax 视觉大模型，自动生成高质量英文 Prompt，并在审阅后一键导出 TXT。

## 🚀 关键亮点

| 功能 | 说明 |
|------|------|
| **批量处理** | 严格一次上传一张，等待返回后处理下一张，安全无 429 |
| **Prompt 审阅** | 支持逐张/批量重新生成、编辑、通过/拒绝 |
| **Manifest 工作流** | 全流程都写入 `manifest.csv`，导出阶段再统一生成 TXT |
| **智能复选框** | 全选 / 半选 三态逻辑，批量操作心里有数 |
| **文件名高亮** | 预览区顶部实时显示当前图片文件名 |
| **OpenRouter 支持** | 默认调用 `minimax/minimax-01` 视觉模型，无需等待官方 |

---

## 📦 安装

```bash
# 克隆仓库
$ git clone https://github.com/yourname/minimax-tagger.git
$ cd minimax-tagger

# 创建虚拟环境（可选）
$ python -m venv .venv && source .venv/bin/activate

# 安装依赖
$ pip install -r requirements.txt
```

---

## 🖥️ 图形界面快速上手

```bash
$ python -m minimax_tagger.gui
```

1. 选择图片文件夹 → `创建Manifest`
2. 点击 `批量处理图片`
3. 审阅 / 重新生成 → `导出 TXT`

> API Key 优先读取 `~/.minimax_tagger.toml`，亦可通过环境变量 `OPENROUTER_API_KEY` 设置。

---

## 🛠️ 命令行用法（可选）

```bash
$ python -m minimax_tagger /path/to/images \
      --prompt "Generate detailed English prompts" \
      --concurrency 1
```

更多参数请参见 `--help`。

---

## 🤝 贡献指南

欢迎提交 PR / Issue，一起把 MiniMax Tagger 打磨得更好！

---

## 📜 许可证

MIT License © 2025 MiniMax Tagger Team 