# UI显示与TXT导出分离功能说明

## 功能概述

根据用户需求，我们实现了**UI显示完整内容，TXT导出只保存英文**的功能。这样既方便用户在界面上审阅完整的中英文对照内容，又确保训练用的TXT文件只包含纯英文提示词。

## 工作原理

### 1. 数据存储策略
- **Manifest记录**：保存完整的中英文对照内容
- **UI显示**：从manifest读取完整内容显示给用户
- **TXT导出**：实时分离英文部分，只写入英文内容

### 2. 分离时机
- **批量处理**：保存完整内容到manifest，创建TXT时分离英文
- **单张重新生成**：UI显示完整内容，用户审阅后保存时分离
- **手动保存**：保存完整内容到manifest，创建TXT时分离
- **导出功能**：从manifest读取完整内容，导出时分离英文

## 具体实现

### 1. 批量处理逻辑
```python
# 保存完整的提示词到记录中（包含中英文）
record.prompt_en = generated_prompt

# 创建TXT文件时分离英文部分
prompt_en, prompt_cn = split_chinese_english(generated_prompt)
self._create_txt_file(image_path, prompt_en)
```

### 2. 审阅界面显示
- **当前提示词编辑框**：显示完整的中英文对照内容
- **新生成的提示词编辑框**：显示完整的中英文对照内容
- 用户可以在界面上看到完整内容进行审阅和编辑

### 3. 保存操作
- **保存当前**：保存完整内容到manifest，分离英文创建TXT
- **通过**：保存完整内容到manifest，分离英文创建TXT
- **拒绝**：保存修改后的完整内容，分离英文创建TXT

### 4. 导出功能
```python
def export_to_txt_files(self, output_dir: Optional[Path] = None) -> int:
    # 从manifest读取完整内容
    for record in approved_records:
        # 分离中英文，只写入英文部分
        prompt_en, prompt_cn = split_chinese_english(record.prompt_en)
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(prompt_en)
```

## 用户体验

### 审阅阶段
1. **完整内容显示**：用户在界面上看到完整的中英文对照
2. **方便对比**：可以同时查看中英文内容，确保翻译准确
3. **灵活编辑**：可以修改中英文内容，保持对照关系

### 训练阶段
1. **纯英文TXT**：训练时只使用英文提示词，避免中文干扰
2. **自动分离**：无需手动处理，系统自动分离英文部分
3. **保持备份**：中文内容保存在manifest中，可随时查看

## 技术细节

### 1. 中英文分离算法
```python
def split_chinese_english(text: str):
    """将中英混合的提示词拆分为英文部分和中文部分"""
    import re
    
    english_lines = []
    chinese_lines = []
    
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # 判断是否包含中文字符
        if re.search(r"[\u4e00-\u9fff]", stripped):
            chinese_lines.append(stripped)
        else:
            english_lines.append(stripped)
    
    return "\n".join(english_lines), "\n".join(chinese_lines)
```

### 2. 文件操作
- **Manifest文件**：保存完整内容，便于后续查看和编辑
- **TXT文件**：只保存英文部分，直接用于LoRA训练
- **实时分离**：每次保存TXT时都重新分离，确保最新内容

## 优势特点

### 1. 用户友好
- ✅ 界面显示完整内容，方便审阅
- ✅ 保持中英文对照关系
- ✅ 支持灵活编辑和修改

### 2. 训练优化
- ✅ TXT文件只包含英文，避免中文干扰
- ✅ 自动分离处理，无需手动操作
- ✅ 确保训练数据纯净

### 3. 数据完整性
- ✅ 完整内容保存在manifest中
- ✅ 中文内容不丢失，可随时查看
- ✅ 支持版本控制和回滚

## 测试验证

通过 `test_ui_display.py` 脚本验证：
- ✅ UI界面显示完整的中英文对照内容
- ✅ TXT文件导出只包含英文部分
- ✅ 中文内容正确分离并保存在manifest中
- ✅ 导出功能正常工作

## 注意事项

1. **编辑建议**：在界面编辑时，建议保持中英文对照格式
2. **分离准确性**：分离算法基于Unicode字符范围，准确率高
3. **备份重要性**：manifest文件包含完整内容，请定期备份
4. **训练兼容性**：TXT文件格式符合LoRA训练标准

这个功能完美平衡了用户体验和训练需求，既保证了界面的易用性，又确保了训练数据的质量。 