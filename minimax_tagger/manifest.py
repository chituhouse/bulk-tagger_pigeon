"""Manifest CSV ↔︎ TXT 文件导入导出工具。"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class ProcessStatus(Enum):
    """处理状态枚举"""
    PENDING = "pending"
    APPROVED = "approved" 
    REJECTED = "rejected"


@dataclass
class ImageRecord:
    """图片记录数据类"""
    filepath: str
    prompt_en: str = ""
    prompt_cn: str = ""
    status: ProcessStatus = ProcessStatus.PENDING
    retry_cnt: int = 0
    
    def to_dict(self) -> Dict[str, str]:
        """转换为字典格式"""
        return {
            "filepath": self.filepath,
            "prompt_en": self.prompt_en,
            "prompt_cn": self.prompt_cn,
            "status": self.status.value,
            "retry_cnt": str(self.retry_cnt)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "ImageRecord":
        """从字典创建记录"""
        return cls(
            filepath=data.get("filepath", ""),
            prompt_en=data.get("prompt_en", ""),
            prompt_cn=data.get("prompt_cn", ""),
            status=ProcessStatus(data.get("status", "pending")),
            retry_cnt=int(data.get("retry_cnt", "0"))
        )


class ManifestManager:
    """Manifest 文件管理器"""
    
    def __init__(self, manifest_path: Path):
        self.manifest_path = manifest_path
        self.records: List[ImageRecord] = []
    
    def load_from_csv(self) -> None:
        """从 CSV 文件加载记录"""
        if not self.manifest_path.exists():
            print(f"Manifest 文件不存在: {self.manifest_path}")
            return
        
        self.records = []
        with open(self.manifest_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    record = ImageRecord.from_dict(row)
                    self.records.append(record)
                except Exception as e:
                    print(f"解析 CSV 行时出错: {row}, 错误: {e}")
    
    def save_to_csv(self) -> None:
        """保存记录到 CSV 文件"""
        # 确保目录存在
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        
        fieldnames = ["filepath", "prompt_en", "prompt_cn", "status", "retry_cnt"]
        
        with open(self.manifest_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in self.records:
                writer.writerow(record.to_dict())
    
    def add_or_update_record(
        self, 
        filepath: str, 
        prompt_en: str = "",
        prompt_cn: str = "",
        status: ProcessStatus = ProcessStatus.PENDING
    ) -> None:
        """添加或更新记录"""
        # 查找是否已存在该文件的记录
        for record in self.records:
            if record.filepath == filepath:
                # 更新现有记录
                if prompt_en:
                    record.prompt_en = prompt_en
                if prompt_cn:
                    record.prompt_cn = prompt_cn
                record.status = status
                return
        
        # 添加新记录
        new_record = ImageRecord(
            filepath=filepath,
            prompt_en=prompt_en,
            prompt_cn=prompt_cn,
            status=status
        )
        self.records.append(new_record)
    
    def get_pending_records(self) -> List[ImageRecord]:
        """获取所有待处理的记录"""
        return [r for r in self.records if r.status == ProcessStatus.PENDING]
    
    def get_approved_records(self) -> List[ImageRecord]:
        """获取所有已通过的记录"""
        return [r for r in self.records if r.status == ProcessStatus.APPROVED]
    
    def update_record_status(self, filepath: str, status: ProcessStatus) -> bool:
        """更新记录状态"""
        for record in self.records:
            if record.filepath == filepath:
                record.status = status
                return True
        return False
    
    def increment_retry_count(self, filepath: str) -> bool:
        """增加重试计数"""
        for record in self.records:
            if record.filepath == filepath:
                record.retry_cnt += 1
                return True
        return False
    
    def export_to_txt_files(self, output_dir: Optional[Path] = None) -> int:
        """
        导出已通过的记录为同名 .txt 文件（供 LoRA 训练使用）
        
        Args:
            output_dir: 输出目录，如果为 None 则在图片文件同级目录
        
        Returns:
            导出的文件数量
        """
        approved_records = self.get_approved_records()
        exported_count = 0
        
        for record in approved_records:
            if not record.prompt_en:
                continue
                
            # 确定 txt 文件路径
            image_path = Path(record.filepath)
            if output_dir:
                txt_path = output_dir / (image_path.stem + ".txt")
                txt_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                txt_path = image_path.with_suffix(".txt")
            
            # 写入提示词
            try:
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(record.prompt_en)
                exported_count += 1
                print(f"导出: {txt_path}")
            except Exception as e:
                print(f"导出失败 {txt_path}: {e}")
        
        return exported_count
    
    def import_from_directory(self, directory: Path, extensions: tuple[str, ...] = (".jpg", ".png", ".webp")) -> int:
        """
        从目录导入图片文件，创建初始记录
        
        Args:
            directory: 图片目录
            extensions: 支持的图片扩展名
        
        Returns:
            导入的文件数量
        """
        imported_count = 0
        
        for ext in extensions:
            pattern = f"**/*{ext}"
            for image_path in directory.glob(pattern):
                # 使用相对路径
                relative_path = str(image_path.relative_to(directory))
                
                # 检查是否已存在
                exists = any(r.filepath == relative_path for r in self.records)
                if not exists:
                    self.add_or_update_record(relative_path)
                    imported_count += 1
        
        return imported_count


def create_manifest_from_directory(directory: Path, manifest_path: Path) -> ManifestManager:
    """从目录创建新的 manifest 文件"""
    manager = ManifestManager(manifest_path)
    imported_count = manager.import_from_directory(directory)
    manager.save_to_csv()
    print(f"从 {directory} 导入了 {imported_count} 个图片文件")
    return manager 