# Phigros 解包打包工具（PhigrosExtractor）

放入 Phigros 安装包，一键提取谱面/曲绘/音频，并打包 Phira 可读取的 `.pez`。
适配 Phigros 3.x / 4.0.0 / 4.0.1。仅供个人学习，请勿传播提取资源。

---

## 快速开始

1. 安装环境（只需一次）：
   - [Python 3.10~3.12](https://www.python.org/downloads/)（安装勾选 *Add to PATH*；
     3.13+ 缺 UnityPy 轮子，脚本会自动尝试 `py -3.12`）
   - [ffmpeg](https://ffmpeg.org/download.html) 放入 PATH（音频转换/转码用）
2. 把 Phigros 安装包（APK）改名为 `base.apk`，放进本目录。
3. 双击 `CLICKME.bat`，按提示操作即可。

流程：导出曲目信息 → 提取全部资源 → ogg 转 wav → 询问是否批量打包 .pez。

首次提取约 2~3 分钟；wav 转换约 5~15 分钟（可在 config.ini 关 music 后跳过）。

## 日常使用

| 命令 | 作用 |
|---|---|
| 双击 `CLICKME.bat` | 全流程（新版本 APK 更新后重跑即可） |
| `python phira.py` | 批量打包所有 .pez（先选 ogg/wav） |
| `python phira.py --ogg` / `--wav` | 免交互批量打包；`-f` 强制重打 |
| `python phira_gui.py` | 图形界面：搜索选曲 → 选难度 → 选音质档位 → 单个生成 |

### GUI 音频体积档位

| 档位 | 内容 | 参考体积* |
|---|---|---|
| 不压缩 | 无损 wav 原音质 | ~60 MB |
| 平衡 | ogg 192kbps 立体声 | ~9 MB |
| 小文件 | ogg 64kbps 单声道 32kHz | ~6 MB |

\* 以 What do you want more than a Happy ending?（EZ，谱面 4.7MB）为例；
小文件档下限由谱面体积决定。转码以 wav 为源，避免二次有损压缩。

## 产出目录

| 目录 | 内容 |
|---|---|
| `info/` | 定数表、曲名/曲师/画师/谱师表、收藏品、头像表、tips |
| `chart/<曲id>.0/` | 谱面 JSON（`c9s.*` 为第九章隐藏曲） |
| `music_ogg/` | 提取的原始音频（ogg，不删除）；`<曲id>_IN.ogg` 为 IN 专用音源 |
| `music_wav/` | 无损 wav（ogg2wav 转出） |
| `illustration/` `illustrationBlur/` `illustrationLowRes/` | 曲绘（多曲绘曲按难度存为 `<曲id>_EZ.png` 等） |
| `avatar/` | 头像 PNG |
| `c9s/` | 隐藏曲其余素材 |
| `phira/{EZ,HD,IN,AT,SP}/` | 批量打包的 .pez |

## 新版本 APK 更新后的增量提取

1. 换上新 `base.apk`；2. `config.ini` 的 `[UPDATE]` 任一项改 `1`；
3. 运行 `CLICKME.bat`（只提取新曲目）；4. 改回 `0`。

## 文件清单

| 文件 | 说明 |
|---|---|
| `CLICKME.bat` | 一键入口 |
| `catalog.py` | Addressables catalog 解析 + 隐藏曲 AES 解密 |
| `gameInformation.py` | 信息表导出（新旧 typetree 自动回退，兼容 data.unity3d 布局） |
| `resource.py` | 资源提取主程序 |
| `ogg2wav.py` | ogg → wav（ffmpeg，保留源） |
| `phira_gui.py` | 图形界面打包器（三档音质） |
| `phira.py` | 批量打包器（ogg/wav 可选） |
| `typetree.json` | MonoBehaviour 结构定义 |
| `config.ini` | 提取开关 / 隐藏曲密码 / 增量模式 |
| `libogg.dll` `libvorbis.dll` | 音频重建必需，勿删 |
| `log.py` `requirements.txt` `LICENSE` | 其余 |

运行后出现的 `__pycache__/` 是缓存，可删。

## 常见问题

**Q: 依赖装不上 / 提示缺 UnityPy？**
Python 版本过高（3.13+）。安装 Python 3.12 后重跑，CLICKME 会自动选用。

**Q: 某曲报"无法读取 bundle"？**
大文件复制偶发 CRC 错误，重新复制 APK；程序已内置 3 次重试。

**Q: 游戏更新后信息表解析失败？**
Il2CppDumper 出 DummyDll → TypeTreeGenerator 重新生成 `GameInformation` 树，
替换 `typetree.json` 的 `GameInformation_v400` 条目（序列化字段以生成器为准）。

**Q: 隐藏曲内容为空？**
检查 `config.ini` 的 `[C9S] password` 是否为当前版本密码。

**Q: 批量打包想换音质重打？**
`python phira.py --wav -f`（或 `--ogg -f`）强制全量重打。
