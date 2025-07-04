# MiniMax Vision 批量反推提示词工具 — 项目规划书

> 版本：v1.0  日期：2025-07-03

---

## 1. 项目背景
- 现有 Coze 流程无法处理图片，决定切换 **MiniMax vision-02** API。
- 目标：针对 20 – 100 张 LoRA 数据集，自动生成英文反推提示词，支持人工审阅与多次重生。

## 2. 关键需求
| 编号 | 功能 | 说明 |
| --- | --- | --- |
| F1 | 目录扫描 | 递归读取 `*.jpg / *.png / *.webp`；支持 `--skip-exist` |
| F2 | 调用 API | 单次请求 **动态切块**，HTTP Body ≤ 15 MB；文本+图片混合 |
| F3 | 写结果 | 写回 `manifest.csv` 及可选同名 `.txt` |
| F4 | GUI 审阅 | 缩略图+提示词列表；重生 / 手编 / 通过 |
| F5 | 主提示词可编辑 | GUI 左栏实时修改，多项目多配置 |
| F6 | 状态追踪 | `pending / approved / rejected / retry_n` 字段 |
| F7 | 并发&重试 | 多线程调用、指数退避、错误日志 |

## 3. 模块划分
```
minimax_tagger/
├── __main__.py       # CLI 入口
├── config.py         # 读写 config.toml
├── api.py            # MiniMax REST 封装
├── pipeline.py       # 批处理 & 动态切块
├── gui.py            # PySide6 GUI
├── manifest.py       # CSV ↔︎ TXT 转换
└── utils/            # Base64、日志等
```

## 4. API 调用格式
```jsonc
POST https://api.minimax.chat/v1/complete
{
  "model": "vision-02",
  "temperature": 0.2,
  "messages": [
    { "role": "system", "content": [
        {"type": "text", "text": "${SYSTEM_PROMPT}"}
    ]},
    { "role": "user", "content": [
        {"type": "text",  "text": "${USER_PROMPT}"},
        {"type": "image", "image": "data:image/png;base64,${B64}"}
    ]}
  ]
}
```

## 5. Manifest 设计
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| filepath | str | 相对路径 |
| prompt_en | str | 反推英文提示词 |
| prompt_cn | str | (可选) 中文对照 |
| status | enum | pending / approved / rejected |
| retry_cnt | int | 重生次数 |

> 备注：LoRA 训练脚本若需要同名 `.txt`，`manifest.py` 中提供 `to_txt()` 方法批量导出。

## 6. 动态切块算法（简要）
```python
MAX_BYTES = 15 * 1024 * 1024  # 15 MB 安全阈
batch, size_acc = [], 0
for img in images:
    b64 = encode_b64(img)
    if size_acc + len(b64) > MAX_BYTES:
        yield batch
        batch, size_acc = [], 0
    batch.append((img, b64))
    size_acc += len(b64)
if batch:
    yield batch
```

## 7. GUI 线框
```
┌──────────────────────────────────────────┐
│ 文件夹📂  API-Key🔑  Group-ID #️⃣  [保存] │
│──────────────────────────────────────────│
│ 主提示词 (QPlainTextEdit)                │
│                                          │
│ [执行] [暂停] [导出TXT]                  │
├──────────────────────────────────────────┤
│ 缩略列表 (状态/重试) │ 图片预览 │ 提示词 │
│              (双击可编) │         │ [重生]│
│                               │ [通过]   │
└──────────────────────────────────────────┘
```

## 8. requirements.txt（初稿）
```
aiohttp>=3.8
rich
pandas
PySide6
loguru
python-dotenv
```

## 9. 开发里程碑
| 阶段 | 目标 | 预计工时 |
| --- | --- | --- |
| M1 | CLI 扫描+调用API | 1d |
| M2 | Manifest + 重试 | 0.5d |
| M3 | GUI 雏形 (浏览/编辑) | 1.5d |
| M4 | 多线程 + 日志优化 | 0.5d |
| M5 | 完整测试 & 文档 | 1d |

---

## 10. 与 Cursor 的交互提示词（按步骤复制给 AI）
> **说明**：下面每行都是一次单独发送给 Cursor 的指令。

1. `请在新文件夹 minimax_tagger 中初始化 Python 项目并生成上方目录结构。`
2. `在 minimax_tagger/api.py 内实现 MiniMax vision-02 的 async 调用封装，需要支持文本+图片片段。`
3. `在 minimax_tagger/pipeline.py 实现动态切块算法和批量调用逻辑。`
4. `在 manifest.py 编写 CSV ↔︎ txt 导入导出工具函数。`
5. `使用 PySide6 在 gui.py 创建横分栏界面，左侧预设区、右侧审阅区，含重生/通过按钮。`
6. `补充 config.py 支持读取 ~/.minimax_tagger.toml 与 GUI 写回。`
7. `生成 requirements.txt 并在 README 里写安装&使用示例。`
8. `编写 tests 目录，包含 API mock 与 pipeline 单元测试。`

> 若需要迭代，请把"修改点"告诉 Cursor，例如："请给 gui.py 的列表增加状态图标列"。

---

## 11. FAQ & 风险
- **QPS 限制**：MiniMax 免费额度 QPS=1，同步任务太多会排队，可升级套餐。  
- **大图超限**：1024×1024 无损 PNG 可能 3-4 MB，请预先压缩或降低张数阈值。  
- **隐私合规**：需确认图片无涉敏内容，MiniMax 服务端有审计。

---

> 复制本文件到新工程即可作为团队共识文档。祝开发顺利！ 