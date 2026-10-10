# -*- coding: utf-8 -*-
"""把 music_ogg/ 下的 ogg 转换为 music_wav/ 下的 wav（保留源文件，不删除）。
c9s/ 目录下的 ogg 就地转换（同样保留）。已存在的 wav 自动跳过。

使用 ffmpeg（需在 PATH 中），不依赖 pydub。
"""
import os
import subprocess
import sys

AUDIO_EXTS = (".ogg", ".mp3", ".flac")


def convert(src, dst):
    """ffmpeg 转码；返回 (成功, 消息)。"""
    if os.path.isfile(dst):
        return True, "skip"
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", src, "-vn", dst],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return r.returncode == 0, dst


def main():
    ok = fail = skip = 0
    # music_ogg/*.ogg -> music_wav/*.wav
    if os.path.isdir("music_ogg"):
        os.makedirs("music_wav", exist_ok=True)
        for f in sorted(os.listdir("music_ogg")):
            if not f.lower().endswith(AUDIO_EXTS):
                continue
            src = os.path.join("music_ogg", f)
            dst = os.path.join("music_wav", os.path.splitext(f)[0] + ".wav")
            if os.path.isfile(dst):
                skip += 1
                continue
            success, msg = convert(src, dst)
            if success:
                ok += 1
                print("转换成功: %s -> %s" % (src, dst))
            else:
                fail += 1
                print("转换失败: %s" % src)
    # c9s/*.ogg -> c9s/*.wav（就地，保留源）
    if os.path.isdir("c9s"):
        for f in sorted(os.listdir("c9s")):
            if not f.lower().endswith(AUDIO_EXTS):
                continue
            src = os.path.join("c9s", f)
            dst = os.path.join("c9s", os.path.splitext(f)[0] + ".wav")
            if os.path.isfile(dst):
                skip += 1
                continue
            success, _ = convert(src, dst)
            if success:
                ok += 1
                print("转换成功: %s" % dst)
            else:
                fail += 1
                print("转换失败: %s" % src)
    print("完成：转换 %d，跳过 %d，失败 %d" % (ok, skip, fail))
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
