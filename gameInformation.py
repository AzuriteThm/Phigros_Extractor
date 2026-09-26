import json
import os
import struct
import sys
from UnityPy import Environment
import zipfile
from io import BytesIO
from log import init_console_logger
import logging
import catalog

DEBUG = False


def read_monobehaviours(env):
    """枚举 (脚本名, MonoBehaviour对象)。直接用 UnityPy 的 PPtr 解析；
    个别对象解析失败（依赖未加载）时跳过。"""
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            name = obj.read().m_Script.get_obj().read().name
        except Exception:
            continue
        yield name, obj


def run_legacy(path, logger, typetree):
    """旧版 APK：GameInformation 等 MonoBehaviour 还在 bin/Data 的场景文件里。"""
    env = Environment()
    with zipfile.ZipFile(path) as apk:
        with apk.open("assets/bin/Data/globalgamemanagers.assets") as f:
            env.load_file(BytesIO(f.read()), name="assets/bin/Data/globalgamemanagers.assets")
        with apk.open("assets/bin/Data/level0") as f:
            env.load_file(BytesIO(f.read()))

    candidates = {
        "GameInformation": ["GameInformation", "GameInformation_v400"],
        "GetCollectionControl": ["GetCollectionControl", "GetCollectionControl_v400"],
        "TipsProvider": ["TipsProvider", "TipsProvider_v400"],
    }
    found = {}
    for script_name, obj in read_monobehaviours(env):
        if script_name not in candidates or script_name in found:
            continue
        for tree_name in candidates[script_name]:
            if tree_name not in typetree:
                continue
            try:
                if script_name == "GameInformation":
                    data = obj.read_typetree(typetree[tree_name])
                    # 校验：必须能读到合法曲库
                    songs = data.get("song", {}).get("mainSongs")
                    assert songs and isinstance(songs[0]["songsId"], str) and songs[0]["songsId"]
                else:
                    # 与旧程序一致：包装为属性访问对象
                    data = obj.read_typetree(typetree[tree_name], True)
                found[script_name] = data
                break
            except Exception:
                continue
    return found.get("GameInformation"), found.get("GetCollectionControl"), found.get("TipsProvider")


def write_legacy_tables(GameInformation, Collections, Tips, logger):
    difficulty = []
    table = []
    for key, songs in GameInformation["song"].items():
        if key == "otherSongs":
            continue
        for song in songs:
            if len(song["difficulty"]) == 5:
                song["difficulty"].pop()
            if song["difficulty"][-1] == 0.0:
                song["difficulty"].pop()
                song["charter"].pop()
            for i in range(len(song["difficulty"])):
                song["difficulty"][i] = str(round(song["difficulty"][i], 1))
            song["songsId"] = song["songsId"][:-2]
            difficulty.append([song["songsId"]]+song["difficulty"])
            table.append((song["songsId"], song["songsName"], song["composer"], song["illustrator"], *song["charter"]))

    logger.info(difficulty)
    logger.info(table)

    with open("info/difficulty.tsv", "w", encoding="utf8") as f:
        for item in difficulty:
            f.write("\t".join(map(str, item)))
            f.write("\n")

    with open("info/info.tsv", "w", encoding="utf8") as f:
        for item in table:
            f.write("\t".join(item))
            f.write("\n")

    single = []
    illustration = []
    for key in GameInformation["keyStore"]:
        if key["kindOfKey"] == 0:
            single.append(key["keyName"])
        elif key["kindOfKey"] == 2 and key["keyName"] != "Introduction" and key["keyName"] not in single:
            illustration.append(key["keyName"])

    with open("info/single.txt", "w", encoding="utf8") as f:
        for item in single:
            f.write("%s\n" % item)

    with open("info/illustration.txt", "w", encoding="utf8") as f:
        for item in illustration:
            f.write("%s\n" % item)
    logger.info(single)
    logger.info(illustration)

    D = {}
    for item in Collections.collectionItems:
        if item.key in D:
            D[item.key][1] = item.subIndex
        else:
            D[item.key] = [item.multiLanguageTitle.chinese, item.subIndex]

    with open("info/collection.tsv", "w", encoding="utf8") as f:
        for key, value in D.items():
            f.write("%s\t%s\t%s\n" % (key, value[0], value[1]))

    with open("info/avatar.txt", "w", encoding="utf8") as avatar:
        with open("info/tmp.tsv", "w", encoding="utf8") as tmp:
            for item in Collections.avatars:
                avatar.write(item.name)
                avatar.write("\n")
                tmp.write("%s\t%s\n" % (item.name, item.addressableKey[7:]))

    with open("info/tips.txt", "w", encoding="utf8") as f:
        for tip in Tips.tips[0].tips:
            f.write(tip)
            f.write("\n")


def run_catalog_tables(path, logger):
    """新版 APK（约 3.x 起）：曲库 MonoBehaviour 已不在安装包内（改由运行时下载），
    改从 Addressables catalog 推导曲目列表、头像列表等信息。
    注意：定数、画师、谱师、收藏品、tips 不在安装包内，无法提供。"""
    keys, key_to_bundle = catalog.parse_catalog(path)

    songs = {}
    avatars = []
    for key in key_to_bundle:
        if key[:7] == "avatar.":
            avatars.append(key[7:])
        elif key[:14] == "Assets/Tracks/" and key[:15] != "Assets/Tracks/#":
            song_id, _, file_name = key[14:].partition("/")
            songs.setdefault(song_id, set()).add(file_name)

    difficulty = []
    table = []
    for song_id in sorted(songs):
        levels = sorted(songs[song_id])
        diffs = []
        for name in ("Chart_EZ.json", "Chart_HD.json", "Chart_IN.json", "Chart_AT.json"):
            if name in levels:
                diffs.append("-")  # 定数不在安装包内
        difficulty.append([song_id] + diffs)
        # 曲目 id 形如 曲名.曲师.编号
        title = song_id.rsplit(".", 2)[0]
        artist = song_id.rsplit(".", 2)[1] if song_id.count(".") >= 2 else ""
        table.append((song_id, title, artist, "", ""))

    with open("info/difficulty.tsv", "w", encoding="utf8") as f:
        for item in difficulty:
            f.write("\t".join(item))
            f.write("\n")
    with open("info/info.tsv", "w", encoding="utf8") as f:
        for item in table:
            f.write("\t".join(item))
            f.write("\n")

    with open("info/avatar.txt", "w", encoding="utf8") as avatar:
        with open("info/tmp.tsv", "w", encoding="utf8") as tmp:
            for name in sorted(avatars):
                avatar.write(name)
                avatar.write("\n")
                tmp.write("%s\t%s\n" % (name, name))

    logger.info("从 catalog 推导出 %d 首曲目、%d 个头像" % (len(songs), len(avatars)))
    logger.warning("此版本安装包内不含 GameInformation/GetCollectionControl/TipsProvider 数据"
                   "（改由运行时下载），定数/画师/谱师/收藏品/tips 无法导出")


def run(path, logger):
    Tips = None
    GameInformation = None
    Collections = None
    with open("typetree.json") as f:
        typetree = json.load(f)
    try:
        GameInformation, Collections, Tips = run_legacy(path, logger, typetree)
    except Exception as e:
        logger.warning("旧版数据提取失败（%s），改用 catalog 推导" % e)
    if GameInformation and Collections and Tips:
        write_legacy_tables(GameInformation, Collections, Tips, logger)
    else:
        run_catalog_tables(path, logger)


if __name__ == "__main__":
    if len(sys.argv) == 1 and os.path.isdir("/data/"):
        import subprocess
        r = subprocess.run("pm path com.PigeonGames.Phigros",stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,shell=True)
        file_path = r.stdout[8:-1].decode()
    else:
        file_path = sys.argv[1]
    if not os.path.isdir("info"):
        os.mkdir("info")
    run(file_path, init_console_logger())
