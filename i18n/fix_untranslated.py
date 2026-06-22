#!/usr/bin/env python3
"""Add self.tr() to hardcoded Chinese UI strings in main_gui.py."""

from pathlib import Path

src = Path(__file__).parent.parent / "src" / "main_gui.py"
text = src.read_text(encoding="utf-8")

# ---------- 1. 右侧结果表格表头 + 行标签 ----------
# line 1482
old = 'self.result_table.setHorizontalHeaderLabels(["指标", "数值"])'
new = 'self.result_table.setHorizontalHeaderLabels([self.tr("指标"), self.tr("数值")])'
text = text.replace(old, new, 1)

# line 1486
old = '''metrics = ["节目响度(I)", "最大短时响度(S)", "最大瞬时响度(M)", "最大真峰值(TP)", "响度范围(LRA)"]'''
new = '''metrics = [self.tr("节目响度(I)"), self.tr("最大短时响度(S)"), self.tr("最大瞬时响度(M)"), self.tr("最大真峰值(TP)"), self.tr("响度范围(LRA)")]'''
text = text.replace(old, new, 1)

# ---------- 2. 左侧多单声道表格列名 ----------
# line 1078
old = "self.mono_files_table.setHorizontalHeaderLabels(['#', '声道', '文件名'])"
new = "self.mono_files_table.setHorizontalHeaderLabels([self.tr('#'), self.tr('声道'), self.tr('文件名')])"
text = text.replace(old, new, 1)

# ---------- 3. 声道配置 combobox ----------
# line 870
old = 'self.config_combo.addItems(["自动检测", "stereo", "5.1", "7.1", "5.1.4", "7.1.2", "7.1.4"])'
new = 'self.config_combo.addItems([self.tr("自动检测"), "stereo", "5.1", "7.1", "5.1.4", "7.1.2", "7.1.4"])'
text = text.replace(old, new, 1)

# line 639 setCurrentText
old = 'self.config_combo.setCurrentText("自动检测")'
new = 'self.config_combo.setCurrentText(self.tr("自动检测"))'
text = text.replace(old, new, 1)

# ---------- 4. 多单声道模板 combobox ----------
# line 995-998
old = '''self.mono_template_combo.addItems([
            "自动检测", "Stereo (2.0)", "5.1 (6ch)", "7.1 (8ch)",
            "7.1.2 (10ch)", "5.1.4 (10ch)", "7.1.4 (12ch)", "自定义"
        ])'''
new = '''self.mono_template_combo.addItems([
            self.tr("自动检测"), "Stereo (2.0)", "5.1 (6ch)", "7.1 (8ch)",
            "7.1.2 (10ch)", "5.1.4 (10ch)", "7.1.4 (12ch)", self.tr("自定义")
        ])'''
text = text.replace(old, new, 1)

# ---------- 5. 标准信息 "目标:" / "峰值:" ----------
# line 1593-1595
old = '''self.std_info.setText(
            f"目标: {std.integrated_target:+.1f} LKFS (±{std.integrated_tolerance:.1f} LU)\\n"
            f"峰值: {std.true_peak_limit:+.1f} dBTP"
        )'''
new = '''self.std_info.setText(
            self.tr("目标: {target} LKFS (±{tol} LU)\\n峰值: {peak} dBTP")
            .format(target=f"{std.integrated_target:+.1f}",
                    tol=f"{std.integrated_tolerance:.1f}",
                    peak=f"{std.true_peak_limit:+.1f}")
        )'''
text = text.replace(old, new, 1)

# ---------- 6. Excel 导出表头 ----------
# line 2272
old = "cell = ws.cell(row=row, column=1, value='每秒最大真峰值')"
new = "cell = ws.cell(row=row, column=1, value=self.tr('每秒最大真峰值'))"
text = text.replace(old, new, 1)

# line 2277
old = "tp_headers = ['时间(秒)', '真峰值(dBTP)', '标准限值', '状态']"
new = "tp_headers = [self.tr('时间(秒)'), self.tr('真峰值(dBTP)'), self.tr('标准限值'), self.tr('状态')]"
text = text.replace(old, new, 1)

# ---------- 7. 还有一些 results 区域未包裹的 ----------
# 搜索结果中 "节目响度: --" 和 "峰值: --" 已经被 tr() 包裹了，但中间面板的标准信息里还有中文
# "GY/T 282-2014 (中国广电-电视)" 这是标准名称，保持原样不翻译

src.write_text(text, encoding="utf-8")
print("Done.")
