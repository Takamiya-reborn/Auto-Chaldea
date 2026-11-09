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

> **分辨率要求**：内置模板均以 1280×720 分辨率采集，任务中的 `region` 坐标也以 1280×720 为基准。
> 模板匹配不做任何缩放，请将设备（模拟器或真机）分辨率固定为 **1280×720** ，其他分辨率下识别会失败。

- 基于 OpenCV 的模板匹配识别 UI 元素
- 支持全屏识别和 ROI（感兴趣区域）识别
- 支持单模板识别和多模板识别
- 支持按置信度排序、索引点击和重复匹配处理
- 可配置识别区域、重试间隔和超时

### 3. YAML 任务系统

- 任务步骤以 YAML 配置，放在 `assets/task/`
- 每个步骤都可以定义模板、区域、等待、重试与超时
- 支持 `single` / `multi` / `none` 三种识别模式
- 允许通过 `Center` 直接点击屏幕中心，跳过模板识别；也支持 `Enemy1` / `Enemy2` / `Enemy3` 等内置坐标点
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
│       │   ├── graph_runner.py      # 画面图任务执行
│       │   ├── flows.py             # 内置标准周回 flow 展开
│       │   └── ...
│       ├── ui/
│       │   ├── main_window.py
│       │   ├── task_panel.py
│       │   ├── task_detail.py
│       │   └── ...
│       └── utils/
│           ├── adb_device.py
│           ├── paths.py
│           ├── recognizer.py
│           └── screen.py            # 帧来源：截屏 + 帧缓存 + ROI 缓存
├── assets/
│   ├── platform-tools/
│   ├── qss/
│   ├── task/
│   └── template/
├── scripts/
│   ├── scap.py              # 开发用截图脚本，生成模板或校验画面
│   ├── check.py             # 检查屏幕与模板的最高匹配度
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

打包版本默认不显示控制台。如果启动失败，会在 exe 同目录生成
`startup-error.log`，同时弹出错误详情窗口；请根据该文件排查缺少的资源或
运行库问题。

### 开发期间的辅助脚本

```powershell
uv run scripts/scap.py [port]
```

功能是截图并放置在`assets/template/`
如果本机只有一个 ADB 设备，可省略端口；如果有多个设备，请显式指定端口来区分。

检查当前屏幕与指定模板图像的最高矩阵匹配度：

```powershell
uv run scripts/check.py "Path to template image"
```

脚本会截取一次当前屏幕，使用 OpenCV `TM_CCOEFF_NORMED` 在指定模板图像中查找最高匹配度，并输出匹配度及最佳匹配位置。默认要求只有一个在线 ADB 设备；多设备时可使用序列号明确指定：

```powershell
uv run scripts/check.py "Path to template image" --device SERIAL
```

### 设置任务执行次数

在任务详情区域点击“执行”后，可在弹窗中输入执行次数，范围为 1 到 9999 次。这里的次数表示完整任务的重复次数，每次都会从第一个步骤重新开始执行。

运行期间，状态栏会显示当前执行次数与总次数，并可使用“暂停”、“继续”或“停止”控制任务。任务执行失败或设备断开时会提前终止后续执行。

## 任务 YAML 介绍

任务配置位于 `assets/task/`，一个最小示例如下（`region` 与内置坐标点均以 1280×720 分辨率为基准，见上文「模板识别引擎」的分辨率要求）：

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
- `template`：模板图片文件名，默认从 `assets/template/` 中查找；也支持内置命名坐标点，任务开始执行时统一解析为固定坐标点击（跳过模板识别）：
  - `Center`：屏幕中心
  - `Enemy1` / `Enemy2` / `Enemy3`：预设的敌人位置，坐标在 `task_executor.py` 的 `NAMED_POINTS` 中以 1280x720 为基准填写，执行时按实际屏幕尺寸等比缩放
  - 命名坐标点也可与普通模板混用在 `multi` 模式的逗号列表中，如 `Enemy1,Enemy2,Enemy3`，解析时拆分为先点击坐标、再识别模板的独立步骤
- `mode`：识别模式，默认 `single`；`multi` 表示同时匹配多个模板, 例如：要在三色卡中任选几张、在不同狗粮中任选20张；`none` 只识别并等待模板出现，不执行点击，适合等待开始标志
- `count`：在 `multi` 模式下，重叠去重后按屏幕位置（上→下、左→右）取前 `count` 个结果依次点击
- `index`：同屏多个匹配时的点击顺序，默认取第一个匹配
- `region`：识别区域，可传 `x1, y1, x2, y2`，也支持 `左`、`右`、`上`、`下`、`左上` 等别名
- `step_interval`：点击成功后等待多久再进入下一步，默认约 `1.0` 秒
- `timeout`：单步识别超时，超过后任务失败并终止
- `retry_interval` 和 `max_retry_interval`：未匹配到目标时的重试间隔与上限

## 画面图任务

线性 steps 是"每步只有一个去向"的退化图。任务也可以直接写成画面图（借鉴 MAA
ProcessTask 的循环语义）：节点 = 一个画面（识别 + 动作），`next` = 有序候选列表——
一帧截图按序尝试候选，先命中谁走谁。"接下来做什么"由当前画面决定，而不是步骤顺序。

```yaml
task_name: 图任务示例
entry: [选助战]
nodes:
  选助战:
    template: 助战池/选助战
    region: 右
    max_times: 3
    exceeded_next: []
    next: [开始任务]
  开始任务:
    template: 基本/开始任务
    region: 右下
    timeout: 3
    next: [战斗]
  战斗:
    template: 基本/attack
    region: 右下
    action: none
    steps:
      - template: skill_1.png
      - template: Center
    next: [战斗, 结算]
  结算:
    template: 基本/请点击游戏界面
    region: 下
    next: [结算, 下一步]
```

### 节点字段（除 template 外全部可省略）

- `template`：识别模板；缺省时为无条件节点（如命名坐标点），只能放在候选列表末尾
- `region` / `index` / `threshold`：识别区域、点击第几个匹配、匹配阈值，与线性步骤语法一致
- `action`：`click`（默认，点击识别到的目标）/ `none`（只识别，配合 `steps`）
- `click`：命名坐标点（`Center`、`enemy1` 等），无识别直接点击
- `steps`：命中后按线性语法顺序执行的子步骤（复用 `task_executor`）
- `next`：候选下一节点列表（一帧截图按序尝试）
- `on_error_next`：出错路由（子步骤失败 / 等待超时且无可选节点），用于自救
- `max_times` / `exceeded_next`：本节点最多命中次数；到达后再出现则走 `exceeded_next` 而不执行动作
- `timeout`：等待本节点的秒数；超时视为"已处理"，直接前往其 `next`（可选节点语义，与线性 `timeout` 一致）
- `pre_delay` / `post_delay`：动作前 / 后的等待秒数

### 路由与校验规则

- 每轮访问取一帧截图，按序扫描候选节点，命中即执行其动作并路由到它的 `next`
- 等待超时或用户跳过时：优先视为"可选节点已处理"（第一个声明了 `timeout` 的候选直接前往其 `next`），否则走第一个候选的 `on_error_next`，都没有则任务失败
- 点击成功后立即失效帧缓存，下一轮强制重新截屏
- 加载时静态校验：所有边引用的节点必须存在；无条件节点不能出现在候选列表中间（它不识别就命中，会短路后面的候选）；不可达节点只告警不阻止运行
- `max_times` 到达后节点不再执行动作，仅按 `exceeded_next` 路由；`exceeded_next` 为空列表表示"当它不存在"

## 标准周回 flow

周回任务的外壳（助战 → 开始 → 战斗 → 结算）一成不变，已沉淀为内置图模板。
任务文件加 `flow: 标准周回` 后只写每回合的变化部分，加载时展开为上面的画面图。
连刷次数不写在任务文件里，由 UI 的「执行次数」输入驱动：一次图执行 = 一轮完整周回。
完整示例见 `assets/task/日常虐菜Pro.yaml`。

```yaml
task_name: 日常虐菜Pro
prerequisite: 1号位所长，2号位摩根，三号位杀狐，御主穿CD服
flow: 标准周回
turns:
  1: # 每回合一个条目，键 = 回合序号，必须从 1 连续编号
    skills:
      - pool: 2 # → 技能池/skill_2（region 默认 下）
      - pool: 3
        index: 1 # 第 2 个匹配
      - target: 摩根/冬之女王 # → 角色池/摩根/冬之女王（目标头像）
      - master: true # → 基本/御主技能（region 默认 右）
    cards: # 3 个选卡槽位，每个槽位一次识别点击；解析到 cards 自动先点右下角攻击
      - np: 既已过去的人理之终 # 宝具槽位 → 宝具/<名>
      - [buster, arts] # 目标范围：点范围内屏幕最靠前的一个命中
      - [buster, arts, quick] # 最后一张兜底全色卡
```

### 技能条目字段

- `pool` / `target` / `master` / `template`：四选一，分别为技能池模板序号、角色池目标头像、御主技能、原始模板路径；字符串简写按是否含 `/` 区分 target 与 template；`pool` 条目 region 默认 `下`，`master` 条目 region 默认 `右`，均可在条目里覆盖
- `index` / `region` / `threshold`：与线性步骤语法一致，原样透传
- `center`：显式覆盖动画跳过方式（见下表），取 `double` / `tap` / `none`，或布尔值（`true` → `tap`，`false` → `none`）

### 回合条目字段

- `skills`：技能条目列表，按序执行（见上「技能条目字段」）
- `cards`：选卡槽位列表，每回合最多 3 个（宝具占其一），每个槽位一次识别点击，按列表顺序执行。槽位三种写法：字符串（单一目标 → `基本/<名>`）、数组（目标范围，`multi` 模式点屏幕最靠前的一个命中）、映射（宝具 `np: 名称` → `宝具/<名>`）。已选中的卡出现选中标记后置信度下降不再命中，槽位间的候选范围可安全重叠。解析到 `cards` 即自动先点击右下角攻击按钮进入选卡，无需显式配置，个别界面差异用 `attack_region` 字段覆盖

### 动画跳过规则（自动分派）

`Center` 点击是加快动画播放用的，不是游戏确认按钮。技能条目的点击方式按下列规则自动分派，无需手写中央点击：

| 条目类型               | 点击方式      | 原因                                                      |
| ---------------------- | ------------- | --------------------------------------------------------- |
| 普通技能（pool）       | 双击          | 第一击触发技能，第二击跳过动画                            |
| 后面紧跟 target 的技能 | 单击          | 只是打开目标菜单，动画还没开始                            |
| target（目标头像）     | 单击 + Center | 动画在选完目标后才开始播；双击目标会点在目标菜单上出错    |
| master                 | 单击          | 御主技能菜单里无动画可跳                                  |
| 裸 template 条目       | 单击          | 用途不明，单击最稳妥；需要跳动画时显式写 `center: double` |

### 逃生门

- 任务同时写了 `flow` 和 `nodes` 时以手写 `nodes` 为准（不展开 flow，仅打印提示）
- 非 `标准周回` 的流程：不加 `flow` 字段，直接手写 `nodes`（见「画面图任务」）

## 屏幕帧复用

所有识别共用按设备注册的帧来源（`utils/screen.py`），一次截屏可被多次识别复用：

- **原始格式截屏**：`screencap` 不带 `-p`，跳过设备端 PNG 编码与主机端解码；解析失败时自动回退 PNG 并记住，后续不再尝试原始格式
- **帧缓存**：识别只读缓存帧；点击成功后由执行器立即失效，重试循环每轮也强制刷新，语义与旧版"每次识别都截屏"一致
- **ROI 缓存**：single 模式且 `index: 0` 时启用——模板命中后记住位置（向外扩一圈模板尺寸作余量），下次只在附近小区域搜索；未命中自动退回全区域搜索
- **图模式额外收益**：一轮访问按序尝试全部候选时共用同一帧截图

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

## 许可证与素材声明

除另有说明外，本项目中由项目作者创作并拥有相应权利的源代码，采用 [MIT License](LICENSE) 授权。

以下内容不在上述 MIT 授权范围内，仍受其原始权利人或原始许可证约束：

- `assets/template/` 中与 Fate/Grand Order 相关的截图、识别模板和游戏素材
- `assets/task/` 中基于游戏内容制作的任务配置及相关素材
- `assets/platform-tools/` 中的 Android Platform Tools 及其附带文件
- 项目依赖、第三方库和第三方资源

本项目是非官方的个人研究与自动化工具，与 Fate/Grand Order、其开发者或发行方不存在隶属、授权或合作关系。使用者应自行确认相关游戏服务条款、素材使用权限以及所在地区的法律要求，并自行承担使用本项目产生的风险。

除 MIT 许可证明确授予的权利外，本项目不授予任何游戏名称、商标、角色、画面或其他第三方内容的权利。
