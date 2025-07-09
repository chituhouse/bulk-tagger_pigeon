# MiniMax Tagger Windows 使用指南

## 0.1.1 更新

- 安装脚本将自动在桌面创建 `MiniMax Tagger` 图标，双击即可启动 GUI。

---

## 1. 环境准备

1. 安装 **Python 3.10+**（建议 3.10/3.11）：
   - 访问 https://www.python.org/downloads/windows/ ，下载并运行安装包。
   - 勾选 *Add python.exe to PATH* 后再点击 *Install Now*。
   - 安装完成后，打开 *命令提示符* (Win+R → `cmd`)，输入 `python --version`，确认版本号。

2. 安装 **Git**（可选，用于克隆仓库）：
   - 访问 https://git-scm.com/download/win ，完成安装。

## 2. 获取项目文件

方式 A – 直接解压：
1. 将同事发送的 `MiniMax_Tagger_Win.zip` 拷贝到任意目录。
2. 右键 → *全部解压* 或使用 7-Zip 解压。

方式 B – Git 克隆（需要 Git）：
```bash
git clone https://github.com/your-org/minimax_tagger.git
```

> 本指南以下假设你已位于项目根目录：
> ```bash
> cd MiniMax_Tagger
> ```

## 3. 创建虚拟环境（推荐）
```bash
python -m venv .venv
".venv\Scripts\activate"   # PowerShell 下改为 .venv\Scripts\Activate.ps1
```

## 4. 安装依赖
```bash
pip install -r requirements.txt
```

若需要 GUI，请确保 **PySide6** 安装成功；若下载速度慢，可指定清华镜像：
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 5. 配置 API 密钥

MiniMax Tagger 需要访问 **MiniMax 视觉大模型** 或 **OpenRouter**。
请向管理员申请以下信息并写入 *环境变量*：

```powershell
# MiniMax 直接调用示例
setx MINIMAX_API_KEY "你的_API_Key"
setx MINIMAX_GROUP_ID "你的_Group_ID"   # 企业账号可选

# 如果使用 OpenRouter
setx OPENROUTER_API_KEY "你的_OpenRouter_Key"
```

注销/重开终端后生效。也可以在 PowerShell 中临时设置：
```powershell
$env:MINIMAX_API_KEY = "你的_API_Key"
```

> 可选：将其它高级设置写入 `%USERPROFILE%\.minimax_tagger.toml`，示例见仓库根目录 `README.md`。

## 6. 运行图形界面 (GUI)
```bash
python -m minimax_tagger.gui
```
出现窗口后：
1. 选择包含图片的文件夹 → *生成 manifest*。
2. 填写用户提示词模板（英文），点击 *开始批量处理*。
3. 审核生成的提示词，导出 TXT 文件。

## 7. 命令行批量处理 (CLI)
```bash
python -m minimax_tagger 你的目录 --prompt "英文提示词模板"
```
可用参数:
```
--concurrency   并发协程数 (默认1)
--retry         重试次数 (默认3)
--check-config  测试 API 连接
```

## 8. 常见问题
| 现象 | 解决方案 |
| ---- | -------- |
| GUI 启动后空白/闪退 | 检查是否安装了 GPU 驱动；尝试 `python -m pip install PySide6-Addons` |
| `SSL: CERTIFICATE_VERIFY_FAILED` | 在 PowerShell 中执行 `[Net.ServicePointManager]::SecurityProtocol = 3072` 或使用 `pip install certifi` 更新证书 |
| 请求 429 速率限制 | 减小 `--concurrency` 或等待额度恢复 |

## 9. 升级
```bash
pip install --upgrade minimax-tagger
```

## 10. 卸载
```bash
pip uninstall minimax-tagger
```

---
版权所有 © 2025 MiniMax Tagger 团队 