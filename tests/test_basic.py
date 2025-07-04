"""基础功能测试"""
import unittest
from pathlib import Path
import sys
import os

# 添加项目路径到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from minimax_tagger.config import settings
from minimax_tagger.manifest import ManifestManager, ProcessStatus, ImageRecord


class TestBasicFunctionality(unittest.TestCase):
    """测试基础功能"""
    
    def setUp(self):
        """测试前的设置"""
        self.test_dir = Path(__file__).parent / "test_data"
        self.test_dir.mkdir(exist_ok=True)
        
        self.manifest_path = self.test_dir / "test_manifest.csv"
    
    def tearDown(self):
        """测试后的清理"""
        if self.manifest_path.exists():
            self.manifest_path.unlink()
    
    def test_config_loading(self):
        """测试配置加载"""
        self.assertIsNotNone(settings)
        self.assertEqual(settings.concurrency, 1)
        self.assertGreater(settings.max_batch_size_bytes, 0)
    
    def test_manifest_manager_creation(self):
        """测试 ManifestManager 创建"""
        manager = ManifestManager(self.manifest_path)
        self.assertEqual(manager.manifest_path, self.manifest_path)
        self.assertEqual(len(manager.records), 0)
    
    def test_image_record_creation(self):
        """测试 ImageRecord 创建"""
        record = ImageRecord(
            filepath="test.jpg",
            prompt_en="A test image",
            status=ProcessStatus.PENDING
        )
        
        self.assertEqual(record.filepath, "test.jpg")
        self.assertEqual(record.prompt_en, "A test image")
        self.assertEqual(record.status, ProcessStatus.PENDING)
        self.assertEqual(record.retry_cnt, 0)
    
    def test_manifest_save_load(self):
        """测试 manifest 保存和加载"""
        manager = ManifestManager(self.manifest_path)
        
        # 添加测试记录
        manager.add_or_update_record(
            filepath="test1.jpg",
            prompt_en="Test prompt 1",
            status=ProcessStatus.PENDING
        )
        manager.add_or_update_record(
            filepath="test2.png",
            prompt_en="Test prompt 2", 
            status=ProcessStatus.APPROVED
        )
        
        # 保存
        manager.save_to_csv()
        self.assertTrue(self.manifest_path.exists())
        
        # 重新加载
        new_manager = ManifestManager(self.manifest_path)
        new_manager.load_from_csv()
        
        self.assertEqual(len(new_manager.records), 2)
        
        # 验证数据
        record1 = new_manager.records[0]
        self.assertEqual(record1.filepath, "test1.jpg")
        self.assertEqual(record1.prompt_en, "Test prompt 1")
        self.assertEqual(record1.status, ProcessStatus.PENDING)


if __name__ == "__main__":
    unittest.main() 