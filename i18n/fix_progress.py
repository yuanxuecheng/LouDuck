#!/usr/bin/env python3
"""Add self.tr() to hardcoded Chinese strings in progress emit / status labels."""

from pathlib import Path

src = Path(__file__).parent.parent / "src" / "main_gui.py"
text = src.read_text(encoding="utf-8")

# sub_step.emit strings
replaces = [
    ('self.sub_step.emit("准备音频...", 0)', 'self.sub_step.emit(self.tr("准备音频..."), 0)'),
    ('self.sub_step.emit("加载完成", 15)', 'self.sub_step.emit(self.tr("加载完成"), 15)'),
    ('self.sub_step.emit("读取ADM...", 5)', 'self.sub_step.emit(self.tr("读取 ADM..."), 5)'),
    ('self.sub_step.emit("ADM加载完成", 15)', 'self.sub_step.emit(self.tr("ADM 加载完成"), 15)'),
    ('self.sub_step.emit("分析文件...", 2)', 'self.sub_step.emit(self.tr("分析文件..."), 2)'),
    ('self.sub_step.emit("多单声道加载完成", 15)', 'self.sub_step.emit(self.tr("多单声道加载完成"), 15)'),
    ('self.sub_step.emit("开始测量...", 20)', 'self.sub_step.emit(self.tr("开始测量..."), 20)'),
    ('self.sub_step.emit("计算最终指标...", 90)', 'self.sub_step.emit(self.tr("计算最终指标..."), 90)'),
    ('self.sub_step.emit("整理结果...", 95)', 'self.sub_step.emit(self.tr("整理结果..."), 95)'),
    ('self.sub_step.emit("完成", 100)', 'self.sub_step.emit(self.tr("完成"), 100)'),
    # line 1678 which failed earlier
    ('self.filename_label.setText(f"✓ 渲染: {p.name}")', 'self.filename_label.setText(self.tr("✓ 渲染: {name}").format(name=p.name))'),
    # ADM info messages
    ('self.adm_info.setPlainText("正在解析ADM...")', 'self.adm_info.setPlainText(self.tr("正在解析 ADM..."))'),
    ('self.adm_info.setPlainText("[错误] 无法解析ADM元数据\\n\\n可能原因：\\n1. 文件不是有效的ADM/BW64格式\\n2. XML命名空间不匹配")',
     'self.adm_info.setPlainText(self.tr("[错误] 无法解析 ADM 元数据\\n\\n可能原因：\\n1. 文件不是有效的 ADM/BW64 格式\\n2. XML 命名空间不匹配"))'),
    ('self.adm_info.setPlainText("[警告] ADM元数据解析为空\\n\\n可能原因：\\n1. 命名空间检测失败\\n2. 文件不包含ADM数据")',
     'self.adm_info.setPlainText(self.tr("[警告] ADM 元数据解析为空\\n\\n可能原因：\\n1. 命名空间检测失败\\n2. 文件不包含 ADM 数据"))'),
]

for old, new in replaces:
    if old in text:
        text = text.replace(old, new, 1)
    else:
        print(f"WARN: not found: {old[:60]}...")

# f-strings with Chinese fragments that need tr() wrapping
# "测量中... {current_block}/{total_blocks}块{speed_str}"
old = 'self.sub_step.emit(f"测量中... {current_block}/{total_blocks}块{speed_str}", int(progress_pct))'
new = 'self.sub_step.emit(self.tr("测量中... {current_block}/{total_blocks} 块{speed_str}").format(current_block=current_block, total_blocks=total_blocks, speed_str=speed_str), int(progress_pct))'
text = text.replace(old, new, 1)

# "初始化: {num_channels}ch, {actual_duration:.1f}s"
old = 'self.sub_step.emit(f"初始化: {num_channels}ch, {actual_duration:.1f}s", 15)'
new = 'self.sub_step.emit(self.tr("初始化: {num_channels} ch, {actual_duration:.1f} s").format(num_channels=num_channels, actual_duration=actual_duration), 15)'
text = text.replace(old, new, 1)

# "加载中... {mb_loaded:.1f}/{mb_total:.1f}MB"
old = 'self.sub_step.emit(f"加载中... {mb_loaded:.1f}/{mb_total:.1f}MB", int(progress))'
new = 'self.sub_step.emit(self.tr("加载中... {mb_loaded:.1f}/{mb_total:.1f} MB").format(mb_loaded=mb_loaded, mb_total=mb_total), int(progress))'
text = text.replace(old, new, 1)

src.write_text(text, encoding="utf-8")
print("Done.")
