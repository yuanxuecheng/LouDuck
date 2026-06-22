#!/usr/bin/env python3
"""Add QCoreApplication.translate() to report_exporter.py Chinese strings."""

from pathlib import Path

src = Path(__file__).parent.parent / "src" / "report_exporter.py"
text = src.read_text(encoding="utf-8")

# Add import
if "from PySide6.QtCore import QCoreApplication" not in text:
    text = text.replace(
        "from pathlib import Path",
        "from pathlib import Path\nfrom PySide6.QtCore import QCoreApplication"
    )

# Helper for shorter calls
TR = lambda s: f'QCoreApplication.translate("ReportExporter", "{s}")'

# TXT report labels
replaces = [
    ('"      ITU-R BS.1770-5 响度测量报告"', TR("      ITU-R BS.1770-5 Loudness Measurement Report")),
    ('f"测量时间: {self.results.measurement_time}"', 'QCoreApplication.translate("ReportExporter", "测量时间: {time}").format(time=self.results.measurement_time)'),
    ('f"文件路径: {self.results.file_path or \'-\'}"', 'QCoreApplication.translate("ReportExporter", "文件路径: {path}").format(path=self.results.file_path or "-")'),
    ('f"文件名称: {self.results.file_name or self.results.filename}"', 'QCoreApplication.translate("ReportExporter", "文件名称: {name}").format(name=self.results.file_name or self.results.filename)'),
    ('f"时长:     {self._format_duration(self.results.duration)}"', 'QCoreApplication.translate("ReportExporter", "时长:     {duration}").format(duration=self._format_duration(self.results.duration))'),
    ('f"采样率:   {self.results.sample_rate} Hz"', 'QCoreApplication.translate("ReportExporter", "采样率:   {sr} Hz").format(sr=self.results.sample_rate)'),
    ('f"声道数:   {self.results.channels}"', 'QCoreApplication.translate("ReportExporter", "声道数:   {ch}").format(ch=self.results.channels)'),
    ('"ADM 信息:"', TR("ADM 信息:")),
    ('f"渲染器:   {self.results.renderer_info}"', 'QCoreApplication.translate("ReportExporter", "渲染器:   {info}").format(info=self.results.renderer_info)'),
    ('f"创作软件: {self.results.authoring_info}"', 'QCoreApplication.translate("ReportExporter", "创作软件: {info}").format(info=self.results.authoring_info)'),
    ('f"参考布局: {self.results.ref_layout}"', 'QCoreApplication.translate("ReportExporter", "参考布局: {layout}").format(layout=self.results.ref_layout)'),
    ('"多单声道文件列表:"', TR("多单声道文件列表:")),
    ('"测量结果:"', TR("测量结果:")),
    ('f"  节目响度:      {self.results.integrated:+.2f} LKFS"', 'QCoreApplication.translate("ReportExporter", "  节目响度:      {val:+.2f} LKFS").format(val=self.results.integrated)'),
    ('f"  最大短时响度:  {self.results.short_term:+.2f} LKFS"', 'QCoreApplication.translate("ReportExporter", "  最大短时响度:  {val:+.2f} LKFS").format(val=self.results.short_term)'),
    ('f"  最大瞬时响度:  {self.results.momentary:+.2f} LKFS"', 'QCoreApplication.translate("ReportExporter", "  最大瞬时响度:  {val:+.2f} LKFS").format(val=self.results.momentary)'),
    ('f"  最大真峰值:    {self.results.true_peak:+.2f} dBTP"', 'QCoreApplication.translate("ReportExporter", "  最大真峰值:    {val:+.2f} dBTP").format(val=self.results.true_peak)'),
    ('f"  响度范围:      {self.results.lra:.2f} LU"', 'QCoreApplication.translate("ReportExporter", "  响度范围:      {val:.2f} LU").format(val=self.results.lra)'),
    ('"合规性:"', TR("合规性:")),
    ("f\"  EBU R128:  {'通过' if abs(self.results.integrated - (-23)) <= 1.0 else '未通过'}\"",
     'QCoreApplication.translate("ReportExporter", "  EBU R128:  {status}").format(status=(QCoreApplication.translate("ReportExporter", "通过") if abs(self.results.integrated - (-23)) <= 1.0 else QCoreApplication.translate("ReportExporter", "未通过")))'),
    ("f\"  真峰值:    {'通过' if self.results.true_peak <= -1.0 else '超标'}\"",
     'QCoreApplication.translate("ReportExporter", "  真峰值:    {status}").format(status=(QCoreApplication.translate("ReportExporter", "通过") if self.results.true_peak <= -1.0 else QCoreApplication.translate("ReportExporter", "超标")))'),
    # CSV rows
    ('["节目响度", f"{self.results.integrated:.4f}", "LKFS", "-23.0",', '[QCoreApplication.translate("ReportExporter", "节目响度"), f"{self.results.integrated:.4f}", "LKFS", "-23.0",'),
    ('["最大短时响度", f"{self.results.short_term:.4f}", "LKFS", "-23.0", "-"],', '[QCoreApplication.translate("ReportExporter", "最大短时响度"), f"{self.results.short_term:.4f}", "LKFS", "-23.0", "-"],'),
    ('["最大瞬时响度", f"{self.results.momentary:.4f}", "LKFS", "-", "-"],', '[QCoreApplication.translate("ReportExporter", "最大瞬时响度"), f"{self.results.momentary:.4f}", "LKFS", "-", "-"],'),
    ('["最大真峰值", f"{self.results.true_peak:.4f}", "dBTP", "-1.0",', '[QCoreApplication.translate("ReportExporter", "最大真峰值"), f"{self.results.true_peak:.4f}", "dBTP", "-1.0",'),
    ('["响度范围", f"{self.results.lra:.4f}", "LU", "-", "-"],', '[QCoreApplication.translate("ReportExporter", "响度范围"), f"{self.results.lra:.4f}", "LU", "-", "-"],'),
]

for old, new in replaces:
    if old in text:
        text = text.replace(old, new, 1)
    else:
        print(f"WARN: not found: {old[:70]}...")

src.write_text(text, encoding="utf-8")
print("Done.")
