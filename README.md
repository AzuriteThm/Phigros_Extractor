# Phigros 拆包工具（PhigrosExtractor）

把 Phigros 安装包（APK）里的资源提取为通用格式：谱面 JSON、曲绘 PNG、音乐 WAV、
曲目信息表，并可打包成 Phira 可读取的 `.pez` 自制谱。

**已适配 Phigros 4.0.0（第九章）**，同时兼容旧版安装包（3.x）。
仅供个人学习使用，请勿传播提取出的资源。

---

## 快速开始

1. 安装 [Python 3](https://www.python.org/downloads/)（安装时勾选 *Add to PATH*）。
2. 把 Phigros 安装包改名为 `base.apk`，放进本目录。
3. 双击 `CLICKME.bat`，等待完成（全量提取约 1～3 分钟）。

完成后各资源目录见下表。`base.apk` 可以删掉，下次有新版本再放进来即可。

> 命令行方式等价于：
> ```
> pip install -r requirements.txt
> python gameInformation.py base.apk
> python resource.py base.apk
> python ogg2wav.py
> ```

## 三步流程说明

| 脚本 | 作用 |
|---|---|
| `gameInformation.py` | 从安装包场景数据导出 `info/` 信息表（见下） |
| `resource.py` | 按 Addressables catalog 提取全部资源（含解密隐藏曲） |
| `ogg2wav.py` | 把 `music/` 与 `c9s/` 下的 ogg 转成 wav 并删除源文件（需 ffmpeg） |

## 产出目录

| 目录 | 内容 |
|---|---|
| `info/` | `difficulty.tsv` 定数 · `info.tsv` 曲名/曲师/画师/谱师 · `collection.tsv` 收藏品中文名 · `avatar.txt` 头像 · `single.txt` / `illustration.txt` 单曲/曲绘列表 · `tips.txt` 游戏小贴士 |
| `chart/<曲id>.0/` | 谱面 `EZ/HD/IN/AT.json`（明文，formatVersion 3）；`chart/c9s.*/` 为第九章隐藏曲 |
| `music/` | 音乐（ogg，转 wav 后为 wav）；`<曲id>_IN.wav` 为 IN 专用音源（如 Cristalisia） |
| `illustration/` `illustrationBlur/` `illustrationLowRes/` | 曲绘三套（原图 / 模糊 / 低清） |
| `avatar/` | 头像 PNG |
| `c9s/` | 第九章隐藏曲其余素材（合集头图、剧情立绘等） |

## 交互式打包 .pez（Phira 自制谱）

```
python phira_gui.py
```

弹出窗口：搜索/选择曲目 → 点选难度（该曲没有的难度自动置灰）→ 保存 .pez。
选中曲目后右侧面板显示曲师/画师/定数/谱师，切换难度时联动更新。

自动处理的特殊情况：

- IN 专用音源（Cristalisia 的 `music_IN`）按所选难度自动选用；
- 第九章隐藏曲（`c9s.*`）谱面/音频/曲绘跨目录配对，难度显示为 SP；
- `info.tsv` 缺失时从曲 id（`曲名.曲师`）推导元数据。

另有旧脚本 `python phira.py`：一次性把**所有**曲目按难度打包到 `phira/{EZ,HD,IN,AT}/`。

## 配置（config.ini）

```ini
[TYPES]
; 各类资源提取开关
avatar = true
Chart = true
IllustrationBlur = true
IllustrationLowRes = true
Illustration = true
music = true
; 第九章隐藏曲（加密 bundle）开关
c9s = true

[C9S]
; 隐藏曲解密密码（AES-256-CBC：key=SHA512(密码)[0:32]，iv=SHA512(密码)[32:48]）
; 官方更换密码后只需改这里，无需改代码
password = Backward, go backward, turn back to the antemundane realm, go back to the -

[UPDATE]
; 增量模式：任意一项非 0 时启用（见下）
main_story = 0
other_song = 0
side_story = 0
```

### 增量更新（新版本发布后）

新 APK 出来后不必全量重提：

1. 把新的 `base.apk` 放进目录；
2. `[UPDATE]` 任一项改成 `1`，运行 `resource.py`（或 CLICKME）；
3. 程序只提取 `chart/` 里没有的曲目和 `avatar/` 里没有的头像；
4. 完成后把数值改回 `0`。

注意：增量模式按目录对比，`gameInformation.py` 的信息表每次都会全量重建。

## 文件清单

| 文件 | 说明 |
|---|---|
| `CLICKME.bat` | Windows 一键入口（装依赖 → 三步流程） |
| `catalog.py` | Addressables catalog 解析 + 隐藏曲 AES 解密 |
| `gameInformation.py` | 信息表导出（旧版/新版 typetree 自动回退） |
| `resource.py` | 资源提取主程序 |
| `ogg2wav.py` | ogg 转 wav |
| `phira_gui.py` | 交互式 .pez 打包器 |
| `typetree.json` | MonoBehaviour 结构定义（`*_v400` 条目由 DummyDll 生成） |
| `config.ini` | 提取开关 / 隐藏曲密码 / 增量模式 |
| `libogg.dll` `libvorbis.dll` | fsb5 音频重建必需，勿删 |
| `log.py` | 日志工具 |
| `requirements.txt` | 依赖清单 |
| `LICENSE` | 许可证 |

运行后出现的 `__pycache__/` 是 Python 字节码缓存，可随时删除，会自动重建。

## 依赖

- Python 3.10+
- `pip install -r requirements.txt`：UnityPy / fsb5 / pycryptodome（+pydub）
- `ogg2wav.py` 需要 [ffmpeg](https://ffmpeg.org/download.html) 在 PATH 中

## 常见问题

**Q: 提取某曲时报"无法读取 bundle"？**
多为大文件复制偶发的 CRC 错误——重新复制 APK 再跑；程序已内置 3 次重试。

**Q: 游戏更新后解析信息表失败？**
用 [Il2CppDumper](https://github.com/Perfare/Il2CppDumper) 处理新 APK 得到 DummyDll，
再用 [TypeTreeGenerator](https://github.com/K0lb3/TypeTreeGenerator) 重新生成
`GameInformation` 树，替换 `typetree.json` 里的 `GameInformation_v400` 条目。
注意：序列化字段以生成器结果为准，不要按 dump.cs 的类字段手写（两者不一致）。

**Q: 隐藏曲内容是空的 / 解密失败？**
检查 `[C9S] password` 是否为当前版本的正确密码。

**Q: 手机上怎么用？**
在 Termux 等 Linux 环境中直接运行三个 py 脚本（参数传 APK 路径）；无参数时脚本
会尝试通过 `pm path com.PigeonGames.Phigros` 自动定位安装包。

---

## 附录：4.0.0 相对旧版本的适配点

1. **Addressables catalog 新格式**（`catalog.py`）
   3.x 的 catalog 直接用 bundle 文件名做资源地址；4.0.0 起所有 bundle 重建，
   资源 key 变为双哈希形式，必须解析 catalog 条目（KeyDataString /
   EntryDataString 二进制结构）把每个资源映射到它真实的 bundle 文件名。
   旧版 APK 走同一套解析器，两者兼容。

2. **GameInformation 曲库 typetree 更新**
   曲库数据在安装包 `level0` 场景里。4.0.0 的 GameInformation 在
   challengeSongItems 之后新增 `hiddenChallengeSongItem`（隐藏课题曲）。
   `typetree.json` 的 `*_v400` 条目由 DummyDll 经 TypeTreeGenerator 按 Unity
   序列化规则自动生成。`gameInformation.py` 自动在旧树/新树间回退。

3. **第九章隐藏曲加密 bundle**（`config.ini` 的 `[C9S]`）
   4.0.0 新增 `C9SecretAssetBundleProvider`，8 个 `c9s.*` bundle 使用
   AES-256-CBC 整包加密（文件头 `47 A9 C9 7D BE EF C3 E4`），
   `key = SHA512(UTF8(密码))[0:32]`，`iv = SHA512(...)[32:48]`。
   密码是游戏内第九章解谜答案，改版后只需更新 config.ini。

4. **增量模式语义变化**
   旧版按"主线/单曲/支线更新数量"截取依赖包内曲库顺序表，新版该表结构已变，
   统一改为目录对比增量（见上文"增量更新"）。
