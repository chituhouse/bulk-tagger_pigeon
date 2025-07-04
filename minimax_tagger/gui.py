"""PySide6 GUI 界面模块。"""
from __future__ import annotations

import sys
import asyncio
from pathlib import Path
from typing import Optional

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QSplitter, QTextEdit, QPlainTextEdit, QPushButton, QLabel,
        QListWidget, QListWidgetItem, QFrame, QGroupBox, QLineEdit,
        QProgressBar, QMessageBox, QFileDialog, QCheckBox
    )
    from PySide6.QtCore import Qt, QThread, QTimer, Signal
    from PySide6.QtGui import QPixmap, QFont
except ImportError:
    print("错误：未安装 PySide6，请运行: pip install PySide6")
    sys.exit(1)

from .manifest import ManifestManager, ProcessStatus, ImageRecord
from .config import settings


class BatchProcessingThread(QThread):
    """批量处理工作线程"""
    
    # 信号定义
    progress_updated = Signal(int, int, str)  # 当前进度, 总数, 当前图片名
    image_processed = Signal(str, str, bool)  # 图片路径, 生成的提示词, 是否成功
    processing_finished = Signal(int, int)    # 成功数量, 总数量
    error_occurred = Signal(str)              # 错误信息
    
    def __init__(self, manifest_manager, image_folder, prompt_template, system_prompt=None):
        super().__init__()
        self.manifest_manager = manifest_manager
        self.image_folder = Path(image_folder)
        self.prompt_template = prompt_template
        self.system_prompt = system_prompt
        self.should_stop = False
        
    def stop_processing(self):
        """停止处理"""
        self.should_stop = True
        
    def run(self):
        """主处理逻辑"""
        try:
            # 获取待处理的图片
            pending_records = [
                record for record in self.manifest_manager.records
                if record.status == ProcessStatus.PENDING
            ]
            
            if not pending_records:
                self.processing_finished.emit(0, 0)
                return
            
            total_count = len(pending_records)
            success_count = 0
            
            # 逐张处理图片
            for i, record in enumerate(pending_records):
                if self.should_stop:
                    break
                    
                # 更新进度
                self.progress_updated.emit(i + 1, total_count, record.filepath)
                
                try:
                    # 构建图片完整路径
                    image_path = self.image_folder / record.filepath
                    
                    if not image_path.exists():
                        error_msg = f"图片文件不存在: {image_path}"
                        self.image_processed.emit(record.filepath, error_msg, False)
                        continue
                    
                    # 调用异步API处理单张图片
                    result = self._process_single_image(image_path)
                    
                    if result:
                        generated_prompt, success = result
                        if success:
                            # 更新记录
                            record.prompt_en = generated_prompt
                            record.status = ProcessStatus.APPROVED  # 自动通过，立即创建TXT文件
                            success_count += 1
                            
                            # 立即创建TXT文件
                            self._create_txt_file(image_path, generated_prompt)
                        
                        self.image_processed.emit(record.filepath, generated_prompt, success)
                    else:
                        self.image_processed.emit(record.filepath, "处理失败", False)
                        
                except Exception as e:
                    error_msg = f"处理图片时出错: {str(e)}"
                    self.image_processed.emit(record.filepath, error_msg, False)
                    
            # 保存更新后的manifest
            try:
                self.manifest_manager.save_to_csv()
            except Exception as e:
                self.error_occurred.emit(f"保存manifest失败: {str(e)}")
                
            # 处理完成
            self.processing_finished.emit(success_count, total_count)
            
        except Exception as e:
            self.error_occurred.emit(f"批量处理过程中发生错误: {str(e)}")
    
    def _process_single_image(self, image_path: Path):
        """处理单张图片 - 在新的事件循环中运行异步代码"""
        try:
            # 创建新的事件循环（因为在线程中）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 运行异步处理
                result = loop.run_until_complete(self._async_process_image(image_path))
                return result
            finally:
                loop.close()
                
        except Exception as e:
            return f"异步处理失败: {str(e)}", False
    
    async def _async_process_image(self, image_path: Path):
        """异步处理单张图片"""
        try:
            from .pipeline import process_image_batch
            
            # 调用API处理单张图片
            results = await process_image_batch(
                image_paths=[image_path],
                prompt_template=self.prompt_template,
                system_prompt=self.system_prompt
            )
            
            if results and len(results) > 0:
                _, generated_prompt, success = results[0]
                return generated_prompt, success
            else:
                return "API返回空结果", False
                
        except Exception as e:
            return f"API调用失败: {str(e)}", False
    
    def _create_txt_file(self, image_path: Path, prompt: str):
        """为图片创建对应的TXT文件"""
        try:
            txt_path = image_path.with_suffix(".txt")
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(prompt)
            print(f"✅ 创建TXT文件: {txt_path}")
        except Exception as e:
            print(f"❌ 创建TXT文件失败 {image_path}: {e}")


############################################
# 1. 新增 —— 单张图片处理后台线程
############################################
class SingleImageProcessingThread(QThread):
    finished = Signal(str, str, bool)   # img_path, prompt, success
    error   = Signal(str)
    progress = Signal(str)              # 进度信息

    def __init__(self, image_path: Path, prompt_template: str, system_prompt: str | None):
        super().__init__()
        self.image_path       = image_path
        self.prompt_template  = prompt_template
        self.system_prompt    = system_prompt
        self._should_stop     = False

    def stop_processing(self):
        """停止处理"""
        self._should_stop = True

    def run(self):
        try:
            if self._should_stop:
                return
                
            self.progress.emit("正在初始化...")
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            if self._should_stop:
                return
                
            self.progress.emit("正在调用API...")
            
            from .pipeline import process_image_batch
            results = loop.run_until_complete(
                process_image_batch(
                    image_paths     = [self.image_path],
                    prompt_template = self.prompt_template,
                    system_prompt   = self.system_prompt
                )
            )
            
            if self._should_stop:
                return
                
            if results:
                _, prompt, success = results[0]
                self.finished.emit(str(self.image_path), prompt, success)
            else:
                self.finished.emit(str(self.image_path), "API 返回空结果", False)

        except Exception as e:
            if not self._should_stop:
                self.error.emit(f"单张处理失败: {e}")
        finally:
            try: 
                loop.close()
            except Exception: 
                pass

############################################
# 2. 新增 —— 批量重新生成线程
############################################
class BatchRegenerateThread(QThread):
    """批量重新生成线程"""
    
    progress_updated = Signal(int, int, str)  # 当前进度, 总数, 当前图片名
    image_regenerated = Signal(str, str, bool)  # 图片路径, 生成的提示词, 是否成功
    batch_finished = Signal(int, int)  # 成功数量, 总数量
    error_occurred = Signal(str)  # 错误信息
    
    def __init__(self, image_paths: list, prompt_template: str, system_prompt: str | None = None):
        super().__init__()
        self.image_paths = image_paths
        self.prompt_template = prompt_template
        self.system_prompt = system_prompt
        self._should_stop = False
        
    def stop_processing(self):
        """停止处理"""
        self._should_stop = True
        
    def run(self):
        """批量重新生成主逻辑"""
        try:
            total_count = len(self.image_paths)
            success_count = 0
            
            for i, image_path in enumerate(self.image_paths):
                if self._should_stop:
                    break
                    
                # 更新进度
                self.progress_updated.emit(i + 1, total_count, image_path.name)
                
                try:
                    # 处理单张图片
                    result = self._process_single_image(image_path)
                    
                    if result:
                        generated_prompt, success = result
                        if success:
                            success_count += 1
                        self.image_regenerated.emit(str(image_path), generated_prompt, success)
                    else:
                        self.image_regenerated.emit(str(image_path), "处理失败", False)
                        
                except Exception as e:
                    error_msg = f"处理图片时出错: {str(e)}"
                    self.image_regenerated.emit(str(image_path), error_msg, False)
                    
            # 批量处理完成
            self.batch_finished.emit(success_count, total_count)
            
        except Exception as e:
            self.error_occurred.emit(f"批量重新生成过程中发生错误: {str(e)}")
    
    def _process_single_image(self, image_path: Path):
        """处理单张图片"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 运行异步处理
                result = loop.run_until_complete(self._async_process_image(image_path))
                return result
            finally:
                loop.close()
                
        except Exception as e:
            return f"异步处理失败: {str(e)}", False
    
    async def _async_process_image(self, image_path: Path):
        """异步处理单张图片"""
        try:
            from .pipeline import process_image_batch
            
            # 调用API处理单张图片
            results = await process_image_batch(
                image_paths=[image_path],
                prompt_template=self.prompt_template,
                system_prompt=self.system_prompt
            )
            
            if results and len(results) > 0:
                _, generated_prompt, success = results[0]
                return generated_prompt, success
            else:
                return "API返回空结果", False
                
        except Exception as e:
            return f"API调用失败: {str(e)}", False


class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.manifest_manager: Optional[ManifestManager] = None
        self.current_manifest_path: Optional[Path] = None
        self.processing_thread: Optional[BatchProcessingThread] = None
        self.regen_thread: SingleImageProcessingThread | None = None   # 单张重新生成线程
        self.batch_regen_thread: BatchRegenerateThread | None = None   # 批量重新生成线程
        
        # 尝试加载配置文件
        settings.load_from_file()
        
        self.init_ui()
        self.setup_connections()
        self.load_config_to_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("MiniMax Tagger v1.0.0 - 批量反推提示词工具")
        self.setMinimumSize(1200, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 顶部控制区
        control_frame = self.create_control_panel()
        main_layout.addWidget(control_frame)
        
        # 主要工作区
        work_splitter = self.create_work_area()
        main_layout.addWidget(work_splitter)
        
        # 底部状态栏
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("就绪")
    
    def create_control_panel(self) -> QFrame:
        """创建顶部控制面板"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        frame.setMaximumHeight(160)  # 增加高度以容纳新功能
        
        layout = QVBoxLayout(frame)
        
        # 第一行：文件夹选择
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("图片文件夹:"))
        
        self.folder_path_edit = QLineEdit()
        self.folder_path_edit.setPlaceholderText("选择包含图片的文件夹...")
        folder_layout.addWidget(self.folder_path_edit)
        
        self.browse_folder_btn = QPushButton("浏览文件夹")
        self.browse_folder_btn.setMaximumWidth(100)
        folder_layout.addWidget(self.browse_folder_btn)
        
        self.create_manifest_btn = QPushButton("创建Manifest")
        self.create_manifest_btn.setMaximumWidth(100)
        folder_layout.addWidget(self.create_manifest_btn)
        
        layout.addLayout(folder_layout)
        
        # 第二行：Manifest文件选择
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("Manifest 文件:"))
        
        self.manifest_path_edit = QLineEdit()
        self.manifest_path_edit.setPlaceholderText("选择现有的 manifest.csv 文件...")
        file_layout.addWidget(self.manifest_path_edit)
        
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setMaximumWidth(80)
        file_layout.addWidget(self.browse_btn)
        
        self.load_btn = QPushButton("加载")
        self.load_btn.setMaximumWidth(60)
        file_layout.addWidget(self.load_btn)
        
        layout.addLayout(file_layout)
        
        # 第三行：API 配置
        api_layout = QHBoxLayout()
        api_layout.addWidget(QLabel("API Key:"))
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("输入 MiniMax API Key...")
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addWidget(self.api_key_edit)
        
        api_layout.addWidget(QLabel("Group ID:"))
        
        self.group_id_edit = QLineEdit()
        self.group_id_edit.setPlaceholderText("Group ID (可选)")
        api_layout.addWidget(self.group_id_edit)
        
        self.save_config_btn = QPushButton("保存配置")
        self.save_config_btn.setMaximumWidth(80)
        api_layout.addWidget(self.save_config_btn)
        
        layout.addLayout(api_layout)
        
        # 第四行：操作按钮
        action_layout = QHBoxLayout()
        
        self.execute_btn = QPushButton("批量处理图片")
        self.execute_btn.setMinimumHeight(35)
        self.execute_btn.setEnabled(False)  # 初始禁用，加载manifest后启用
        action_layout.addWidget(self.execute_btn)
        
        self.pause_btn = QPushButton("停止处理")
        self.pause_btn.setMinimumHeight(35)
        self.pause_btn.setEnabled(False)
        action_layout.addWidget(self.pause_btn)
        
        self.export_txt_btn = QPushButton("导出 TXT")
        self.export_txt_btn.setMinimumHeight(35)
        action_layout.addWidget(self.export_txt_btn)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(25)
        self.progress_bar.setVisible(False)  # 初始隐藏
        action_layout.addWidget(self.progress_bar)
        
        layout.addLayout(action_layout)
        
        return frame
    
    def create_work_area(self) -> QSplitter:
        """创建主要工作区域"""
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：提示词编辑区
        left_panel = self.create_prompt_panel()
        splitter.addWidget(left_panel)
        
        # 右侧：图片审阅区
        right_panel = self.create_review_panel()
        splitter.addWidget(right_panel)
        
        # 设置分割比例
        splitter.setSizes([400, 800])
        
        return splitter
    
    def create_prompt_panel(self) -> QGroupBox:
        """创建提示词编辑面板"""
        group = QGroupBox("提示词模板")
        layout = QVBoxLayout(group)
        
        # 系统提示词
        layout.addWidget(QLabel("系统提示词:"))
        self.system_prompt_edit = QPlainTextEdit()
        self.system_prompt_edit.setMaximumHeight(100)
        self.system_prompt_edit.setPlainText(
            "你是一个专业的图像分析师，请仔细观察图像并生成准确的英文描述。"
        )
        layout.addWidget(self.system_prompt_edit)
        
        # 用户提示词
        layout.addWidget(QLabel("用户提示词模板:"))
        self.user_prompt_edit = QPlainTextEdit()
        self.user_prompt_edit.setPlainText(
            "请为这张图片生成一个详细的英文提示词，描述图片中的内容、风格、构图等要素。"
        )
        layout.addWidget(self.user_prompt_edit)
        
        return group
    
    def create_review_panel(self) -> QSplitter:
        """创建图片审阅面板"""
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：图片列表
        left_group = QGroupBox("图片列表")
        left_layout = QVBoxLayout(left_group)
        
        # 批量操作控制
        batch_control_layout = QHBoxLayout()
        
        self.select_all_checkbox = QCheckBox("全选")
        batch_control_layout.addWidget(self.select_all_checkbox)
        
        self.batch_regenerate_btn = QPushButton("批量重新生成")
        self.batch_regenerate_btn.setEnabled(False)
        batch_control_layout.addWidget(self.batch_regenerate_btn)
        
        batch_control_layout.addStretch()
        left_layout.addLayout(batch_control_layout)
        
        self.image_list = QListWidget()
        left_layout.addWidget(self.image_list)
        
        splitter.addWidget(left_group)
        
        # 右侧：详细信息
        right_panel = self.create_detail_panel()
        splitter.addWidget(right_panel)
        
        # 设置分割比例
        splitter.setSizes([300, 500])
        
        return splitter
    
    def create_detail_panel(self) -> QWidget:
        """创建详细信息面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 图片预览区
        preview_group = QGroupBox("图片预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.image_preview = QLabel("选择图片查看预览")
        self.image_preview.setMinimumHeight(200)
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setStyleSheet("border: 1px solid gray;")
        preview_layout.addWidget(self.image_preview)
        
        layout.addWidget(preview_group)
        
        # 提示词对比区域
        prompt_group = QGroupBox("提示词")
        prompt_layout = QVBoxLayout(prompt_group)
        
        # 当前提示词（只读）
        current_label = QLabel("当前提示词:")
        current_label.setFont(QFont("Arial", 9, QFont.Bold))
        prompt_layout.addWidget(current_label)
        
        self.current_prompt_edit = QTextEdit()
        self.current_prompt_edit.setMaximumHeight(100)
        self.current_prompt_edit.setReadOnly(True)
        self.current_prompt_edit.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        prompt_layout.addWidget(self.current_prompt_edit)
        
        # 新生成的提示词（可编辑）
        new_label = QLabel("新生成的提示词:")
        new_label.setFont(QFont("Arial", 9, QFont.Bold))
        prompt_layout.addWidget(new_label)
        
        self.generated_prompt_edit = QTextEdit()
        self.generated_prompt_edit.setMaximumHeight(100)
        prompt_layout.addWidget(self.generated_prompt_edit)
        
        layout.addWidget(prompt_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.regenerate_btn = QPushButton("重新生成")
        button_layout.addWidget(self.regenerate_btn)
        
        self.approve_btn = QPushButton("通过")
        self.approve_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        button_layout.addWidget(self.approve_btn)
        
        self.reject_btn = QPushButton("拒绝")
        self.reject_btn.setStyleSheet("background-color: #f44336; color: white;")
        button_layout.addWidget(self.reject_btn)
        
        layout.addLayout(button_layout)
        
        return widget
    
    def setup_connections(self):
        """设置信号连接"""
        # 文件夹和Manifest相关
        self.browse_folder_btn.clicked.connect(self.browse_image_folder)
        self.create_manifest_btn.clicked.connect(self.create_manifest_from_folder)
        self.browse_btn.clicked.connect(self.browse_manifest_file)
        self.load_btn.clicked.connect(self.load_manifest)
        
        # 配置和处理相关
        self.save_config_btn.clicked.connect(self.save_config)
        self.execute_btn.clicked.connect(self.start_batch_processing)
        self.pause_btn.clicked.connect(self.stop_batch_processing)
        self.export_txt_btn.clicked.connect(self.export_txt_files)
        
        # 图片审阅相关
        self.image_list.currentItemChanged.connect(self.on_image_selected)
        self.approve_btn.clicked.connect(self.approve_current_image)
        self.reject_btn.clicked.connect(self.reject_current_image)
        self.regenerate_btn.clicked.connect(self.regenerate_current_image)
        
        # 批量操作相关
        self.select_all_checkbox.stateChanged.connect(self.on_select_all_changed)
        self.batch_regenerate_btn.clicked.connect(self.start_batch_regenerate)
    
    def browse_manifest_file(self):
        """浏览选择 manifest 文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择 Manifest 文件", "", "CSV files (*.csv)"
        )
        if file_path:
            self.manifest_path_edit.setText(file_path)
    
    def load_manifest(self):
        """加载 manifest 文件"""
        manifest_path = self.manifest_path_edit.text().strip()
        if not manifest_path:
            QMessageBox.warning(self, "警告", "请先选择 manifest 文件")
            return
        
        try:
            self.current_manifest_path = Path(manifest_path)
            self.manifest_manager = ManifestManager(self.current_manifest_path)
            self.manifest_manager.load_from_csv()
            
            # 更新图片列表
            self.update_image_list()
            self.execute_btn.setEnabled(True)  # 启用批量处理按钮
            self.status_bar.showMessage(f"已加载 {len(self.manifest_manager.records)} 个记录")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载 manifest 文件失败:\n{e}")
    
    def update_image_list(self):
        """更新图片列表显示"""
        if not self.manifest_manager:
            return
        
        self.image_list.clear()
        for record in self.manifest_manager.records:
            # 创建包含复选框的自定义widget
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(5, 2, 5, 2)
            
            # 复选框
            checkbox = QCheckBox()
            checkbox.setProperty("record", record)  # 绑定记录
            checkbox.stateChanged.connect(self.on_item_checkbox_changed)
            item_layout.addWidget(checkbox)
            
            # 状态和文件名标签
            status_label = QLabel(f"{record.status.value} | {record.filepath}")
            item_layout.addWidget(status_label)
            
            item_layout.addStretch()
            
            # 创建列表项
            item = QListWidgetItem()
            item.setData(Qt.UserRole, record)
            item.setSizeHint(item_widget.sizeHint())
            
            self.image_list.addItem(item)
            self.image_list.setItemWidget(item, item_widget)
    
    def on_image_selected(self, current_item, previous_item):
        """当选择图片时的处理"""
        if not current_item:
            return
        
        record = current_item.data(Qt.UserRole)
        if record:
            # 显示当前提示词（原始）
            self.current_prompt_edit.setPlainText(record.prompt_en)
            
            # 如果有临时的新提示词，显示在新生成区域
            if hasattr(record, 'temp_new_prompt') and record.temp_new_prompt:
                self.generated_prompt_edit.setPlainText(record.temp_new_prompt)
                # 启用通过/拒绝按钮
                self.approve_btn.setEnabled(True)
                self.reject_btn.setEnabled(True)
            else:
                # 清空新生成区域
                self.generated_prompt_edit.setPlainText("")
                # 禁用通过/拒绝按钮
                self.approve_btn.setEnabled(False)
                self.reject_btn.setEnabled(False)
            
            # 加载和显示图片预览
            self.load_image_preview(record.filepath)
    
    def load_image_preview(self, filepath: str):
        """加载并显示图片预览"""
        try:
            # 构建完整的图片路径
            if self.current_manifest_path:
                image_folder = self.current_manifest_path.parent
                full_path = image_folder / filepath
            else:
                folder_path = self.folder_path_edit.text().strip()
                if folder_path:
                    full_path = Path(folder_path) / filepath
                else:
                    self.image_preview.setText(f"无法确定图片路径: {filepath}")
                    return
            
            if not full_path.exists():
                self.image_preview.setText(f"图片文件不存在: {filepath}")
                return
            
            # 加载图片
            from PySide6.QtGui import QPixmap
            from PySide6.QtCore import Qt
            pixmap = QPixmap(str(full_path))
            
            if pixmap.isNull():
                self.image_preview.setText(f"无法加载图片: {filepath}")
                return
            
            # 缩放图片以适应预览区域
            preview_size = self.image_preview.size()
            if preview_size.width() > 50 and preview_size.height() > 50:  # 确保有合理的尺寸
                scaled_pixmap = pixmap.scaled(
                    preview_size, 
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_preview.setPixmap(scaled_pixmap)
            else:
                # 如果预览区域太小，使用默认尺寸
                scaled_pixmap = pixmap.scaled(
                    300, 200,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_preview.setPixmap(scaled_pixmap)
                
        except Exception as e:
            self.image_preview.setText(f"加载图片失败: {filepath}\n错误: {str(e)}")
    
    def load_config_to_ui(self):
        """从配置加载到UI"""
        try:
            if settings.api_key:
                self.api_key_edit.setText(settings.api_key)
            if settings.group_id:
                self.group_id_edit.setText(settings.group_id)
            if settings.system_prompt:
                self.system_prompt_edit.setPlainText(settings.system_prompt)
        except Exception as e:
            self.status_bar.showMessage(f"加载配置失败: {e}")
    
    def save_config(self):
        """保存配置"""
        try:
            settings.api_key = self.api_key_edit.text().strip()
            settings.group_id = self.group_id_edit.text().strip() or None
            settings.system_prompt = self.system_prompt_edit.toPlainText()
            
            settings.save_to_file()
            QMessageBox.information(self, "成功", "配置已保存")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败:\n{e}")
    
    def browse_image_folder(self):
        """浏览选择图片文件夹"""
        folder_path = QFileDialog.getExistingDirectory(
            self, "选择图片文件夹", ""
        )
        if folder_path:
            self.folder_path_edit.setText(folder_path)
    
    def create_manifest_from_folder(self):
        """从文件夹创建新的manifest"""
        folder_path = self.folder_path_edit.text().strip()
        if not folder_path:
            QMessageBox.warning(self, "警告", "请先选择图片文件夹")
            return
        
        folder = Path(folder_path)
        if not folder.exists():
            QMessageBox.warning(self, "警告", "选择的文件夹不存在")
            return
        
        try:
            # 扫描图片文件
            image_extensions = ['.jpg', '.jpeg', '.png', '.webp']
            image_files = []
            
            for ext in image_extensions:
                image_files.extend(folder.rglob(f'*{ext}'))
                image_files.extend(folder.rglob(f'*{ext.upper()}'))
            
            if not image_files:
                QMessageBox.warning(self, "警告", "在选择的文件夹中没有找到图片文件")
                return
            
            # 创建manifest文件
            manifest_path = folder / "manifest.csv"
            self.current_manifest_path = manifest_path
            self.manifest_manager = ManifestManager(manifest_path)
            
            # 添加图片记录
            for img_file in image_files:
                relative_path = img_file.relative_to(folder)
                record = ImageRecord(
                    filepath=str(relative_path),
                    prompt_en="",
                    prompt_cn="",
                    status=ProcessStatus.PENDING,
                    retry_cnt=0
                )
                self.manifest_manager.records.append(record)
            
            # 保存manifest
            self.manifest_manager.save_to_csv()
            
            # 更新UI
            self.manifest_path_edit.setText(str(manifest_path))
            self.update_image_list()
            self.execute_btn.setEnabled(True)
            
            QMessageBox.information(
                self, "成功", 
                f"成功创建manifest文件，包含 {len(image_files)} 张图片"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建manifest失败:\n{e}")
    
    def start_batch_processing(self):
        """开始批量处理图片"""
        if not self.manifest_manager:
            QMessageBox.warning(self, "警告", "请先加载manifest文件")
            return
        
        # 检查API配置
        api_key = self.api_key_edit.text().strip()
        if not api_key:
            QMessageBox.warning(self, "警告", "请先输入API Key")
            return
        
        # 确认是否开始处理
        pending_count = sum(1 for record in self.manifest_manager.records 
                          if record.status == ProcessStatus.PENDING)
        
        if pending_count == 0:
            QMessageBox.information(self, "信息", "没有待处理的图片")
            return
        
        reply = QMessageBox.question(
            self, "确认", 
            f"将逐张处理 {pending_count} 张待处理的图片，是否继续？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            # 更新配置
            settings.api_key = api_key
            settings.group_id = self.group_id_edit.text().strip() or None
            settings.system_prompt = self.system_prompt_edit.toPlainText()
            
            # 获取图片文件夹路径
            if self.current_manifest_path:
                image_folder = self.current_manifest_path.parent
            else:
                image_folder = Path(self.folder_path_edit.text().strip())
            
            if not image_folder.exists():
                QMessageBox.warning(self, "警告", "无法确定图片文件夹路径")
                return
            
            # 启动后台处理线程
            self.processing_thread = BatchProcessingThread(
                manifest_manager=self.manifest_manager,
                image_folder=image_folder,
                prompt_template=self.user_prompt_edit.toPlainText(),
                system_prompt=self.system_prompt_edit.toPlainText()
            )
            
            # 连接信号
            self.processing_thread.progress_updated.connect(self.on_progress_updated)
            self.processing_thread.image_processed.connect(self.on_image_processed)
            self.processing_thread.processing_finished.connect(self.on_processing_finished)
            self.processing_thread.error_occurred.connect(self.on_error_occurred)
            
            # 更新UI状态
            self.execute_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.progress_bar.setMaximum(pending_count)
            
            # 启动线程
            self.processing_thread.start()
            self.status_bar.showMessage("正在逐张处理图片...")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动批量处理失败:\n{e}")
    
    def stop_batch_processing(self):
        """停止批量处理"""
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.stop_processing()
            self.processing_thread.wait(3000)  # 等待最多3秒
            self.status_bar.showMessage("正在停止处理...")
    
    def on_progress_updated(self, current: int, total: int, current_image: str):
        """处理进度更新"""
        self.progress_bar.setValue(current)
        self.status_bar.showMessage(f"处理中 ({current}/{total}): {current_image}")
    
    def on_image_processed(self, image_path: str, prompt: str, success: bool):
        """单张图片处理完成"""
        status = "✅" if success else "❌"
        print(f"{status} {image_path}: {prompt[:50]}...")
        
        # 更新图片列表显示
        self.update_image_list()
    
    def on_processing_finished(self, success_count: int, total_count: int):
        """批量处理完成"""
        # 重置UI状态
        self.execute_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        # 显示结果
        self.status_bar.showMessage(f"处理完成：成功 {success_count}/{total_count} 张图片")
        QMessageBox.information(
            self, "处理完成", 
            f"批量处理已完成！\n\n成功处理: {success_count} 张\n总计: {total_count} 张"
        )
        
        # 更新图片列表
        self.update_image_list()
    
    def on_error_occurred(self, error_message: str):
        """处理错误"""
        QMessageBox.critical(self, "处理错误", error_message)
        
        # 重置UI状态
        self.execute_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("处理失败")
    
    ############################################
    # 2. 槽函数 —— 线程回调
    ############################################
    def on_image_regenerated(self, img_path: str, prompt: str, success: bool):
        """重新生成完成回调"""
        # 重新启用按钮
        self.regenerate_btn.setEnabled(True)
        
        # 清理线程引用
        if self.regen_thread:
            self.regen_thread.deleteLater()
            self.regen_thread = None

        # 将绝对路径转为 manifest 中的相对路径
        base = self.current_manifest_path.parent if self.current_manifest_path \
               else Path(self.folder_path_edit.text().strip())
        try:
            rel_path = str(Path(img_path).relative_to(base))
        except Exception:
            rel_path = Path(img_path).name

        # 更新记录
        if self.manifest_manager:
            updated = False
            for rec in self.manifest_manager.records:
                if rec.filepath == rel_path:
                    if success:
                        # 将新生成的提示词保存为临时属性，用于对比
                        rec.temp_new_prompt = prompt
                        rec.retry_cnt += 1
                        
                        # 更新UI显示 - 显示新旧对比
                        self.current_prompt_edit.setPlainText(rec.prompt_en)  # 显示原始提示词
                        self.generated_prompt_edit.setPlainText(prompt)  # 显示新生成的提示词
                        
                        # 启用通过/拒绝按钮
                        self.approve_btn.setEnabled(True)
                        self.reject_btn.setEnabled(True)
                    else:
                        # 失败时清理临时属性
                        if hasattr(rec, 'temp_new_prompt'):
                            delattr(rec, 'temp_new_prompt')
                    updated = True
                    break
            
            if not updated:
                QMessageBox.warning(self, "警告", f"未找到对应的记录: {rel_path}")

        # 显示结果
        if success:
            self.status_bar.showMessage(f"重新生成成功: {Path(img_path).name} - 请选择通过或拒绝")
            QMessageBox.information(self, "成功", f"重新生成成功！\n\n文件: {Path(img_path).name}\n提示词长度: {len(prompt)} 字符\n\n请查看新旧提示词对比，然后选择通过或拒绝。")
        else:
            self.status_bar.showMessage("重新生成失败")
            QMessageBox.warning(self, "重新生成失败", f"处理失败:\n{prompt}")
    
    def on_regeneration_progress(self, message: str):
        """重新生成进度更新"""
        self.status_bar.showMessage(message)
    
    def on_regeneration_error(self, error_message: str):
        """重新生成错误处理"""
        # 重新启用按钮
        self.regenerate_btn.setEnabled(True)
        
        # 清理线程引用
        if self.regen_thread:
            self.regen_thread.deleteLater()
            self.regen_thread = None
        
        # 显示错误
        self.status_bar.showMessage("重新生成失败")
        QMessageBox.critical(self, "重新生成错误", error_message)
    
    def _create_txt_file_for_record(self, record: 'ImageRecord', base_path: Path):
        """为记录创建TXT文件"""
        try:
            image_path = base_path / record.filepath
            txt_path = image_path.with_suffix(".txt")
            
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(record.prompt_en)
            
            print(f"✅ 自动创建TXT文件: {txt_path}")
            
        except Exception as e:
            print(f"❌ 创建TXT文件失败 {record.filepath}: {e}")
    
    ############################################
    # 3. 完善的重新生成功能
    ############################################
    def regenerate_current_image(self):
        """重新生成当前图片的提示词"""
        # 检查是否有选中的图片
        current_item = self.image_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一张图片")
            return
        
        record = current_item.data(Qt.UserRole)
        if not record:
            QMessageBox.warning(self, "警告", "无法获取图片记录")
            return

        # 检查是否正在处理
        if self.regen_thread and self.regen_thread.isRunning():
            QMessageBox.warning(self, "警告", "正在处理中，请稍候...")
            return

        # 验证API配置
        api_key = self.api_key_edit.text().strip()
        if not api_key:
            QMessageBox.warning(self, "警告", "请先输入 API Key")
            return

        # 验证提示词模板
        user_prompt = self.user_prompt_edit.toPlainText().strip()
        if not user_prompt:
            QMessageBox.warning(self, "警告", "请先输入用户提示词模板")
            return

        # 构造完整路径
        image_folder = self.current_manifest_path.parent if self.current_manifest_path \
                       else Path(self.folder_path_edit.text().strip())
        image_path = image_folder / record.filepath
        
        if not image_path.exists():
            QMessageBox.warning(self, "警告", f"图片文件不存在:\n{image_path}")
            return

        # 确认操作
        reply = QMessageBox.question(
            self, "确认重新生成", 
            f"确定要重新生成以下图片的提示词吗？\n\n"
            f"文件: {record.filepath}\n"
            f"当前重试次数: {record.retry_cnt}\n\n"
            f"重新生成将会覆盖现有的提示词。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return

        # 启动重新生成
        self._start_regeneration(image_path, user_prompt)
    
    def _start_regeneration(self, image_path: Path, user_prompt: str):
        """启动重新生成过程"""
        try:
            # 禁用按钮防止重复点击
            self.regenerate_btn.setEnabled(False)
            self.status_bar.showMessage(f"正在重新生成: {image_path.name}")

            # 创建并启动线程
            self.regen_thread = SingleImageProcessingThread(
                image_path      = image_path,
                prompt_template = user_prompt,
                system_prompt   = self.system_prompt_edit.toPlainText().strip()
            )
            
            # 连接信号
            self.regen_thread.finished.connect(self.on_image_regenerated)
            self.regen_thread.error.connect(self.on_regeneration_error)
            self.regen_thread.progress.connect(self.on_regeneration_progress)
            
            # 启动线程
            self.regen_thread.start()
            
        except Exception as e:
            self.regenerate_btn.setEnabled(True)
            QMessageBox.critical(self, "启动失败", f"无法启动重新生成过程:\n{e}")
    
    def _cleanup_regen_thread(self):
        """清理重新生成线程"""
        if self.regen_thread:
            if self.regen_thread.isRunning():
                self.regen_thread.stop_processing()
                self.regen_thread.wait(3000)  # 等待最多3秒
            self.regen_thread.deleteLater()
            self.regen_thread = None
    
    def export_txt_files(self):
        """导出 TXT 文件"""
        if not self.manifest_manager:
            QMessageBox.warning(self, "警告", "请先加载 manifest 文件")
            return
        
        try:
            exported_count = self.manifest_manager.export_to_txt_files()
            QMessageBox.information(self, "成功", f"成功导出 {exported_count} 个 TXT 文件")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败:\n{e}")
    
    def approve_current_image(self):
        """通过当前图片 - 使用新生成的提示词"""
        current_item = self.image_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一张图片")
            return
            
        record = current_item.data(Qt.UserRole)
        if not record:
            QMessageBox.warning(self, "警告", "无法获取图片记录")
            return
            
        # 检查是否有新生成的提示词
        if not hasattr(record, 'temp_new_prompt') or not record.temp_new_prompt:
            QMessageBox.warning(self, "警告", "没有新生成的提示词可以通过")
            return
            
        try:
            # 使用新生成的提示词替换原有的
            record.prompt_en = record.temp_new_prompt
            record.status = ProcessStatus.APPROVED
            
            # 创建TXT文件
            image_folder = self.current_manifest_path.parent if self.current_manifest_path \
                           else Path(self.folder_path_edit.text().strip())
            self._create_txt_file_for_record(record, image_folder)
            
            # 清理临时属性
            delattr(record, 'temp_new_prompt')
            
            # 保存更改
            if self.manifest_manager:
                self.manifest_manager.save_to_csv()
                self.update_image_list()
                
            # 更新UI显示
            self.current_prompt_edit.setPlainText(record.prompt_en)
            self.generated_prompt_edit.setPlainText("")
            
            # 禁用通过/拒绝按钮
            self.approve_btn.setEnabled(False)
            self.reject_btn.setEnabled(False)
            
            self.status_bar.showMessage(f"✅ 已通过新提示词: {record.filepath}")
            QMessageBox.information(self, "成功", "新提示词已通过并保存！")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"通过提示词时出错:\n{e}")
    
    def reject_current_image(self):
        """拒绝当前图片 - 删除新生成的提示词"""
        current_item = self.image_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一张图片")
            return
            
        record = current_item.data(Qt.UserRole)
        if not record:
            QMessageBox.warning(self, "警告", "无法获取图片记录")
            return
            
        # 检查是否有新生成的提示词
        if not hasattr(record, 'temp_new_prompt') or not record.temp_new_prompt:
            QMessageBox.warning(self, "警告", "没有新生成的提示词可以拒绝")
            return
            
        try:
            # 清理临时属性（拒绝新提示词）
            delattr(record, 'temp_new_prompt')
            
            # 更新UI显示 - 恢复原有提示词
            self.current_prompt_edit.setPlainText(record.prompt_en)
            self.generated_prompt_edit.setPlainText("")
            
            # 禁用通过/拒绝按钮
            self.approve_btn.setEnabled(False)
            self.reject_btn.setEnabled(False)
            
            self.status_bar.showMessage(f"❌ 已拒绝新提示词: {record.filepath}")
            QMessageBox.information(self, "拒绝", "新提示词已拒绝，保留原有提示词。")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"拒绝提示词时出错:\n{e}")

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        # 检查是否有正在运行的线程
        threads_running = []
        
        if self.processing_thread and self.processing_thread.isRunning():
            threads_running.append("批量处理")
        
        if self.regen_thread and self.regen_thread.isRunning():
            threads_running.append("重新生成")
        
        if threads_running:
            reply = QMessageBox.question(
                self, "确认退出", 
                f"以下任务正在运行:\n• {chr(10).join(threads_running)}\n\n"
                f"确定要退出程序吗？\n(正在运行的任务将被强制停止)",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                event.ignore()
                return
        
        # 停止并清理所有线程
        self._cleanup_all_threads()
        
        # 保存配置
        try:
            self.save_config()
        except Exception as e:
            print(f"保存配置时出错: {e}")
        
        # 接受关闭事件
        event.accept()
    
    def _cleanup_all_threads(self):
        """清理所有线程"""
        # 清理批量处理线程
        if self.processing_thread:
            if self.processing_thread.isRunning():
                self.processing_thread.stop_processing()
                self.processing_thread.wait(3000)
            self.processing_thread.deleteLater()
            self.processing_thread = None
        
        # 清理重新生成线程
        self._cleanup_regen_thread()
        
        # 清理批量重新生成线程
        self._cleanup_batch_regen_thread()
    
    def _cleanup_batch_regen_thread(self):
        """清理批量重新生成线程"""
        if self.batch_regen_thread:
            if self.batch_regen_thread.isRunning():
                self.batch_regen_thread.stop_processing()
                self.batch_regen_thread.wait(3000)
            self.batch_regen_thread.deleteLater()
            self.batch_regen_thread = None

    ############################################
    # 批量重新生成功能
    ############################################
    def on_select_all_changed(self, state):
        """全选/全不选复选框状态改变"""
        is_checked = state == Qt.CheckState.Checked
        
        for i in range(self.image_list.count()):
            item = self.image_list.item(i)
            widget = self.image_list.itemWidget(item)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(is_checked)
    
    def on_item_checkbox_changed(self):
        """单个复选框状态改变"""
        # 更新批量重新生成按钮状态
        selected_count = self.get_selected_records_count()
        self.batch_regenerate_btn.setEnabled(selected_count > 0)
        
        # 更新全选复选框状态
        total_count = self.image_list.count()
        if selected_count == 0:
            self.select_all_checkbox.setChecked(False)
        elif selected_count == total_count:
            self.select_all_checkbox.setChecked(True)
        else:
            self.select_all_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
    
    def get_selected_records_count(self):
        """获取选中的记录数量"""
        count = 0
        for i in range(self.image_list.count()):
            item = self.image_list.item(i)
            widget = self.image_list.itemWidget(item)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    count += 1
        return count
    
    def get_selected_records(self):
        """获取选中的记录列表"""
        selected_records = []
        for i in range(self.image_list.count()):
            item = self.image_list.item(i)
            widget = self.image_list.itemWidget(item)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    record = checkbox.property("record")
                    if record:
                        selected_records.append(record)
        return selected_records
    
    def start_batch_regenerate(self):
        """开始批量重新生成"""
        # 检查是否有选中的图片
        selected_records = self.get_selected_records()
        if not selected_records:
            QMessageBox.warning(self, "警告", "请先选择要重新生成的图片")
            return
        
        # 检查是否正在处理
        if (self.batch_regen_thread and self.batch_regen_thread.isRunning()) or \
           (self.regen_thread and self.regen_thread.isRunning()) or \
           (self.processing_thread and self.processing_thread.isRunning()):
            QMessageBox.warning(self, "警告", "有其他任务正在处理中，请稍候...")
            return
        
        # 验证API配置
        api_key = self.api_key_edit.text().strip()
        if not api_key:
            QMessageBox.warning(self, "警告", "请先输入 API Key")
            return
        
        # 验证提示词模板
        user_prompt = self.user_prompt_edit.toPlainText().strip()
        if not user_prompt:
            QMessageBox.warning(self, "警告", "请先输入用户提示词模板")
            return
        
        # 构建图片路径列表
        image_folder = self.current_manifest_path.parent if self.current_manifest_path \
                       else Path(self.folder_path_edit.text().strip())
        
        image_paths = []
        for record in selected_records:
            image_path = image_folder / record.filepath
            if image_path.exists():
                image_paths.append(image_path)
            else:
                QMessageBox.warning(self, "警告", f"图片文件不存在: {image_path}")
                return
        
        # 确认操作
        reply = QMessageBox.question(
            self, "确认批量重新生成", 
            f"确定要重新生成以下 {len(selected_records)} 张图片的提示词吗？\n\n"
            f"这将为每张图片生成新的提示词用于对比。\n"
            f"您可以逐个选择通过或拒绝。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 启动批量重新生成
        self._start_batch_regeneration(image_paths, user_prompt)
    
    def _start_batch_regeneration(self, image_paths: list, user_prompt: str):
        """启动批量重新生成过程"""
        try:
            # 禁用相关按钮
            self.batch_regenerate_btn.setEnabled(False)
            self.regenerate_btn.setEnabled(False)
            self.execute_btn.setEnabled(False)
            
            # 显示进度条
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(len(image_paths))
            self.progress_bar.setValue(0)
            
            self.status_bar.showMessage(f"开始批量重新生成 {len(image_paths)} 张图片...")
            
            # 创建并启动线程
            self.batch_regen_thread = BatchRegenerateThread(
                image_paths=image_paths,
                prompt_template=user_prompt,
                system_prompt=self.system_prompt_edit.toPlainText().strip()
            )
            
            # 连接信号
            self.batch_regen_thread.progress_updated.connect(self.on_batch_regen_progress)
            self.batch_regen_thread.image_regenerated.connect(self.on_batch_regen_image_done)
            self.batch_regen_thread.batch_finished.connect(self.on_batch_regen_finished)
            self.batch_regen_thread.error_occurred.connect(self.on_batch_regen_error)
            
            # 启动线程
            self.batch_regen_thread.start()
            
        except Exception as e:
            # 恢复按钮状态
            self.batch_regenerate_btn.setEnabled(True)
            self.regenerate_btn.setEnabled(True)
            self.execute_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, "启动失败", f"无法启动批量重新生成过程:\n{e}")
    
    def on_batch_regen_progress(self, current: int, total: int, current_image: str):
        """批量重新生成进度更新"""
        self.progress_bar.setValue(current)
        self.status_bar.showMessage(f"正在处理 ({current}/{total}): {current_image}")
    
    def on_batch_regen_image_done(self, img_path: str, prompt: str, success: bool):
        """批量重新生成单张图片完成"""
        # 找到对应的记录并更新
        base = self.current_manifest_path.parent if self.current_manifest_path \
               else Path(self.folder_path_edit.text().strip())
        
        try:
            rel_path = str(Path(img_path).relative_to(base))
        except Exception:
            rel_path = Path(img_path).name
        
        if self.manifest_manager:
            for rec in self.manifest_manager.records:
                if rec.filepath == rel_path:
                    if success:
                        # 保存新生成的提示词为临时属性
                        rec.temp_new_prompt = prompt
                        rec.retry_cnt += 1
                        print(f"✅ 批量重新生成成功: {rel_path}")
                    else:
                        print(f"❌ 批量重新生成失败: {rel_path} - {prompt}")
                    break
    
    def on_batch_regen_finished(self, success_count: int, total_count: int):
        """批量重新生成完成"""
        # 恢复按钮状态
        self.batch_regenerate_btn.setEnabled(True)
        self.regenerate_btn.setEnabled(True)
        self.execute_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # 更新图片列表显示
        self.update_image_list()
        
        # 显示完成消息
        self.status_bar.showMessage(f"批量重新生成完成: {success_count}/{total_count} 成功")
        QMessageBox.information(
            self, "批量重新生成完成", 
            f"批量重新生成完成！\n\n"
            f"成功: {success_count} 张\n"
            f"失败: {total_count - success_count} 张\n"
            f"总计: {total_count} 张\n\n"
            f"请在图片列表中逐个查看并选择通过或拒绝新生成的提示词。"
        )
        
        # 清理线程
        self._cleanup_batch_regen_thread()
    
    def on_batch_regen_error(self, error_message: str):
        """批量重新生成错误处理"""
        # 恢复按钮状态
        self.batch_regenerate_btn.setEnabled(True)
        self.regenerate_btn.setEnabled(True)
        self.execute_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # 显示错误
        self.status_bar.showMessage("批量重新生成失败")
        QMessageBox.critical(self, "批量重新生成错误", error_message)
        
        # 清理线程
        self._cleanup_batch_regen_thread()


def run_gui():
    """运行 GUI 应用"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui() 