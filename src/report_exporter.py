"""检测报告导出器 (整合修复版)"""

import json
import csv
from datetime import datetime
from dataclasses import dataclass
from typing import List
from pathlib import Path


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
    
    def __post_init__(self):
        if not self.measurement_time:
            self.measurement_time = datetime.now().isoformat()


class ReportExporter:
    """报告导出器"""
    
    def __init__(self, results: LoudnessResults):
        self.results = results
    
    def export_txt(self, path: str) -> str:
        """导出 TXT"""
        lines = [
            "=" * 60,
            "      ITU-R BS.1770-5 响度测量报告",
            "=" * 60,
            "",
            f"测量时间: {self.results.measurement_time}",
            f"文件名:   {self.results.filename}",
            f"时长:     {self._format_duration(self.results.duration)}",
            f"采样率:   {self.results.sample_rate} Hz",
            f"声道数:   {self.results.channels}",
            "",
            "-" * 60,
            "测量结果:",
            "-" * 60,
            f"  节目响度:      {self.results.integrated:+.2f} LUFS",
            f"  最大短时响度:  {self.results.short_term:+.2f} LUFS",
            f"  最大瞬时响度:  {self.results.momentary:+.2f} LUFS",
            f"  最大真峰值:    {self.results.true_peak:+.2f} dBTP",
            f"  响度范围:      {self.results.lra:.2f} LU",
            "",
            "合规性:",
            f"  EBU R128:  {'通过' if abs(self.results.integrated - (-23)) <= 1.0 else '未通过'}",
            f"  真峰值:    {'通过' if self.results.true_peak <= -1.0 else '超标'}",
            "=" * 60,
        ]
        
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
                "filename": self.results.filename,
                "duration": self.results.duration,
                "sample_rate": self.results.sample_rate,
                "channels": self.results.channels
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
            writer.writerow(["Metric", "Value", "Unit", "Target", "Status"])
            
            rows = [
                ["节目响度", f"{self.results.integrated:.4f}", "LUFS", "-23.0", 
                 "Pass" if abs(self.results.integrated - (-23)) <= 1.0 else "Fail"],
                ["最大短时响度", f"{self.results.short_term:.4f}", "LUFS", "-23.0", "-"],
                ["最大瞬时响度", f"{self.results.momentary:.4f}", "LUFS", "-", "-"],
                ["最大真峰值", f"{self.results.true_peak:.4f}", "dBTP", "-1.0",
                 "Pass" if self.results.true_peak <= -1.0 else "Fail"],
                ["响度范围", f"{self.results.lra:.4f}", "LU", "-", "-"],
            ]
            writer.writerows(rows)
        
        return path
    
    def _format_duration(self, seconds: float) -> str:
        """格式化时长"""
        m = int(seconds // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{m:02d}:{s:02d}.{ms:03d}"
