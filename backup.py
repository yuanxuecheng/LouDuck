#!/usr/bin/env python3
"""
LouDuck 简易备份脚本
用法: python backup.py [备注]
效果: 在 backups/ 目录下生成 src-YYYYMMDD-HHMMSS-备注.zip
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime


def backup():
    project_dir = Path(__file__).parent.resolve()
    src_dir = project_dir / 'src'
    backup_dir = project_dir / 'backups'
    
    if not src_dir.exists():
        print(f"[ERROR] 未找到 {src_dir}")
        return 1
    
    backup_dir.mkdir(exist_ok=True)
    
    # 生成文件名
    now = datetime.now().strftime('%Y%m%d-%H%M%S')
    note = sys.argv[1] if len(sys.argv) > 1 else 'manual'
    # 清理备注中的非法字符
    note = ''.join(c if c.isalnum() or c in '-_' else '_' for c in note)[:20]
    zip_name = f"src-{now}-{note}"
    zip_path = backup_dir / zip_name
    
    # 打包
    archive = shutil.make_archive(str(zip_path), 'zip', str(src_dir))
    print(f"[OK] 已备份: {Path(archive).name}")
    print(f"     路径: {backup_dir}")
    
    # 自动清理：只保留最近 10 个备份
    all_backups = sorted(backup_dir.glob('src-*.zip'), key=lambda p: p.stat().st_mtime)
    if len(all_backups) > 10:
        for old in all_backups[:-10]:
            old.unlink()
            print(f"     清理旧备份: {old.name}")
    
    return 0


if __name__ == '__main__':
    sys.exit(backup())
