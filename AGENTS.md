# ImmersiveLoudness 项目指南

> 本文件面向 AI 编码助手。阅读者被假设对项目一无所知。

## 项目概述

**ImmersiveLoudness**（沉浸式音频文件响度测量工具，简称 IAFLM）是一个基于 ITU-R BS.1770-5 标准的响度测量桌面应用程序，当前版本 v3.1。

核心功能：
- 支持标准多声道音频文件（WAV/FLAC/MP3/OGG）的响度测量
- 支持 ADM/BW64 沉浸式音频文件解析与测量
- 支持多单声道文件（Multi-Mono）智能声道匹配与测量
- 支持多种声道配置：Stereo、5.1、7.1、5.1.4、7.1.2、7.1.4
- 实时响度测量（节目响度、最大短时响度、最大瞬时响度、真峰值、LRA）
- 多标准合规性检查（GY/T 282-2014、GY/T 377-2023、EBU R128、ATSC A/85）
- 导出 TXT / JSON / CSV / Excel 详细报告

## 技术栈

- **Python 版本**: 3.14（使用 venv 虚拟环境）
- **GUI 框架**: PySide6（Qt Widgets，Fusion 风格，深色主题）
- **科学计算**: NumPy、SciPy（signal 模块用于 K-加权滤波和真峰值 4x 过采样）
- **音频 I/O**: soundfile（基于libsndfile，支持 WAV/BW64 等格式）
- **Excel 导出**: openpyxl
- **打包工具**: PyInstaller（生成 Windows 单文件 EXE）

## 项目结构

```
ImmersiveLoudness/
├── src/                          # 核心源代码（所有业务逻辑在此）
│   ├── main_gui.py               # GUI 主程序（QMainWindow + QThread 工作线程）
│   ├── itu1770_meter.py          # ITU-R BS.1770-5 响度测量核心算法
│   ├── adm_parser.py             # ADM/BW64 解析器（ITU-R BS.2076 / BS.2088）
│   └── report_exporter.py        # 报告导出器（TXT / JSON / CSV）
├── assets/
│   └── icon.ico                  # 应用程序图标
├── pyinstaller_hooks/
│   └── hook-immersive_loudness.py # PyInstaller 隐藏导入配置
├── build/
│   └── ImmersiveLoudness.spec    # PyInstaller spec 文件（已生成）
├── dist/
│   └── ImmersiveLoudness.exe     # 构建产物（Windows 可执行文件）
├── backups/                      # 自动备份存放目录（zip 格式）
├── exports/                      # 报告导出默认目录（运行时创建）
├── venv/                         # Python 虚拟环境
├── backup.py                     # 备份脚本：打包 src/ 到 backups/
├── build_20260420.py             # 构建脚本：自动安装依赖 + PyInstaller 打包
├── install.bat                   # Windows 安装脚本（创建桌面/开始菜单快捷方式）
├── 备份.bat                       # 调用 backup.py 的便捷批处理
└── 用备份恢复.bat                  # 从 backups/ 恢复 src/ 的批处理
```

**注意**：本项目没有 `pyproject.toml`、`setup.py`、`requirements.txt` 或 `package.json`。依赖通过 `build_20260420.py` 脚本自动检查并 pip 安装。

## 模块职责

### `src/main_gui.py`（2109 行）
- 程序入口点（`if __name__ == "__main__": main()`）
- `LoudnessMeterApp`：主窗口，三栏布局（左：输入/配置，中：标准与进度，右：结果与导出）
- `DetailedMeasurementWorker`（QThread）：后台测量线程，避免 GUI 卡顿
- `SmartMultiMonoDialog`（QDialog）：多单声道文件智能声道匹配对话框
  - 支持点号分隔声道标识（如 `2005.L.wav`）
  - 支持 iXML 元数据读取
  - 支持正则匹配自动分配声道
- `_export_excel_detailed`：使用 openpyxl 生成带条件格式的 Excel 报告

### `src/itu1770_meter.py`（318 行）
- `ITU1770Meter`：响度测量引擎
- 实现 K-加权两段滤波（Stage1/Stage2 系数，48kHz 标准）
- 真峰值测量（48 阶 FIR 4x 过采样）
- 双门控集成响度（绝对门限 -70 LUFS，相对门限 -10 LU）
- 短时响度（3 秒滑动窗口）、瞬时响度（400ms）、LRA（10%-95% 百分位）
- 支持声道权重（ITU-R BS.1770-5 Table 4，侧/后环绕 +1.5dB）

### `src/adm_parser.py`（875 行）
- `BW64Parser`：BW64/RIFF 文件解析，提取 axml/chna/fmt/data chunk
- `ADM`：ADM XML 解析器（动态命名空间检测）
- 空间特征规则引擎：基于声道名称/方位角/仰角自动识别配置（stereo/5.1/7.1/5.1.4/7.1.4/7.1.2）
- 渲染器与创作软件信息提取（ITU-R BS.2076-3 §5.8.6）
- 支持 speakerLabel 到角度的映射（ITU 标签如 M+030、U+045 等）

### `src/report_exporter.py`（125 行）
- `LoudnessResults`：测量结果数据类
- `ReportExporter`：导出 TXT（中文报告）、JSON（结构化）、CSV（表格）

## 构建与运行

### 开发环境运行

```powershell
# 1. 激活虚拟环境（Windows）
venv\Scripts\Activate.ps1

# 2. 确保依赖已安装（若未安装，手动安装以下包）
pip install PySide6 numpy scipy soundfile openpyxl

# 3. 运行
cd src
python main_gui.py
```

### 打包为 EXE

```powershell
# 方法1：使用自动构建脚本
python build_20260420.py

# 方法2：直接使用已有的 spec 文件
pyinstaller build\ImmersiveLoudness.spec --distpath dist --workpath build --noconfirm
```

构建产物位于 `dist/ImmersiveLoudness.exe`。

**注意**：`build_20260420.py` 会自动处理以下 PyInstaller 常见问题：
- 包含 `unittest` 和 `unittest.mock`（SciPy/NumPy 内部依赖）
- 包含 `scipy.special._cdflib`、`scipy._lib.messagestream`
- 包含 `numpy.core._dtype_ctypes`、`numpy.core._multiarray_tests`
- 排除不必要的模块以减小体积（matplotlib、pandas、tkinter、pytest 等）

### 安装到系统

将 `install.bat` 与 `dist/ImmersiveLoudness.exe` 放在同一目录，以管理员身份运行 `install.bat`：
- 复制 EXE 到 `%ProgramFiles%\ImmersiveLoudness`
- 创建桌面快捷方式
- 创建开始菜单快捷方式

## 代码风格与约定

- **语言**：项目注释、UI 文本、文档均使用中文。变量名使用英文（snake_case）。
- **代码组织**：
  - 使用 `dataclass` 定义配置和数据结构
  - 类型注解广泛使用（`typing` 模块）
  - GUI 使用 Qt Signal/Slot 模式进行线程间通信
- **字符串/文档**：模块顶部有大段中文 docstring 说明功能、已知问题和修复记录
- **打印调试**：广泛使用 `print()` 输出中文调试信息（如 `[ADM解析]`、`[Excel导出]`）
- **异常处理**：工作线程中必须捕获异常并通过 `Signal` 传回主线程显示，避免程序崩溃

## 测试策略

**当前状态：无正式测试套件。** `tests/` 目录存在但为空。

验证修改的主要方式：
1. **手动 GUI 测试**：运行程序，分别测试三种输入模式（标准文件、ADM 文件、多单声道文件）
2. **算法验证**：使用已知响度的测试音频验证测量结果（ITU 提供参考测试序列）
3. **Excel 导出验证**：检查条件格式、超标红色标注、中文显示是否正常
4. **ADM 解析验证**：使用不同来源的 ADM/BW64 文件测试解析兼容性

若添加自动化测试，建议：
- 使用 `pytest` + `pytest-qt` 测试 GUI 组件
- 使用标准测试音频（如 EBU Tech 3341/3342 提供的参考文件）验证算法精度
- 测试 ADM 解析时使用包含不同命名空间和渲染器信息的样本文件

## 开发惯例

### 备份机制
修改前建议运行备份：
```powershell
python backup.py "修改描述"
# 或双击 备份.bat
```
会自动在 `backups/` 下生成 `src-YYYYMMDD-HHMMSS-修改描述.zip`，并自动清理保留最近 10 个备份。

恢复时使用 `用备份恢复.bat`，按提示输入备份文件名（不含 `.zip`）。

### 修改注意事项
1. **线程安全**：所有耗时操作（音频加载、响度计算）必须在 `QThread` 中进行，禁止在 GUI 线程执行重型 NumPy/SciPy 运算
2. **进度报告**：长任务应通过 `sub_step.emit(描述, 百分比)` 向 GUI 报告进度
3. **openpyxl 延迟导入**：Excel 导出功能使用 `try/except ImportError` 延迟导入 openpyxl，确保未安装时程序仍能运行（仅该功能不可用）
4. **soundfile 兼容性**：大文件（>50MB）使用分块流式读取，避免内存溢出
5. **ADM 命名空间**：ADM XML 可能使用不同命名空间，解析代码使用动态检测，修改时勿硬编码命名空间 URI

## 安全与部署考虑

- **目标平台**：Windows（当前 spec 文件和 install.bat 均为 Windows 设计）
- **路径处理**：使用 `pathlib.Path` 处理跨平台路径，但某些绝对路径（如 spec 文件中的 `D:/My Documents/...`）是当前开发环境的硬编码路径，构建前可能需要更新
- **权限**：install.bat 需要管理员权限才能写入 `%ProgramFiles%` 和创建开始菜单快捷方式
- **数据安全**：程序仅在本地处理音频文件，不联网，无用户数据采集
