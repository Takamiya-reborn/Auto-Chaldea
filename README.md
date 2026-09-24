# Auto-Chaldea

Auto-Chaldea 是一个基于 ADB、OpenCV 和 PySide6 的 FGO 自动化辅助工具，核心思路是：

- 通过 ADB 连接 Android 设备/模拟器
- 截图并对当前画面进行模板识别
- 根据 YAML 任务步骤决定下一步动作
- 通过 ADB 执行点击、滑动和其它输入操作
- 在桌面端统一管理设备、任务、日志和执行状态

它适合用于处理重复性较强、规则明确的游戏操作，并尽量通过识别画面来驱动流程，减少对玩家的精神污染。

> 使用范围：本项目用于个人设备上的辅助研究与重复操作自动化。请遵守游戏服务条款、当地法律以及账号安全要求，不要用于绕过安全机制或影响其他玩家。

## 主要功能

### 1. ADB 设备连接与控制

- 连接本地 Android 设备或模拟器
- 自动探测可用的 ADB 设备
- 截取当前屏幕并保存图片
- 通过坐标点击、滑动等方式执行操作
- 监控设备状态与断开事件

### 2. 模板识别引擎

- 基于 OpenCV 的模板匹配识别 UI 元素
- 支持全屏识别和 ROI（感兴趣区域）识别
- 支持单模板识别和多模板识别
- 支持按置信度排序、索引点击和重复匹配处理
- 可配置识别区域、重试间隔和超时

### 3. YAML 任务系统

- 任务步骤以 YAML 配置，放在 `assets/task/`
- 每个步骤都可以定义模板、区域、等待、重试与超时
- 支持 `single` / `multi` 两种识别模式
- 允许通过 `Center` 直接点击屏幕中心，跳过模板识别
- 任务执行器会按顺序执行，直到目标出现、点击成功或任务失败

### 4. 桌面化执行界面

- 设备选择与连接控制
- 任务列表与任务详情查看
- 实时日志与状态反馈
- 执行任务前可设置重复执行次数（1 到 9999 次）
- 执行过程中显示当前执行次数与总次数
- 暂停、继续、停止等运行控制
- 任务执行过程中可查看当前识别结果和动作状态

### 5. 任务脚本与调试工具

- `scripts/` 目录下的脚本属于开发辅助工具，不参与正式项目构成
- 这些脚本用于在开发过程中抓取屏幕、生成/校验模板、调试识别逻辑
- 正式项目功能由 `src/auto_chaldea/` 和 `assets/` 负责，而不是脚本目录本身
- 开发者可在需要时手动运行脚本来补充 `assets/template/`，并据此迭代任务配置

## 目录结构

```text
.
├── main.py                  # 程序入口
├── pyproject.toml           # uv / Python 依赖配置
├── README.md                # 项目说明
├── src/
│   └── auto_chaldea/
│       ├── __init__.py
│       ├── core/
│       │   ├── task_executor.py
│       │   ├── task_loader.py
│       │   ├── task_schema.py
│       │   └── ...
│       ├── ui/
│       │   ├── main_window.py
│       │   ├── task_panel.py
│       │   ├── task_detail.py
│       │   └── ...
│       └── utils/
│           ├── adb_device.py
│           ├── paths.py
│           └── recognizer.py
├── assets/
│   ├── platform-tools/
│   ├── qss/
│   ├── task/
│   └── template/
├── scripts/
│   ├── scap.py              # 开发用截图脚本，生成模板或校验画面
│   └── ...                  # 其它开发辅助脚本
└── uv.lock
```

## 运行方式

本项目使用 Python 3.13 与 uv 管理依赖。

### 安装依赖

```powershell
uv sync
```

### 启动桌面应用

```powershell
uv run auto-chaldea
```

### 打包 Windows 程序

确保已安装依赖并配置好 Visual Studio C++ 编译环境后，执行：

```powershell
.\scripts\nuitka.ps1
```

### 开发期间的辅助脚本

```powershell
uv run scripts/scap.py [port]
```

功能是截图并放置在`assets/template/`
如果本机只有一个 ADB 设备，可省略端口；如果有多个设备，请显式指定端口来区分。

### 设置任务执行次数

在任务详情区域点击“执行”后，可在弹窗中输入执行次数，范围为 1 到 9999 次。这里的次数表示完整任务的重复次数，每次都会从第一个步骤重新开始执行。

运行期间，状态栏会显示当前执行次数与总次数，并可使用“暂停”、“继续”或“停止”控制任务。任务执行失败或设备断开时会提前终止后续执行。

## 任务 YAML 介绍

任务配置位于 `assets/task/`，一个最小示例如下：

```yaml
task_name: 示例任务
prerequisite: 需要准备指定从者和御主礼装
steps:
  - template: attack.png
  - template: Center
  - template: skill_1.png
    index: 1
    region: "0, 0, 1280, 720"
    step_interval: 1.0
    timeout: 30
  - template: buster,arts,quick
    mode: multi
    count: 2
```

### 字段说明

- `prerequisite`：任务执行前需要满足的条件，会显示在任务详情区域；支持普通文本和多行文本
- `template`：模板图片文件名，默认从 `assets/template/` 中查找；如果为 `Center`，则直接点击屏幕中心
- `mode`：识别模式，默认 `single`；`multi` 表示同时匹配多个模板, 例如：要在三色卡中任选几张、在不同狗粮中任选20张
- `count`：在 `multi` 模式下，按置信度排名取前 `count` 个结果依次点击
- `index`：同屏多个匹配时的点击顺序，默认取第一个匹配
- `region`：识别区域，可传 `x1, y1, x2, y2`，也支持 `左`、`右`、`上`、`下`、`左上` 等别名
- `step_interval`：点击成功后等待多久再进入下一步，默认约 `1.0` 秒
- `timeout`：单步识别超时，超过后任务失败并终止
- `retry_interval` 和 `max_retry_interval`：未匹配到目标时的重试间隔与上限

## 开发上手建议

### 1. 先理解主流程

这套项目的核心链路可以概括为：

`ADB 连接 / 屏幕截图 -> 模板识别 -> 任务步骤执行 -> 点击/滑动 -> 游戏状态变化`

主要代码入口：

- `main.py`：程序启动入口
- `src/auto_chaldea/__init__.py`：导出 `main` 与常用执行函数
- `src/auto_chaldea/core/task_loader.py`：加载任务
- `src/auto_chaldea/core/task_executor.py`：执行任务步骤
- `src/auto_chaldea/utils/adb_device.py`：ADB 设备连接、点击、滑动和尺寸读取
- `src/auto_chaldea/utils/recognizer.py`：识别逻辑
- `src/auto_chaldea/ui/`：桌面端界面

### 2. 添加一个新任务

1. 在 `assets/task/` 下新增 YAML 文件
2. 将对应模板图片放进 `assets/template/`
3. 确保模板名和 YAML 中的 `template` 字段一致
4. 启动程序后在任务列表中选择并执行

### 3. 调整识别逻辑

- 识别逻辑主要在 `src/auto_chaldea/utils/recognizer.py`
- 区域逻辑与模板常量在 `task_schema.py` 等模块中处理
- 若需要修改点击方式、截图流程或设备操作，直接查看 `src/auto_chaldea/utils/adb_device.py`

### 4. 修改界面

- 主窗口入口：`src/auto_chaldea/ui/main_window.py`
- 任务列表面板：`task_panel.py`
- 任务详情/执行控制：`task_detail.py`
- 设备状态监控：`device_monitor.py`

### 5. 调试建议

- 先用 `scripts/scap.py` 抓取一张目标画面，作为模板或识别样本
- 把截图保存到 `assets/template/`，并按任务命名/归类，确保后续 YAML 中引用正确
- 先用小范围 `region` 测试识别，再扩大到完整任务
- 对于高风险或流程变化较大的一步，先单步调试，避免直接全流程执行
- `scripts/` 中的内容用于开发者在调试时临时使用，不应被当成正式运行入口或核心应用功能

## 说明

这个仓库更像一个“可扩展的自动化脚本框架 + 桌面执行器”，而不是一个标准的业务型 Python 项目。开发时更重要的是：

- 任务配置是否准确
- 模板识别是否稳定
- ADB 操作是否可靠
- 程序在设备状态异常时是否能安全停止

如果你是想在这个仓库上继续开发，最值得优先看的几个文件是：

- `main.py`
- `src/auto_chaldea/__init__.py`
- `src/auto_chaldea/core/task_executor.py`
- `src/auto_chaldea/core/task_loader.py`
- `src/auto_chaldea/utils/recognizer.py`
- `assets/task/`
- `assets/template/`

这是本仓库最贴近“真实执行逻辑”的入口，适合用来继续搭建更复杂的任务流和识别策略。
