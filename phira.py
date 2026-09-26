# -*- coding: utf-8 -*-
"""批量 .pez 打包器（PhigrosExtractor 版）。
把 chart/ 里**所有**曲目按难度打包到 phira/{EZ,HD,IN,AT}/，隐藏曲进 phira/SP/。

用法：
    python phira.py            # 全量打包（跳过已存在的 pez）
    python phira.py -f         # 强制重新打包（覆盖已存在）

依赖同目录下的提取产物：chart/ music/ illustration*/ info/
打包规则与 phira_gui.py 完全一致（含 IN 专用音源、隐藏曲配对）。
"""
import os
import sys
import shutil
from zipfile import ZipFile

from phira_gui import (LEVELS, load_infos, scan_songs, meta_for, info_for,
                       find_audio, find_picture, build_pez)

OUT_DIR = "phira"


def main():
    force = "-f" in sys.argv or "--force" in sys.argv

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
    failures = []
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
            try:
                success, msg = build_pez(base_id, chart_dir, lv, meta, out)
            except Exception as e:
                success, msg = False, str(e)
            if success:
                ok += 1
                print("  OK  %s [%s]" % (name, lv))
            else:
                failed += 1
                failures.append("%s [%s]: %s" % (base_id, lv, msg))
                print("  FAIL %s [%s] %s" % (base_id, lv, msg))

    print("-" * 40)
    print("完成：成功 %d，跳过 %d，失败 %d" % (ok, skipped, failed))
    if failures:
        print("\n失败明细：")
        for f in failures:
            print("  ", f)
        sys.exit(1)


if __name__ == "__main__":
    main()
