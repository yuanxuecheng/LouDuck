# LouDuck 项目指南

> 本文件面向 AI 编码助手。阅读者被假设对项目一无所知。

## 项目概述

**LouDuck**（沉浸式音频文件响度测量工具，简称 IAFLM）是一个基于 ITU-R BS.1770-5 标准的响度测量桌面应用程序，当前版本 v3.2。

核心功能：
- 支持标准多声道音频文件（WAV/FLAC/MP3/OGG）的响度测量
- 支持 ADM/BW64/RF64 沉浸式音频文件解析与测量，内置大文件（>4 GB）流式读取
- 支持多单声道文件（Multi-Mono）智能声道匹配与测量
- 支持多种声道配置：Stereo、5.1、7.1、5.1.4、7.1.2、7.1.4
- 实时响度测量（节目响度、最大短时响度、最大瞬时响度、真峰值、LRA）
- 多标准合规性检查（GY/T 282-2014、GY/T 377-2023、EBU R128、ATSC A/85）
- 导出 TXT / JSON / CSV / Excel 详细报告
- 中文 / English 多语言界面（通过 Qt 翻译文件 `.ts` / `.qm`）

## 技术栈

- **Python 版本**: 3.14（开发环境 `venv/` 指向 Python 3.14.4）
- **GUI 框架**: PySide6（Qt Widgets，Fusion 风格，深色主题）
- **科学计算**: NumPy、SciPy（signal 模块用于 K-加权滤波和真峰值 4x 过采样）
- **音频 I/O**: soundfile（基于 libsndfile，支持 WAV/BW64/RF64 等格式）
- **ADM 渲染**: EBU ADM Renderer（`ear`，从 GitHub 直接安装）
- **Excel 导出**: openpyxl
- **打包工具**: PyInstaller（生成 Windows onedir 目录式发布包，以及 macOS `.app`/DMG）

**注意**：本项目没有 `pyproject.toml`、`setup.py`、`requirements.txt` 或 `package.json`。依赖通过 `build20260806.py` 自动检查并 pip 安装，CI 工作流中也会显式安装。

## 项目结构

```
LouDuck/
├── src/                          # 核心源代码（所有业务逻辑在此）
│   ├── main_gui.py               # GUI 主程序（QMainWindow + QThread 工作线程）
│   ├── itu1770_meter.py          # ITU-R BS.1770-5 响度测量核心算法
│   ├── adm_parser.py             # ADM/BW64/RF64 解析器（ITU-R BS.2076 / BS.2088）
│   ├── report_exporter.py        # 报告导出器（TXT / JSON / CSV）
│   ├── mono_channel_matcher.py   # 多单声道文件智能声道匹配对话框与算法
│   ├── renderers/                # 音频渲染器封装
│   │   ├── __init__.py
│   │   └── ear_renderer.py       # EBU ADM Renderer（EAR）包装层
│   ├── diagnose_adm.py           # ADM/BW64/RF64 大文件诊断脚本
│   └── lra_debug.py              # LRA 计算中间值诊断脚本
├── tests/                        # 单元/集成测试脚本（可直接 python 运行）
│   ├── test_adm_channel_fix.py
│   ├── test_inv_patch.py
│   ├── test_mono_config_sync.py
│   ├── test_mono_matcher.py
│   ├── test_real_adm.py
│   ├── test_streaming_integration.py
│   └── test_streaming_memory.py
├── assets/                       # 图标、背景图等资源
│   ├── icon.ico
│   └── icon.icns
├── i18n/                         # 多语言翻译文件与辅助脚本
│   ├── LouDuck_en.ts / LouDuck_en.qm
│   ├── ImmersiveLoudness_en.ts / ImmersiveLoudness_en.qm
│   └── apply_translations.py 等
├── pyinstaller_hooks/
│   └── hook-immersive_loudness.py # PyInstaller 隐藏导入配置
├── build/
│   └── LouDuck.spec              # PyInstaller spec 文件（由 build20260806.py 自动生成）
├── dist/
│   └── LouDuck/                  # onedir 构建产物目录
├── backups/                      # 自动备份存放目录（zip 格式）
├── exports/                      # 报告导出默认目录（运行时创建）
├── venv/                         # Python 虚拟环境
├── .github/workflows/            # GitHub Actions CI/CD
│   └── build-mac&pc.yml         # macOS Apple Silicon + Windows 构建并发布 Release
├── backup.py                     # 备份脚本：打包 src/ 到 backups/
├── build20260806.py            # 当前主推构建脚本（onedir、optimize=1、自动打包 zip）
├── build_20260427.py           # 旧版 onefile 构建脚本（已不推荐使用）
├── build_20260507.py           # 旧版 onefile 构建脚本（已不推荐使用）
├── build_20260511.py           # 旧版 onefile 构建脚本（已不推荐使用）
├── build_20260614_onedir.py    # 旧版 onedir 构建脚本
├── build_simple.py             # 简化 onefile 构建脚本
├── install.bat                 # Windows 安装脚本（创建桌面/开始菜单快捷方式）
├── 备份.bat                     # 调用 backup.py 的便捷批处理
└── 用备份恢复.bat               # 从 backups/ 恢复 src/ 的批处理
```

## 模块职责

### `src/main_gui.py`
- 程序入口点（`if __name__ == "__main__": main()`）
- `LoudnessMeterApp`：主窗口，三栏布局（左：输入/配置，中：标准与进度，右：结果与导出）
- `DetailedMeasurementWorker`（QThread）：后台测量线程，避免 GUI 卡顿
  - 三种输入模式（标准文件 / ADM / 多单声道）均使用流式读取，避免一次性加载完整音频数组
  - 通过 `ITU1770Meter.feed()` 分块喂入音频，`finalize()` 获取结果
- `SmartMultiMonoDialog`（QDialog）：多单声道文件智能声道匹配对话框
  - 支持点号分隔声道标识（如 `2005.L.wav`）
  - 支持 iXML 元数据读取
  - 支持正则匹配自动分配声道
- `LoudnessCurveWidget`：自绘短时响度/时间曲线（QPainter）
- `ExportOptionsDialog`：导出选项对话框
- `_export_excel_detailed`：使用 openpyxl 生成带条件格式、超标红色标注的 Excel 报告

### `src/itu1770_meter.py`
- `ITU1770Meter`：响度测量引擎（真流式/状态机实现）
  - 公开流式接口：`reset()`、`feed(chunk)`、`finalize()`
  - 保留兼容接口：`process_audio(audio, ...)`，内部走流式核心
  - 内部维护 K-加权 IIR 状态、100ms 功率累积器、400ms 块响度序列、3s 短时响度环形缓冲区、真峰值 FIR 尾部历史
  - 内存占用与文件大小无关，仅取决于 chunk 大小与状态缓冲区
- 实现 K-加权两段滤波（Stage1/Stage2 系数，48kHz 标准）
- 真峰值测量（48 阶 FIR 4x 过采样，跨块保留 overlap 避免边界峰值丢失）
- 双门控集成响度（绝对门限 -70 LKFS，相对门限 -10 LU）
- 短时响度（3 秒滑动窗口）、瞬时响度（400ms）、LRA（10%-95% 百分位）
- 支持声道权重（ITU-R BS.1770-5 Table 4，侧/后环绕 +1.5dB）

### `src/adm_parser.py`
- `BW64Parser`：BW64/RIFF/RF64 文件解析，提取 axml/chna/fmt/data chunk
  - `iter_audio_blocks(block_samples, dtype)`：流式分块读取音频，供 `main_gui.py` 避免一次性全量加载
  - `read_audio()`：小文件兼容接口
  - 支持 RF64 大文件与 `ds64` chunk，正确处理 `0xFFFFFFFF` 占位
- `ADM`：ADM XML 解析器（动态命名空间检测）
- `is_adm_file`：快速判断文件是否包含 ADM 元数据
- 空间特征规则引擎：基于声道名称/方位角/仰角自动识别配置（stereo/5.1/7.1/5.1.4/7.1.4/7.1.2）
- 渲染器与创作软件信息提取（ITU-R BS.2076-3 §5.8.6）
- 支持 speakerLabel 到角度的映射（ITU 标签如 M+030、U+045 等）

### `src/renderers/ear_renderer.py`
- `EBU ADM Renderer` 的 Python 包装层
- 支持将 Dolby Atmos / Audio Vivid（ADM 格式）渲染到标准扬声器布局
- `_create_fixed_bw64`：修复 axml 中 audioStreamFormat 双重引用，并流式复制大文件
- `render_adm`、`get_supported_layouts`、`get_adm_info` 等对外接口

### `src/mono_channel_matcher.py`
- 多单声道 WAV 文件智能声道识别
- `CHANNEL_TEMPLATES`：Stereo / 5.1 / 7.1 / 5.1.4 / 7.1.2 / 7.1.4 模板与正则
- `auto_match_mono_files`：自动根据文件名/iXML 匹配声道
- `_extract_channel_id`：支持点号分隔、长描述性名称等

### `src/report_exporter.py`
- `LoudnessResults`：测量结果数据类
- `ReportExporter`：导出 TXT（中文报告）、JSON（结构化）、CSV（表格）
- Excel 导出逻辑位于 `main_gui.py` 的 `_export_excel_detailed`

### `src/diagnose_adm.py`
- 命令行诊断脚本：打印文件头、`soundfile` 信息、`is_adm_file` 结果、`BW64Parser.parse` 结果
- 用法：`python src/diagnose_adm.py "/path/to/large_adm.wav"`

### `src/lra_debug.py`
- LRA 计算中间值诊断脚本，可与 FFmpeg/libebur128 结果对比
- 用法：`python src/lra_debug.py "/path/to/audio.wav"`

## 构建与运行

### 开发环境运行

```powershell
# 1. 激活虚拟环境（Windows）
venv\Scripts\Activate.ps1

# 2. 确保依赖已安装（若未安装，手动安装以下包）
pip install PySide6 numpy scipy soundfile openpyxl
pip install git+https://github.com/ebu/ebu_adm_renderer.git

# 3. 运行
cd src
python main_gui.py
```

### 打包为 EXE

**推荐方式（当前主推脚本，onedir 目录式发布）：**

```powershell
python build20260806.py
```

该脚本会：
1. 检查并安装依赖（包括 Pillow）
2. 清理 `__pycache__` 与旧的 `build/`、`dist/`
3. 生成 onedir 模式的 `build/LouDuck.spec`
4. 使用 PyInstaller 构建 `dist/LouDuck/` 目录
5. 生成 `install.bat`
6. 自动打包为 `dist/LouDuck_Win_v3.2_YYYYMMDD.zip`

**旧方式（单文件 EXE，已不推荐使用）：**

```powershell
python build_20260427.py
# 产物：dist/ImmersiveLoudness.exe
```

**直接使用已有的 spec 文件：**

```powershell
pyinstaller build\LouDuck.spec --distpath dist --workpath build --noconfirm --clean
```

构建产物位于 `dist/LouDuck/`（onedir 目录式）或 `dist/ImmersiveLoudness.exe`（onefile 单文件）。

**注意**：`build/LouDuck.spec` 由 `build20260806.py` 自动生成，请勿手动修改。spec 中硬编码了当前开发环境的绝对路径（`D:/My Documents/...`），在其他机器上构建前请重新生成。

### CI/CD

`.github/workflows/build-mac&pc.yml` 定义了 GitHub Actions：
- 触发条件：推送 `v*` 标签
- 任务 1：在 `macos-14` 上构建 Apple Silicon 版 `LouDuck.app`，签名后打包为 DMG，并创建 Release
- 任务 2：在 `windows-latest` 上构建 Windows onedir 版，压缩为 zip，并创建 Release

CI 中显式安装的依赖：

```bash
pip install PySide6 numpy scipy soundfile openpyxl
pip install git+https://github.com/ebu/ebu_adm_renderer.git
pip install pyinstaller
```

### 安装到系统

将 `install.bat` 与 `dist/LouDuck/` 目录放在同一目录，以管理员身份运行 `install.bat`：
- 复制整个 `LouDuck/` 目录到 `%ProgramFiles%\LouDuck`
- 创建桌面快捷方式
- 创建开始菜单快捷方式

## 代码风格与约定

- **语言**：项目注释、UI 文本、文档均使用中文。变量名使用英文（snake_case）。
- **代码组织**：
  - 使用 `dataclass` 定义配置和数据结构
  - 类型注解广泛使用（`typing` 模块）
  - GUI 使用 Qt Signal/Slot 模式进行线程间通信
- **字符串/文档**：模块顶部有大段中文 docstring 说明功能、已知问题和修复记录
- **打印调试**：广泛使用 `print()` 输出中文调试信息（如 `[ADM解析]`、`[EAR修复]`、`[Excel导出]`）
- **异常处理**：工作线程中必须捕获异常并通过 `Signal` 传回主线程显示，避免程序崩溃

## 测试策略

`tests/` 目录包含可直接运行的测试脚本，**不是 pytest 风格的测试套件**，主要作为开发过程中的验证脚本。每个文件都可独立执行：

```powershell
# 从项目根目录运行
python tests/test_streaming_integration.py
python tests/test_mono_matcher.py
python tests/test_adm_channel_fix.py
python tests/test_real_adm.py
python tests/test_streaming_memory.py
```

测试文件说明：
- `test_streaming_integration.py`：对比旧版与新流式核心结果一致性，验证 `iter_audio_blocks` 与多单声道流式读取
- `test_mono_matcher.py`：验证 `_extract_channel_id` 与 `auto_match_mono_files` 的声道匹配逻辑
- `test_adm_channel_fix.py`：验证 ADM `to_itu1770_config` 补齐/截断行为，以及 `meter.feed` 通道数不匹配报错
- `test_real_adm.py`：用真实 ADM 文件验证直接测量路径不再越界
- `test_streaming_memory.py`：验证大文件流式处理时的内存占用（依赖 `test_big_10ch.wav`）
- `test_inv_patch.py`、`test_mono_config_sync.py`：历史回归测试

**建议添加正式测试时使用 `pytest` + `pytest-qt` 测试 GUI 组件**，并引入标准测试音频（如 EBU Tech 3341/3342 参考文件）验证算法精度。

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

1. **线程安全**：所有耗时操作（音频加载、响度计算、ADM 渲染）必须在 `QThread` 中进行，禁止在 GUI 线程执行重型 NumPy/SciPy 运算
2. **进度报告**：长任务应通过 `sub_step.emit(描述, 百分比)` 向 GUI 报告进度
3. **openpyxl 延迟导入**：Excel 导出功能使用 `try/except ImportError` 延迟导入 openpyxl，确保未安装时程序仍能运行（仅该功能不可用）
4. **真流式响度核心**：`itu1770_meter.py` 已改造为状态机。修改算法时注意：
   - K-加权滤波状态（`lfilter_zi` 或 0 初始）必须跨 chunk 保持连续
   - 真峰值 FIR 必须保留尾部历史并处理 chunk 边界 overlap
   - Momentary / Short-term / Integrated 的窗口统计基于 100ms / 400ms / 3s 累积器，不保存完整音频
   - LRA 使用的 1s 步进 Short-term 在 `finalize()` 中统一计算
5. **流式文件 I/O**：`main_gui.py`、`adm_parser.py` 和 `ear_renderer.py` 均避免一次性全量加载音频。标准文件通过 `soundfile.blocks()` 分块读取；ADM 通过 `BW64Parser.iter_audio_blocks()` 分块读取；EAR 渲染通过流式复制临时文件实现
6. **ADM 命名空间**：ADM XML 可能使用不同命名空间，解析代码使用动态检测，修改时勿硬编码命名空间 URI
7. **EAR 数据文件**：PyInstaller 打包时必须把 `ear/core/data` 和 `ear/fileio/adm/data` 作为数据目录一起打包，`build20260806.py` 会自动发现这些路径
8. **实时插件复用**：流式核心 `ITU1770Meter.feed()` 可直接用于未来实时插件/响度表。新增实时接口时应保持 `feed()` 的签名与语义不变
9. **大文件 ADM 处理**：修改 BW64/RF64 解析时，必须同时验证 `ds64` chunk、`0xFFFFFFFF` 占位符以及 data chunk 后的 axml 元数据位置

## 安全与部署考虑

- **目标平台**：Windows 为主力开发平台，macOS Apple Silicon 通过 CI 构建（README 也声称支持 macOS Intel，但当前工作流仅包含 Apple Silicon）
- **路径处理**：使用 `pathlib.Path` 处理跨平台路径，但 `build/LouDuck.spec` 中的绝对路径是当前开发环境的硬编码路径，构建前需要重新生成
- **权限**：`install.bat` 需要管理员权限才能写入 `%ProgramFiles%` 和创建开始菜单快捷方式
- **数据安全**：程序仅在本地处理音频文件，不联网，无用户数据采集
- **签名**：当前构建产物未进行 Apple / Microsoft 官方代码签名，分发时会触发安全提示；README 中已包含首次运行的绕过说明
