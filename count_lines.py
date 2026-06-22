import os

def extract_source_for_registration(src_path, output_file, lines_per_page=50, total_pages=60):
    """提取前30页+后30页源代码用于登记"""
    
    all_lines = []
    
    # 收集所有 .py 文件
    for root, dirs, files in os.walk(src_path):
        dirs[:] = [d for d in dirs if d not in ['__pycache__', 'venv', '.git', 'build', 'dist']]
        for f in sorted(files):
            if f.endswith('.py'):
                filepath = os.path.join(root, f)
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
                    lines = file.readlines()
                    all_lines.extend(lines)
    
    total_lines = len(all_lines)
    lines_needed = lines_per_page * (total_pages // 2)  # 30页
    
    if total_lines <= lines_per_page * total_pages:
        # 不足60页，全部提交
        selected_lines = all_lines
    else:
        # 前30页 + 后30页
        head_lines = all_lines[:lines_needed]
        tail_lines = all_lines[-lines_needed:]
        selected_lines = head_lines + ['\n... [中间部分省略] ...\n\n'] + tail_lines
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f'软件名称: LouDuck\n')
        f.write(f'总代码行数: {total_lines}\n')
        f.write(f'提交行数: {len(selected_lines)}\n')
        f.write(f'{"="*80}\n\n')
        f.writelines(selected_lines)
    
    print(f"总代码行数: {total_lines}")
    print(f"已提取到: {output_file}")

# 使用
extract_source_for_registration(
    "D:\\My Documents\\家庭\\我的开发\\ImmersiveLoudness\\src",
    "D:\\My Documents\\家庭\\我的开发\\ImmersiveLoudness\\source_for_registration.txt"
)
