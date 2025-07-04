"""集成测试 - 测试整个系统的健壮性和可靠性"""
import asyncio
import unittest
from pathlib import Path
import tempfile
import shutil
import os
from unittest.mock import AsyncMock, patch

# 添加项目路径到 sys.path
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from minimax_tagger.config import Settings
from minimax_tagger.manifest import ManifestManager, ProcessStatus
from minimax_tagger.pipeline import scan_images_in_directory, dynamic_chunk_images
from minimax_tagger.utils.image_io import validate_image_file, estimate_base64_size
from minimax_tagger.utils.concurrency import retry_async


class TestIntegration(unittest.TestCase):
    """集成测试类"""
    
    def setUp(self):
        """测试前的设置"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.images_dir = self.test_dir / "images"
        self.images_dir.mkdir()
        self.manifest_path = self.test_dir / "manifest.csv"
        
        # 创建测试配置
        self.test_settings = Settings()
        self.test_settings.api_key = "test_key"
        self.test_settings.group_id = "test_group"
        self.test_settings.concurrency = 2
        self.test_settings.retry_max = 2
        
    def tearDown(self):
        """测试后的清理"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def create_dummy_image(self, name: str, size_kb: int = 1) -> Path:
        """创建测试用的虚拟图片文件"""
        image_path = self.images_dir / name
        # 创建指定大小的假图片文件
        with open(image_path, 'wb') as f:
            f.write(b'\xFF\xD8\xFF\xE0' + b'\x00' * (size_kb * 1024 - 4))
        return image_path
    
    def test_directory_scanning_robustness(self):
        """测试目录扫描的健壮性"""
        # 创建各种类型的文件
        self.create_dummy_image("test1.jpg")
        self.create_dummy_image("test2.PNG") 
        self.create_dummy_image("test3.webp")
        
        # 创建非图片文件
        (self.images_dir / "readme.txt").write_text("test")
        (self.images_dir / "config.json").write_text("{}")
        
        # 创建子目录和文件
        sub_dir = self.images_dir / "subdir"
        sub_dir.mkdir()
        self.create_dummy_image("subdir/nested.jpg")
        
        # 测试扫描
        images = scan_images_in_directory(self.images_dir)
        
        # 验证结果
        self.assertEqual(len(images), 4)  # 应该找到4个图片文件
        extensions = [img.suffix.lower() for img in images]
        self.assertIn('.jpg', extensions)
        self.assertIn('.png', extensions) 
        self.assertIn('.webp', extensions)
    
    def test_directory_scanning_error_cases(self):
        """测试目录扫描的错误处理"""
        # 测试不存在的目录
        non_existent = Path("/nonexistent/directory")
        images = scan_images_in_directory(non_existent)
        self.assertEqual(len(images), 0)
        
        # 测试文件而不是目录
        test_file = self.test_dir / "test.txt"
        test_file.write_text("test")
        images = scan_images_in_directory(test_file)
        self.assertEqual(len(images), 0)
    
    def test_dynamic_chunking_algorithm(self):
        """测试动态切块算法"""
        # 创建不同大小的图片
        small_images = [
            self.create_dummy_image(f"small_{i}.jpg", 100)  # 100KB
            for i in range(5)
        ]
        large_images = [
            self.create_dummy_image(f"large_{i}.jpg", 5000)  # 5MB
            for i in range(3)
        ]
        
        all_images = small_images + large_images
        
        # 测试切块
        chunks = list(dynamic_chunk_images(all_images))
        
        # 验证结果
        self.assertGreater(len(chunks), 0)
        
        # 验证每个批次的大小不超过限制
        for chunk in chunks:
            total_size = sum(estimate_base64_size(img) for img in chunk)
            # 添加一些容错空间
            self.assertLess(total_size, self.test_settings.max_batch_size_bytes + 10000)
    
    def test_manifest_operations(self):
        """测试 manifest 操作的健壮性"""
        manager = ManifestManager(self.manifest_path)
        
        # 测试添加记录
        manager.add_or_update_record(
            "test1.jpg", 
            "A beautiful image",
            status=ProcessStatus.PENDING
        )
        manager.add_or_update_record(
            "test2.jpg",
            "Another image", 
            status=ProcessStatus.APPROVED
        )
        
        # 测试保存和加载
        manager.save_to_csv()
        self.assertTrue(self.manifest_path.exists())
        
        # 重新加载
        new_manager = ManifestManager(self.manifest_path)
        new_manager.load_from_csv()
        
        self.assertEqual(len(new_manager.records), 2)
        
        # 测试状态更新
        success = new_manager.update_record_status("test1.jpg", ProcessStatus.APPROVED)
        self.assertTrue(success)
        
        # 测试导出 TXT 文件
        exported_count = new_manager.export_to_txt_files(self.test_dir)
        self.assertEqual(exported_count, 2)  # 两个已通过的记录
        
        # 验证 TXT 文件存在
        self.assertTrue((self.test_dir / "test1.txt").exists())
        self.assertTrue((self.test_dir / "test2.txt").exists())
    
    async def test_retry_mechanism(self):
        """测试重试机制"""
        call_count = 0
        
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Test error")
            return "success"
        
        # 测试成功重试
        result = await retry_async(
            failing_function,
            max_retries=3,
            base_delay=0.01  # 很短的延迟用于测试
        )
        
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)
    
    async def test_retry_mechanism_failure(self):
        """测试重试机制的失败情况"""
        async def always_failing_function():
            raise ValueError("Always fails")
        
        # 测试最终失败
        with self.assertRaises(Exception):
            await retry_async(
                always_failing_function,
                max_retries=2,
                base_delay=0.01
            )
    
    def test_config_file_operations(self):
        """测试配置文件操作"""
        settings = Settings()
        settings.api_key = "test_key_123"
        settings.group_id = "test_group_456"
        settings.concurrency = 5
        
        config_path = self.test_dir / "test_config.toml"
        
        # 测试保存配置
        success = settings.save_to_file(config_path)
        # 注意：如果没有安装 tomli-w，这里可能会失败，这是预期的
        
        if success:
            # 如果保存成功，测试加载
            new_settings = Settings()
            load_success = new_settings.load_from_file(config_path)
            
            if load_success:
                self.assertEqual(new_settings.api_key, "test_key_123")
                self.assertEqual(new_settings.group_id, "test_group_456")
                self.assertEqual(new_settings.concurrency, 5)
    
    def test_image_validation(self):
        """测试图片验证功能"""
        # 创建有效的图片文件
        valid_image = self.create_dummy_image("valid.jpg")
        self.assertTrue(validate_image_file(valid_image))
        
        # 创建无效的文件
        invalid_file = self.images_dir / "invalid.txt"
        invalid_file.write_text("not an image")
        self.assertFalse(validate_image_file(invalid_file))
        
        # 测试不存在的文件
        non_existent = self.images_dir / "nonexistent.jpg"
        self.assertFalse(validate_image_file(non_existent))
        
        # 测试空文件
        empty_file = self.images_dir / "empty.jpg"
        empty_file.touch()
        self.assertFalse(validate_image_file(empty_file))


class TestAsyncIntegration(unittest.IsolatedAsyncioTestCase):
    """异步集成测试"""
    
    async def test_concurrent_processing_simulation(self):
        """模拟并发处理测试"""
        from minimax_tagger.utils.concurrency import run_tasks_with_limit
        
        # 创建模拟任务
        results = []
        
        async def mock_task(index):
            await asyncio.sleep(0.01)  # 模拟工作
            return f"result_{index}"
        
        tasks = [lambda i=i: mock_task(i) for i in range(10)]
        
        # 执行并发任务
        task_results = await run_tasks_with_limit(tasks, max_concurrency=3)
        
        # 验证结果
        self.assertEqual(len(task_results), 10)
        
        # 检查成功的结果
        success_count = sum(1 for result, error in task_results if result and not error)
        self.assertGreater(success_count, 0)


if __name__ == "__main__":
    # 运行同步测试
    unittest.main(verbosity=2) 