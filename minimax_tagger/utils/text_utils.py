def split_chinese_english(text: str):
    """将中英混合的提示词拆分为英文部分和中文部分。

    简单按行拆分，若行中包含中文字符（Unicode 范围 \u4e00-\u9fff）则视为中文，否则视为英文。
    返回 (英文, 中文) 元组，两部分均用换行拼接。
    """
    import re

    english_lines = []
    chinese_lines = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            # 跳过空行
            continue
        # 判断是否包含中文字符
        if re.search(r"[\u4e00-\u9fff]", stripped):
            chinese_lines.append(stripped)
        else:
            english_lines.append(stripped)

    return "\n".join(english_lines), "\n".join(chinese_lines) 