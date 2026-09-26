import gc
from concurrent.futures import ThreadPoolExecutor
from configparser import ConfigParser
from io import BytesIO
import os
from queue import Queue
import sys
import threading
import time
from UnityPy import Environment
from UnityPy.classes import AudioClip
from UnityPy.enums import ClassIDType
from zipfile import ZipFile
from log import init_console_logger
import logging
import catalog


queue_out = Queue()
queue_in = Queue()

avatar = {}  # addressableKey -> 头像显示名（info/tmp.tsv，缺省用 key 本身）


def io():
    while True:
        item = queue_in.get()
        if item is None:
            break
        else:
            path, resource = item
            if type(resource) == BytesIO:
                with resource:
                    with open(path, "wb") as f:
                        f.write(resource.getbuffer())
            else:
                with open(path, "wb") as f:
                    f.write(resource)


def save_image(path, image):
    bytesIO = BytesIO()
    image.save(bytesIO, "png")
    queue_in.put((path, bytesIO))


def save_music(path, music: AudioClip):
    fsb = FSB5(music.m_AudioData)
    rebuilt_sample = fsb.rebuild_sample(fsb.samples[0])
    queue_in.put((path, rebuilt_sample))


classes = ClassIDType.TextAsset, ClassIDType.Sprite, ClassIDType.AudioClip


def save(key, entry, pool, logger):
    obj = entry.get_filtered_objects(classes)
    try:
        obj = next(obj).read()
    except StopIteration:
        return  # 该 bundle 里没有可提取的对象（例如纯着色器/特效包）
    if config["c9s"] and key[:4] == "c9s.":
        # 第九章隐藏曲（加密 bundle 解密后的内容）；c9s.test 是官方密码校验文件，跳过
        if key == "c9s.test":
            return
        # 第九章隐藏曲（加密 bundle 解密后的内容）
        if config["chart"] and type(obj).__name__ == "TextAsset":
            logger.info(key)
            p = "chart/" + key
            if not os.path.exists(p):
                os.mkdir(p)
            queue_in.put(("chart/%s/Chart.json" % key, obj.script))
        elif config["music"] and type(obj).__name__ == "AudioClip" and obj.m_Name == "music":
            pool.submit(save_music, "music/%s.ogg" % key, obj)
        elif type(obj).__name__ == "AudioClip" and config["music"]:
            pool.submit(save_music, "c9s/%s_%s.ogg" % (key, obj.m_Name), obj)
        elif type(obj).__name__ in ("Texture2D", "Sprite"):
            name = obj.m_Name
            if config["illustrationBlur"] and "IllustrationBlur" in name:
                pool.submit(save_image, "illustrationBlur/%s.png" % key, obj.image)
            elif config["illustration"] and (name.startswith("Illustration") or "Locked" in name):
                pool.submit(save_image, "illustration/%s.png" % key, obj.image)
            else:
                if not os.path.isdir("c9s"):
                    os.mkdir("c9s")
                pool.submit(save_image, "c9s/%s_%s.png" % (key, name), obj.image)
    elif config["avatar"] and key[:7] == "avatar.":
        key = avatar.get(key[7:], key[7:])
        bytesIO = BytesIO()
        obj.image.save(bytesIO, "png")
        queue_in.put(("avatar/%s.png" % key, bytesIO))
    elif config["chart"] and key[-14:-7] == "/Chart_" and key[-5:] == ".json":
        logger.info(key)
        p = "chart/" + key[:-14]
        if not os.path.exists(p):
            os.mkdir(p)
        queue_in.put(("chart/%s/%s.json" % (key[:-14], key[-7:-5]), obj.script))
    elif config["illustrationBlur"] and key[-23:-3] == ".0/IllustrationBlur.":
        key = key[:-23]
        bytesIO = BytesIO()
        obj.image.save(bytesIO, "png")
        queue_in.put(("illustrationBlur/%s.png" % key, bytesIO))
    elif config["illustrationLowRes"] and key[-25:-3] == ".0/IllustrationLowRes.":
        key = key[:-25]
        pool.submit(save_image, "illustrationLowRes/%s.png" % key, obj.image)
    elif config["illustration"] and key[-19:-3] == ".0/Illustration.":
        key = key[:-19]
        pool.submit(save_image, "illustration/%s.png" % key, obj.image)
    elif config["music"] and key[-12:] == ".0/music.wav":
        key = key[:-12]
        pool.submit(save_music, "music/%s.ogg" % key, obj)
    elif config["music"] and key[-12:] == ".1/music.wav":
        key = key[:-12]
        pool.submit(save_music, "music/%s.1.ogg" % key, obj)
    elif config["music"] and key[-12:] == ".2/music.wav":
        key = key[:-12]
        pool.submit(save_music, "music/%s.2.ogg" % key, obj)
    elif config["music"] and key[-12:] == ".3/music.wav":
        key = key[:-12]
        pool.submit(save_music, "music/%s.3.ogg" % key, obj)
    elif config["music"] and key[-12:] == ".4/music.wav":
        key = key[:-12]
        pool.submit(save_music, "music/%s.4.ogg" % key, obj)
    elif config["music"] and key[-12:] == ".5/music.wav":
        key = key[:-12]
        pool.submit(save_music, "music/%s.5.ogg" % key, obj)
    elif config["music"] and key[-12:] == ".6/music.wav":
        key = key[:-12]
        pool.submit(save_music, "music/%s.6.ogg" % key, obj)
    elif config["music"] and key[-15:] == ".0/music_IN.wav":
        key = key[:-15]
        pool.submit(save_music, "music/%s_IN.ogg" % key, obj)


def load_bundle(apk, entry_name, c9s_password):
    """从 APK 读取 bundle，遇到 4.0.0 的加密 bundle 自动解密。返回 bytes 或 None。
    读取带 CRC 重试（个别环境下大文件读取偶发校验失败）。"""
    data = None
    for attempt in range(3):
        try:
            data = apk.read("assets/aa/Android/%s" % entry_name)
            break
        except Exception:
            if attempt == 2:
                return None
    if data[:8] == catalog.ENCRYPTED_MAGIC:
        if not c9s_password:
            return None
        try:
            data = catalog.decrypt_bundle(data, c9s_password)
        except Exception:
            return None
        if data[:7] != b"UnityFS":
            return None
    return data


def run(path, logger):
    keys, key_to_bundle = catalog.parse_catalog(path)

    table = []
    for key in key_to_bundle:
        if key[:7] == "avatar.":
            table.append([key, key_to_bundle[key]])
        elif key[:4] == "c9s." and config["c9s"]:
            table.append([key, key_to_bundle[key]])
        elif key[:14] == "Assets/Tracks/" and key[:15] != "Assets/Tracks/#":
            table.append([key[14:], key_to_bundle[key]])
    table.sort()
    for key, value in table:
        logger.info('{key}, {value}'.format(key=key, value=value))

    if config["avatar"]:
        if os.path.isfile("info/tmp.tsv"):
            with open("info/tmp.tsv", encoding="utf8") as f:
                for line in f:
                    line = line.rstrip("\n")
                    if not line:
                        continue
                    l = line.split("\t")
                    if len(l) >= 2:
                        avatar[l[1]] = l[0]

    update = config["UPDATE"]
    incremental = update["main_story"] or update["other_song"] or update["side_story"]
    if incremental:
        # 新版曲库数据不在 APK 内，无法按旧版“主线/支线/单曲”数量截取，
        # 改为增量模式：只提取 chart/ 目录里还没有的曲目，以及 avatar/ 里还没有的头像。
        done_songs = set(os.listdir("chart")) if os.path.isdir("chart") else set()
        done_avatars = {f[:-4] for f in os.listdir("avatar")} if os.path.isdir("avatar") else set()
        table = [t for t in table
                 if not (t[0][:7] == "avatar." and avatar.get(t[0][7:], t[0][7:]) in done_avatars)
                 and not (t[0][:7] != "avatar." and t[0][:4] != "c9s." and t[0].split("/")[0] in done_songs)]
        logger.info("增量模式：本次提取 %d 项" % len(table))

    thread = threading.Thread(target=io, daemon=True)
    thread.start()
    ti = time.time()
    c9s_password = config["c9s_password"]
    try:
        with ZipFile(path) as apk:
            with ThreadPoolExecutor(6) as pool:
                for key, entry_name in table:
                    data = load_bundle(apk, entry_name, c9s_password)
                    if data is None:
                        logger.warning("无法读取 bundle：%s（%s）" % (entry_name, key))
                        continue
                    env = Environment()
                    env.load_file(BytesIO(data), name=key)
                    for i_key, i_entry in env.files.items():
                        save(i_key, i_entry, pool, logger)
                    del env
                    gc.collect()
    finally:
        queue_in.put(None)
        thread.join(timeout=60)
    logger.info("%f秒" % round(time.time() - ti, 4))


if __name__ == "__main__":
    if len(sys.argv) == 1 and os.path.isdir("/data/"):
        import subprocess
        r = subprocess.run("pm path com.PigeonGames.Phigros",stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,shell=True)
        file_path = r.stdout[8:-1].decode()
    else:
        file_path = sys.argv[1]
    c = ConfigParser()
    c.optionxform = str
    c.read("config.ini", "utf8")
    types = c["TYPES"]
    config = {
        "avatar": types.getboolean("avatar"),
        "chart": types.getboolean("Chart"),
        "illustrationBlur": types.getboolean("IllustrationBlur"),
        "illustrationLowRes": types.getboolean("IllustrationLowRes"),
        "illustration": types.getboolean("Illustration"),
        "music": types.getboolean("music"),
        "c9s": types.getboolean("c9s"),
        "c9s_password": c.get("C9S", "password", fallback=""),
        "UPDATE": {
            "main_story": c["UPDATE"].getint("main_story"),
            "side_story": c["UPDATE"].getint("side_story"),
            "other_song": c["UPDATE"].getint("other_song")
        }
    }
    if config["music"]:
        from fsb5 import FSB5
        from fsb5 import vorbis
    type_list = ("avatar", "chart", "c9s", "illustrationBlur", "illustrationLowRes", "illustration", "music")
    for directory in type_list:
        if directory != "c9s" and not config[directory]:
            continue
        if not os.path.isdir(directory):
            os.mkdir(directory)
        if os.path.isdir("/system/") and not os.getcwd().startswith("/data/"):
            with open(directory + "/.nomedia", "wb"):
                pass
    run(file_path, init_console_logger())
