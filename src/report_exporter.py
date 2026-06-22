"""检测报告导出器 (整合修复版)"""

import json
import csv
from datetime import datetime
from dataclasses import dataclass
from typing import List
from pathlib import Path
from PySide6.QtCore import QCoreApplication


@dataclass
class LoudnessResults:
    """测量结果数据结构"""
    integrated: float
    short_term: float
    momentary: float
    true_peak: float
    lra: float
    max_true_peak: float
    duration: float
    filename: str
    sample_rate: int
    channels: int
    blocks: List[float]
    measurement_time: str = ""
    # 文件信息
    file_path: str = ""
    file_name: str = ""
    adm_info: str = ""
    renderer_info: str = ""
    authoring_info: str = ""
    ref_layout: str = ""
    mono_files: list = None
    
    def __post_init__(self):
        if not self.measurement_time:
            self.measurement_time = datetime.now().isoformat()
        if self.mono_files is None:
            self.mono_files = []


class ReportExporter:
    """报告导出器"""
    
    def __init__(self, results: LoudnessResults):
        self.results = results
    
    def export_txt(self, path: str) -> str:
        """导出 TXT"""
        lines = [
            "=" * 60,
            QCoreApplication.translate("ReportExporter", "      ITU-R BS.1770-5 Loudness Measurement Report"),
            "=" * 60,
            "",
            QCoreApplication.translate("ReportExporter", "测量时间: {time}").format(time=self.results.measurement_time),
            QCoreApplication.translate("ReportExporter", "文件路径: {path}").format(path=self.results.file_path or "-"),
            QCoreApplication.translate("ReportExporter", "文件名称: {name}").format(name=self.results.file_name or self.results.filename),
            QCoreApplication.translate("ReportExporter", "时长:     {duration}").format(duration=self._format_duration(self.results.duration)),
            QCoreApplication.translate("ReportExporter", "采样率:   {sr} Hz").format(sr=self.results.sample_rate),
            QCoreApplication.translate("ReportExporter", "声道数:   {ch}").format(ch=self.results.channels),
        ]
        
        # ADM / 渲染器信息
        if self.results.adm_info:
            lines.extend([
                "",
                "-" * 60,
                QCoreApplication.translate("ReportExporter", "ADM 信息:"),
                "-" * 60,
                self.results.adm_info,
            ])
        if self.results.renderer_info:
            lines.append(QCoreApplication.translate("ReportExporter", "渲染器:   {info}").format(info=self.results.renderer_info))
        if self.results.authoring_info:
            lines.append(QCoreApplication.translate("ReportExporter", "创作软件: {info}").format(info=self.results.authoring_info))
        if self.results.ref_layout:
            lines.append(QCoreApplication.translate("ReportExporter", "参考布局: {layout}").format(layout=self.results.ref_layout))
        
        # 多单声道文件列表
        if self.results.mono_files:
            lines.extend([
                "",
                "-" * 60,
                QCoreApplication.translate("ReportExporter", "多单声道文件列表:"),
                "-" * 60,
            ])
            for item in self.results.mono_files:
                lines.append(f"  [{item.get('channel', '?')}] {item.get('name', '')}")
        
        lines.extend([
            "",
            "-" * 60,
            QCoreApplication.translate("ReportExporter", "测量结果:"),
            "-" * 60,
            QCoreApplication.translate("ReportExporter", "  节目响度:      {val:+.2f} LKFS").format(val=self.results.integrated),
            QCoreApplication.translate("ReportExporter", "  最大短时响度:  {val:+.2f} LKFS").format(val=self.results.short_term),
            QCoreApplication.translate("ReportExporter", "  最大瞬时响度:  {val:+.2f} LKFS").format(val=self.results.momentary),
            QCoreApplication.translate("ReportExporter", "  最大真峰值:    {val:+.2f} dBTP").format(val=self.results.true_peak),
            QCoreApplication.translate("ReportExporter", "  响度范围:      {val:.2f} LU").format(val=self.results.lra),
            "",
            QCoreApplication.translate("ReportExporter", "合规性:"),
            QCoreApplication.translate("ReportExporter", "  EBU R128:  {status}").format(status=(QCoreApplication.translate("ReportExporter", "通过") if abs(self.results.integrated - (-23)) <= 1.0 else QCoreApplication.translate("ReportExporter", "未通过"))),
            QCoreApplication.translate("ReportExporter", "  真峰值:    {status}").format(status=(QCoreApplication.translate("ReportExporter", "通过") if self.results.true_peak <= -1.0 else QCoreApplication.translate("ReportExporter", "超标"))),
            "=" * 60,
        ])
        
        content = "\n".join(lines)
        Path(path).write_text(content, encoding='utf-8')
        return content
    
    def export_json(self, path: str) -> str:
        """导出 JSON"""
        data = {
            "metadata": {
                "version": "1.0",
                "standard": "ITU-R BS.1770-5",
                "measurement_time": self.results.measurement_time
            },
            "file_info": {
                "file_path": self.results.file_path,
                "file_name": self.results.file_name or self.results.filename,
                "filename": self.results.filename,
                "duration": self.results.duration,
                "sample_rate": self.results.sample_rate,
                "channels": self.results.channels,
                "adm_info": self.results.adm_info,
                "renderer_info": self.results.renderer_info,
                "authoring_info": self.results.authoring_info,
                "ref_layout": self.results.ref_layout,
                "mono_files": self.results.mono_files
            },
            "measurements": {
                "integrated_lufs": round(self.results.integrated, 4),
                "short_term_lufs": round(self.results.short_term, 4),
                "momentary_lufs": round(self.results.momentary, 4),
                "true_peak_dbtp": round(self.results.true_peak, 4),
                "loudness_range_lu": round(self.results.lra, 4)
            },
            "compliance": {
                "ebu_r128": bool(abs(self.results.integrated - (-23)) <= 1.0),
                "true_peak_limit": bool(self.results.true_peak <= -1.0)
            }
        }
        
        content = json.dumps(data, ensure_ascii=False, indent=2)
        Path(path).write_text(content, encoding='utf-8')
        return content
    
    def export_csv(self, path: str) -> str:
        """导出 CSV"""
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 文件信息
            writer.writerow(["File Path", self.results.file_path])
            writer.writerow(["File Name", self.results.file_name or self.results.filename])
            if self.results.adm_info:
                writer.writerow(["ADM Info", self.results.adm_info.replace('\n', ' ')])
            if self.results.renderer_info:
                writer.writerow(["Renderer", self.results.renderer_info])
            if self.results.authoring_info:
                writer.writerow(["Authoring", self.results.authoring_info])
            if self.results.ref_layout:
                writer.writerow(["Ref Layout", self.results.ref_layout])
            if self.results.mono_files:
                for item in self.results.mono_files:
                    writer.writerow([f"Channel {item.get('channel', '?')}", item.get('path', '')])
            writer.writerow([])
            
            writer.writerow(["Metric", "Value", "Unit", "Target", "Status"])
            
            rows = [
                [QCoreApplication.translate("ReportExporter", "节目响度"), f"{self.results.integrated:.4f}", "LKFS", "-23.0", 
                 "Pass" if abs(self.results.integrated - (-23)) <= 1.0 else "Fail"],
                [QCoreApplication.translate("ReportExporter", "最大短时响度"), f"{self.results.short_term:.4f}", "LKFS", "-23.0", "-"],
                [QCoreApplication.translate("ReportExporter", "最大瞬时响度"), f"{self.results.momentary:.4f}", "LKFS", "-", "-"],
                [QCoreApplication.translate("ReportExporter", "最大真峰值"), f"{self.results.true_peak:.4f}", "dBTP", "-1.0",
                 "Pass" if self.results.true_peak <= -1.0 else "Fail"],
                [QCoreApplication.translate("ReportExporter", "响度范围"), f"{self.results.lra:.4f}", "LU", "-", "-"],
            ]
            writer.writerows(rows)
        
        return path
    
    def _format_duration(self, seconds: float) -> str:
        """格式化时长"""
        m = int(seconds // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{m:02d}:{s:02d}.{ms:03d}"
