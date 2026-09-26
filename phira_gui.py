# -*- coding: utf-8 -*-
"""交互式 .pez 打包器（替代旧 phira.py 的全量批处理）。
运行后弹出窗口：搜索/选择曲目与难度，自动打包生成 Phira 可读取的 .pez。

依赖同目录下的提取产物：
  chart/<曲id>.0/{EZ,HD,IN,AT}.json   谱面（c9s.* 为 Chart.json）
  music/<曲id>.{ogg,wav}              音频（Cristalisia IN 专用 <id>_IN 自动识别）
  illustration*/<曲id>.png            曲绘（优先 LowRes，与旧版一致）
  info/info.tsv difficulty.tsv        元数据（缺失时从曲 id 推导并提示）
"""
import glob
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from zipfile import ZipFile

LEVELS = ["EZ", "HD", "IN", "AT"]
AUDIO_EXTS = [".ogg", ".wav", ".mp3"]

# Random（Sobrem × Silentroom）七张差分谱的谱师。
# 游戏内按 R/A/N/D/O/M 六字母展示（基础版无字母），变体号 .1~.6 依次对应。
# 谱师名义 = 主谱师 × 该字母变体的合作谱师（来自游戏内展示与 il2cpp 代码常量）。
RANDOM_VARIANTS = {
    "1": "R", "2": "A", "3": "N", "4": "D", "5": "O", "6": "M",
}
RANDOM_CHARTER = {
    # (难度, 字母) -> 谱师名义
    ("EZ", ""): "Barbarianerman", ("HD", ""): "IMD_6", ("IN", ""): "_鉄",
    ("EZ", "R"): "野从 & V17AMax", ("HD", "R"): "Rikko & JKy", ("IN", "R"): "TangScend & Rikko",
    ("EZ", "A"): "野从 & Pcat", ("HD", "A"): "Rikko & Ctymax", ("IN", "A"): "TangScend & NerSAN",
    ("EZ", "N"): "野从 & TimiTini", ("HD", "N"): "Rikko & Gausbon", ("IN", "N"): "TangScend & Myna",
    ("EZ", "D"): "野从 & Clutter", ("HD", "D"): "Rikko & Uvernight", ("IN", "D"): "TangScend & Su1fuR",
    ("EZ", "O"): "野从 & 阿爽", ("HD", "O"): "Rikko & 晨", ("IN", "O"): "TangScend & 百九十八",
    ("EZ", "M"): "野从 & J.R", ("HD", "M"): "Rikko & Likey", ("IN", "M"): "TangScend & XMT小咩兔",
}


def random_variant_of(base_id):
    """返回 (是否 Random 变体, 字母)。如 Random.SobremSilentroom.3 -> (True, 'N')。"""
    stem = base_id.rsplit(".", 1)[0] if "." in base_id else base_id
    if stem != "Random.SobremSilentroom":
        return False, ""
    suffix = base_id.rsplit(".", 1)[-1]
    return True, RANDOM_VARIANTS.get(suffix, "")


def load_infos():
    """读取 info.tsv + difficulty.tsv -> {曲id: 元数据}；文件缺失时返回空表。"""
    infos = {}
    try:
        with open("info/info.tsv", encoding="utf8") as f:
            for line in f:
                line = line.rstrip("\n").split("\t")
                if len(line) >= 4:
                    infos[line[0]] = {
                        "Name": line[1],
                        "Composer": line[2],
                        "Illustrator": line[3],
                        "Charter": line[4:],
                    }
    except OSError:
        pass
    try:
        with open("info/difficulty.tsv", encoding="utf8") as f:
            for line in f:
                line = line.rstrip("\n").split("\t")
                if len(line) >= 2 and line[0] in infos:
                    infos[line[0]]["difficulty"] = line[1:]
    except OSError:
        pass
    return infos


def find_audio(base_id, level=None):
    """按优先级找音频；IN 难度优先用 <id>_IN 专用音源（如 Cristalisia）；
    c9s 隐藏曲的音频不以曲 id 命名，回退到 music/c9s.* 里的第一个。"""
    cands = []
    if level == "IN":
        cands += ["music/%s_IN%s" % (base_id, e) for e in AUDIO_EXTS]
    cands += ["music/%s%s" % (base_id, e) for e in AUDIO_EXTS]
    if base_id.startswith("c9s."):
        cands += sorted(p for p in glob.glob("music/c9s.*") if p.endswith(tuple(AUDIO_EXTS)))
    for p in cands:
        if os.path.isfile(p):
            return p
    return None


def find_picture(base_id):
    dirs = ("illustrationLowRes", "illustration", "illustrationBlur")
    # 曲 id 形如 曲名.曲师.编号；多变体曲（Random 的 .1~.6）共用无编号曲绘，逐步去尾降级
    bases = [base_id]
    parts = base_id.split(".")
    while len(parts) > 1:
        parts.pop()
        bases.append(".".join(parts))
    for b in bases:
        for d in dirs:
            if os.path.isfile("%s/%s.png" % (d, b)):
                return "%s/%s.png" % (d, b)
    if base_id.startswith("c9s."):
        # 隐藏曲曲绘不在常规目录，用 c9s 素材兜底（Blur 曲绘/合集头图/剧情立绘）
        for pat in ("illustrationBlur/c9s.*.png", "illustration/c9s.*.png", "c9s/*.png"):
            hits = sorted(glob.glob(pat))
            if hits:
                return hits[0]
    return None


def scan_songs():
    """扫描 chart/ 目录 -> [(曲id, [可用难度], 曲目目录名)]。c9s 隐藏曲视为 SP 难度。"""
    songs = []
    if not os.path.isdir("chart"):
        return songs
    for d in sorted(os.listdir("chart")):
        full = os.path.join("chart", d)
        if not os.path.isdir(full):
            continue
        if os.path.isfile(os.path.join(full, "Chart.json")):
            songs.append((d, ["SP"], d))  # 第九章隐藏曲
            continue
        levels = [lv for lv in LEVELS if os.path.isfile(os.path.join(full, "%s.json" % lv))]
        if levels:
            songs.append((d[:-2] if d.endswith(".0") else d, levels, d))
    return songs


def info_for(base_id, infos):
    """查 info 条目；多变体曲（Random.SobremSilentroom.5 等）回退到去编号的主条目。"""
    m = infos.get(base_id)
    if m is None and "." in base_id and base_id.rsplit(".", 1)[-1].isdigit():
        m = infos.get(base_id.rsplit(".", 1)[0])
    return m


def meta_for(base_id, infos):
    """取元数据；无 info.tsv 时从曲 id（曲名.曲师）推导。隐藏曲（c9s.*）无公开信息。"""
    if base_id.startswith("c9s."):
        return "Chapter 9 隐藏曲", "", "", []
    m = info_for(base_id, infos)
    if m is not None:
        return m["Name"], m["Composer"], m["Illustrator"], m.get("difficulty", [])
    name, _, composer = base_id.rpartition(".")
    return (name or base_id), composer, "", []


def build_pez(base_id, chart_dir, level, meta, out_path):
    """打包一个 .pez（zip：info.txt + 谱面 + 曲绘 + 音频）。返回 (ok, 消息)。
    meta = (曲名, 曲师, 画师, 定数列表, 谱师列表)"""
    chart_path = os.path.join("chart", chart_dir, "Chart.json" if level == "SP" else "%s.json" % level)
    if not os.path.isfile(chart_path):
        return False, "找不到谱面：%s" % chart_path

    audio = find_audio(base_id, level)
    if not audio:
        return False, "找不到音频：music/%s.(ogg|wav|mp3)" % base_id
    picture = find_picture(base_id)
    if not picture:
        return False, "找不到曲绘：illustration*/%s.png" % base_id

    name, composer, illustrator, difficulty, charter_list = meta
    lv_index = LEVELS.index(level) if level in LEVELS else -1
    lv_value = difficulty[lv_index] if 0 <= lv_index < len(difficulty) else "-"
    charter = charter_list[lv_index] if 0 <= lv_index < len(charter_list) else ""

    # Random 差分谱：谱师名义按变体字母表给出
    is_random, letter = random_variant_of(base_id)
    if is_random:
        charter = RANDOM_CHARTER.get((level, letter), charter)
        if letter:
            name = "%s [%s]" % (name, letter)

    audio_ext = os.path.splitext(audio)[1]
    info_txt = (
        "#\n"
        "Name: %s\n"
        "Song: %s%s\n"
        "Picture: %s.png\n"
        "Chart: %s.json\n"
        "Level: %s Lv.%s\n"
        "Composer: %s\n"
        "Illustrator: %s\n"
        "Charter: %s" % (name, base_id, audio_ext, base_id, base_id,
                         level, lv_value, composer, illustrator, charter)
    )

    with ZipFile(out_path, "w") as pez:
        pez.writestr("info.txt", info_txt)
        pez.write(chart_path, "%s.json" % base_id)
        pez.write(picture, "%s.png" % base_id)
        pez.write(audio, "%s%s" % (base_id, audio_ext))
    return True, out_path


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Phigros .pez 打包器")
        self.geometry("720x480")
        self.minsize(640, 400)

        self.infos = load_infos()
        self.songs = scan_songs()  # [(base_id, levels, chart_dir)]
        self.song_meta = {}
        for base_id, levels, chart_dir in self.songs:
            name, composer, illustrator, difficulty = meta_for(base_id, self.infos)
            self.song_meta[base_id] = (name, composer, illustrator, difficulty)
        self.current = None

        # ── 顶部：搜索 ──────────────────────────────
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 0))
        ttk.Label(top, text="搜索:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh_list())
        ttk.Entry(top, textvariable=self.search_var).pack(side="left", fill="x", expand=True, padx=6)

        # ── 中部：曲列表 + 信息面板 ──────────────────
        mid = ttk.Frame(self)
        mid.pack(fill="both", expand=True, padx=8, pady=8)
        listframe = ttk.Frame(mid)
        listframe.pack(side="left", fill="both", expand=True)
        self.listbox = tk.Listbox(listframe, activestyle="dotbox")
        sb = ttk.Scrollbar(listframe, command=self.listbox.yview)
        self.listbox.config(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        panel = ttk.Frame(mid)
        panel.pack(side="left", fill="both", expand=True, padx=(12, 0))
        self.name_var = tk.StringVar(value="← 选择曲目")
        ttk.Label(panel, textvariable=self.name_var, font=("", 13, "bold"), wraplength=280).pack(anchor="w", pady=(0, 6))
        self.detail_var = tk.StringVar(value="")
        ttk.Label(panel, textvariable=self.detail_var, wraplength=280, justify="left").pack(anchor="w")

        ttk.Label(panel, text="难度:").pack(anchor="w", pady=(10, 0))
        self.level_var = tk.StringVar()
        self.level_buttons = {}
        for lv in LEVELS + ["SP"]:
            rb = ttk.Radiobutton(panel, text=lv, value=lv, variable=self.level_var,
                                 state="disabled", command=self.on_level)
            rb.pack(side="left", padx=4)
            self.level_buttons[lv] = rb

        # ── 底部：生成 ──────────────────────────────
        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bottom, text="生成 .pez", command=self.on_generate).pack(side="left")
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(bottom, textvariable=self.status_var).pack(side="left", padx=12)

        self.refresh_list()

    def display_name(self, base_id):
        """列表/标题显示名；Random 变体追加 [R] 等字母标注。"""
        name = self.song_meta[base_id][0]
        is_random, letter = random_variant_of(base_id)
        if is_random and letter:
            return "%s [%s]" % (name, letter)
        return name

    # ── 事件 ──────────────────────────────────────
    def refresh_list(self):
        kw = self.search_var.get().strip().lower()
        self.listbox.delete(0, "end")
        self.list_index = []
        for i, (base_id, levels, _) in enumerate(self.songs):
            text = "%s  (%s)" % (self.display_name(base_id), base_id)
            if kw and kw not in text.lower():
                continue
            self.listbox.insert("end", text)
            self.list_index.append(i)
        if self.songs:
            self.status_var.set("共 %d 首" % len(self.list_index))

    def on_select(self, _=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        base_id, levels, chart_dir = self.songs[self.list_index[sel[0]]]
        self.current = (base_id, levels, chart_dir)
        name, composer, illustrator, difficulty = self.song_meta[base_id]
        audio = find_audio(base_id, None)
        self.name_var.set(self.display_name(base_id))
        self.detail_var.set(
            "曲师: %s\n画师: %s\n曲id: %s\n音频: %s" % (
                composer or "-", illustrator or "-", base_id,
                os.path.basename(audio) if audio else "缺失!"))
        for lv, btn in self.level_buttons.items():
            btn.state(["!disabled"] if lv in levels else ["disabled"])
        self.level_var.set(levels[-1])
        self.on_level()

    def on_level(self):
        base_id, levels, chart_dir = self.current or (None, None, None)
        if not base_id:
            return
        lv = self.level_var.get()
        name, composer, illustrator, difficulty = self.song_meta[base_id]
        idx = LEVELS.index(lv) if lv in LEVELS else -1
        lv_value = difficulty[idx] if 0 <= idx < len(difficulty) else "-"
        charter = ""
        m = info_for(base_id, self.infos)
        if m is not None and 0 <= idx < len(m.get("Charter", [])):
            charter = m["Charter"][idx]
        is_random, letter = random_variant_of(base_id)
        if is_random:
            charter = RANDOM_CHARTER.get((lv, letter), charter)
        self.detail_var.set(
            "曲师: %s\n画师: %s\n定数: %s\n谱师: %s\n曲id: %s" % (
                composer or "-", illustrator or "-", lv_value, charter or "-", base_id))

    def on_generate(self):
        if not self.current:
            messagebox.showwarning("提示", "请先选择曲目")
            return
        base_id, levels, chart_dir = self.current
        lv = self.level_var.get()
        if lv not in levels:
            messagebox.showerror("错误", "该曲目没有 %s 难度" % lv)
            return
        default_name = "%s-%s.pez" % (base_id, lv)
        out = filedialog.asksaveasfilename(
            title="保存 .pez", initialfile=default_name,
            defaultextension=".pez", filetypes=[("Phira 谱面包", "*.pez")])
        if not out:
            return
        m = info_for(base_id, self.infos)
        meta = self.song_meta[base_id] + (m["Charter"] if m else [],)
        try:
            ok, msg = build_pez(base_id, chart_dir, lv, meta, out)
        except Exception as e:
            ok, msg = False, str(e)
        if ok:
            self.status_var.set("已生成: %s" % msg)
            messagebox.showinfo("完成", "已生成\n%s" % msg)
        else:
            self.status_var.set("失败: %s" % msg)
            messagebox.showerror("失败", msg)


if __name__ == "__main__":
    app = App()
    app.mainloop()
