"""配置管理模块 - 读写 config.toml 和环境变量。"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# TOML 支持
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

try:
    import tomli_w
except ImportError:
    tomli_w = None

class Settings:
    """应用设置类，支持从环境变量和配置文件读取。"""
    
    def __init__(self):
        # MiniMax API 配置
        self.api_key: Optional[str] = os.getenv("MINIMAX_API_KEY")
        self.group_id: Optional[str] = os.getenv("MINIMAX_GROUP_ID") 
        self.api_base_url: str = os.getenv(
            "MINIMAX_API_BASE_URL", 
            "https://api.minimax.chat/v1/chat/completions"  # 标准的聊天完成端点
        )
        # 优先检查OpenRouter配置
        self.use_openrouter: bool = bool(os.getenv("OPENROUTER_API_KEY"))
        self.openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
        
        if self.use_openrouter:
            # 使用OpenRouter配置
            self.api_base_url = "https://openrouter.ai/api/v1/chat/completions"
            self.model_name = os.getenv("OPENROUTER_MODEL_NAME", "minimax/minimax-01")
            self.api_key = self.openrouter_api_key
        else:
            # 使用MiniMax直接API配置
            self.model_name: str = os.getenv("MINIMAX_MODEL_NAME", "MiniMax-VL-01")
            self.api_key = os.getenv("MINIMAX_API_KEY")
        
        # 处理配置
        self.concurrency: int = int(os.getenv("CONCURRENCY", "1"))
        self.retry_max: int = int(os.getenv("RETRY_MAX", "3"))
        self.retry_delay: float = float(os.getenv("RETRY_DELAY", "1.0"))
        
        # 切块配置
        self.max_batch_size_bytes: int = int(os.getenv("MAX_BATCH_SIZE_BYTES", str(15 * 1024 * 1024)))  # 15MB
        
        # 文件配置
        self.supported_extensions: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".webp")
        
        # 默认提示词
        self.system_prompt: str = os.getenv(
            "SYSTEM_PROMPT",
            "你是一个专业的图像分析师，请仔细观察图像并生成准确的英文描述。"
        )
    
    def validate(self) -> bool:
        """验证必需的配置项是否完整。"""
        if not self.api_key:
            if self.use_openrouter:
                print("错误：未设置 OPENROUTER_API_KEY 环境变量")
            else:
                print("错误：未设置 MINIMAX_API_KEY 环境变量")
            return False
        
        # 显示当前使用的服务
        if self.use_openrouter:
            print(f"✅ 使用 OpenRouter API，模型: {self.model_name}")
        else:
            print(f"✅ 使用 MiniMax 直接API，模型: {self.model_name}")
            # group_id 改为可选，只警告不阻止运行
            if not self.group_id:
                print("警告：未设置 MINIMAX_GROUP_ID，部分功能可能受限")
        return True
    
    def load_from_file(self, config_path: Optional[Path] = None) -> bool:
        """从配置文件加载设置。
        
        Args:
            config_path: 配置文件路径，默认为 ~/.minimax_tagger.toml
            
        Returns:
            是否成功加载配置
        """
        if config_path is None:
            config_path = Path.home() / ".minimax_tagger.toml"
        
        if not config_path.exists():
            print(f"配置文件不存在: {config_path}")
            return False
        
        if tomllib is None:
            print("错误：未安装 TOML 解析库，请运行: pip install tomli")
            return False
        
        try:
            with open(config_path, "rb") as f:
                config_data = tomllib.load(f)
            
            # 加载 API 配置
            if "api" in config_data:
                api_config = config_data["api"]
                self.api_key = api_config.get("key", self.api_key)
                self.group_id = api_config.get("group_id", self.group_id)
                self.api_base_url = api_config.get("base_url", self.api_base_url)
                self.model_name = api_config.get("model_name", self.model_name)  # 加载模型名称
                
                # 检查配置文件中的API Key是否来自OpenRouter
                if self.api_key and "openrouter" in self.api_base_url.lower():
                    self.use_openrouter = True
                    self.openrouter_api_key = self.api_key
                    print("🔧 检测到OpenRouter配置")
                elif self.api_key and not self.use_openrouter:
                    print("🔧 检测到MiniMax直接API配置")
            
            # 加载处理配置
            if "processing" in config_data:
                proc_config = config_data["processing"]
                self.concurrency = proc_config.get("concurrency", self.concurrency)
                self.retry_max = proc_config.get("retry_max", self.retry_max)
                self.retry_delay = proc_config.get("retry_delay", self.retry_delay)
                self.max_batch_size_bytes = proc_config.get("max_batch_size_bytes", self.max_batch_size_bytes)
            
            # 加载提示词配置
            if "prompts" in config_data:
                prompt_config = config_data["prompts"]
                self.system_prompt = prompt_config.get("system", self.system_prompt)
            
            print(f"成功加载配置文件: {config_path}")
            return True
            
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return False
    
    def save_to_file(self, config_path: Optional[Path] = None) -> bool:
        """保存设置到配置文件。
        
        Args:
            config_path: 配置文件路径，默认为 ~/.minimax_tagger.toml
            
        Returns:
            是否成功保存配置
        """
        if config_path is None:
            config_path = Path.home() / ".minimax_tagger.toml"
        
        if tomli_w is None:
            print("错误：未安装 TOML 写入库，请运行: pip install tomli-w")
            return False
        
        # 构建配置数据
        config_data = {
            "api": {
                "key": self.api_key or "",
                "group_id": self.group_id or "",
                "base_url": self.api_base_url,
                "model_name": self.model_name  # 保存模型名称
            },
            "processing": {
                "concurrency": self.concurrency,
                "retry_max": self.retry_max,
                "retry_delay": self.retry_delay,
                "max_batch_size_bytes": self.max_batch_size_bytes
            },
            "prompts": {
                "system": self.system_prompt
            }
        }
        
        try:
            # 确保目录存在
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, "wb") as f:
                tomli_w.dump(config_data, f)
            
            print(f"成功保存配置文件: {config_path}")
            return True
            
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典格式"""
        return {
            "api_key": self.api_key,
            "group_id": self.group_id,
            "api_base_url": self.api_base_url,
            "model_name": self.model_name,  # 添加模型名称
            "concurrency": self.concurrency,
            "retry_max": self.retry_max,
            "retry_delay": self.retry_delay,
            "max_batch_size_bytes": self.max_batch_size_bytes,
            "system_prompt": self.system_prompt
        }
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """从字典更新配置"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)


# 全局设置实例
settings = Settings() 