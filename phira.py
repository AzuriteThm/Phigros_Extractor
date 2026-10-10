# -*- coding: utf-8 -*-
"""批量 .pez 打包器（PhigrosExtractor 版）。
把 chart/ 里**所有**曲目按难度打包到 phira/{EZ,HD,IN,AT,SP}/，隐藏曲进 SP。

用法：
    python phira.py            # 交互式询问音频格式后全量打包（跳过已存在的 pez）
    python phira.py -f         # 强制重新打包（覆盖已存在）
    python phira.py --ogg      # 免交互：用 ogg（music_ogg/，每首约 3~9 MB，推荐）
    python phira.py --wav      # 免交互：用无损 wav（music_wav/，每首约 30~60 MB）

交互默认回车 = ogg。所选格式优先、另一种作兜底（某曲缺少所选格式时自动用另一种）。
其余打包规则与 phira_gui.py 完全一致（IN 专用音源、隐藏曲配对、Random 差分谱师）。

依赖同目录下的提取产物：chart/ music_ogg/ music_wav/ illustration*/ info/
"""
import os
import sys

from phira_gui import (LEVELS, load_infos, scan_songs, meta_for, info_for,
                       find_audio, build_pez)

OUT_DIR = "phira"


def ask_format():
    """交互式询问音频格式，返回 'ogg' 或 'wav'。"""
    print("批量打包音频格式选择：")
    print("  1) ogg  —— 体积小（每首约 3~9 MB），推荐")
    print("  2) wav  —— 无损原音质（每首约 30~60 MB）")
    while True:
        try:
            choice = input("请输入 1 或 2（默认 1）: ").strip()
        except EOFError:
            choice = ""
        if choice in ("", "1"):
            return "ogg"
        if choice == "2":
            return "wav"
        print("无效输入，请输入 1 或 2。")


def main():
    args = sys.argv[1:]
    force = "-f" in args or "--force" in args
    if "--ogg" in args:
        fmt = "ogg"
    elif "--wav" in args:
        fmt = "wav"
    else:
        fmt = ask_format()
    prefer = (fmt,) + tuple(e for e in ("ogg", "wav", "mp3") if e != fmt)
    print("音频格式：%s" % fmt)

    songs = scan_songs()
    if not songs:
        print("错误：chart/ 目录为空，请先运行 resource.py 提取资源。")
        sys.exit(1)
    infos = load_infos()
    print("发现 %d 首曲目（info 表 %d 条）" % (len(songs), len(infos)))

    # 重建输出目录（保留目录结构，清掉旧 pez）
    for lv in LEVELS + ["SP"]:
        d = os.path.join(OUT_DIR, lv)
        os.makedirs(d, exist_ok=True)
        if force:
            for f in os.listdir(d):
                if f.endswith(".pez"):
                    os.remove(os.path.join(d, f))

    ok = skipped = failed = 0
    total_mb = 0.0
    failures = []
    fallback = 0
    for base_id, levels, chart_dir in songs:
        name, composer, illustrator, difficulty = meta_for(base_id, infos)
        m = info_for(base_id, infos)
        charter_list = m["Charter"] if m else []
        meta = (name, composer, illustrator, difficulty, charter_list)
        for lv in levels:
            out = os.path.join(OUT_DIR, lv if lv in LEVELS else "SP",
                               "%s-%s.pez" % (base_id, lv))
            if os.path.isfile(out) and not force:
                skipped += 1
                continue
            # 按所选格式选源（另一种兜底），原样打包不转码
            audio = find_audio(base_id, lv, prefer=prefer)
            if not audio:
                failed += 1
                failures.append("%s [%s]: 找不到音频" % (base_id, lv))
                print("  FAIL %s [%s] 找不到音频" % (base_id, lv))
                continue
            if os.path.splitext(audio)[1].lstrip(".") != fmt:
                fallback += 1
            try:
                success, msg = build_pez(base_id, chart_dir, lv, meta, out, audio_path=audio)
            except Exception as e:
                success, msg = False, str(e)
            if success:
                ok += 1
                total_mb += os.path.getsize(out) / 1e6
                print("  OK  %s [%s]" % (name, lv))
            else:
                failed += 1
                failures.append("%s [%s]: %s" % (base_id, lv, msg))
                print("  FAIL %s [%s] %s" % (base_id, lv, msg))

    print("-" * 40)
    print("完成：成功 %d，跳过 %d，失败 %d，合计 %.1f MB" % (ok, skipped, failed, total_mb))
    if fallback:
        print("注意：%d 个 pez 因缺少 %s 音源回退用了另一种格式" % (fallback, fmt))
    if failures:
        print("\n失败明细：")
        for f in failures:
            print("  ", f)
        sys.exit(1)


if __name__ == "__main__":
    main()
