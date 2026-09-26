"""Addressables catalog 解析（兼容 3.x 旧格式与 4.0.0 起的新格式）。

catalog.json 里 m_KeyDataString / m_EntryDataString 为 base64 的二进制：
  KeyDataString:  [int32 数量] { [1字节标记][标记0/1: int32长度+数据(ASCII/UTF-16LE)] 或 [标记4: int32值] }
  EntryDataString: [int32 数量] { 28字节 = iid, provider, depidx, X, Y, primaryKey, W }
每个资源 key 通过条目的 depidx 指向所属 bundle 的 key；bundle 条目的 iid 指向
m_InternalIds 里的真实文件名（4.0.0 起 bundle key 与实际文件名不同，必须经 iid 换算）。
"""
import base64
import json
import os
import struct
from zipfile import ZipFile

# 4.0.0 起部分 bundle 使用 AES-256-CBC 整包加密（C9SecretAssetBundleProvider）
ENCRYPTED_MAGIC = bytes.fromhex("47a9c97dbeefc3e4")


def parse_keys(key_data_string):
    data = base64.b64decode(key_data_string)
    count, = struct.unpack_from("<i", data, 0)
    offset = 4
    keys = []
    for _ in range(count):
        marker = data[offset]
        offset += 1
        length, = struct.unpack_from("<i", data, offset)
        offset += 4
        if marker == 4:
            keys.append(("int", length))
        else:
            raw = data[offset:offset + length]
            offset += length
            if marker == 0:
                keys.append(raw.decode("latin-1"))
            elif marker == 1:
                keys.append(raw.decode("utf-16-le", "replace"))
            else:
                raise ValueError("未知的 key 标记 %#x @ %#x" % (marker, offset))
    return keys


def parse_entries(entry_data_string):
    data = base64.b64decode(entry_data_string)
    count, = struct.unpack_from("<i", data, 0)
    entries = []
    for i in range(count):
        entries.append(struct.unpack_from("<7i", data, 4 + 28 * i))
    return entries


def parse_catalog(apk_path):
    """返回 (keys, key->bundle真实文件名 的映射)。"""
    with ZipFile(apk_path) as apk:
        with apk.open("assets/aa/catalog.json") as f:
            data = json.load(f)

    keys = parse_keys(data["m_KeyDataString"])
    entries = parse_entries(data["m_EntryDataString"])
    internal_ids = data["m_InternalIds"]

    # bundle key -> APK 里的真实文件名
    bundle_key_to_real = {}
    for iid, _prov, _dep, _x, _y, pk, _w in entries:
        key = keys[pk] if 0 <= pk < len(keys) else None
        if isinstance(key, str) and key.endswith(".bundle") and 0 <= iid < len(internal_ids):
            name = os.path.basename(internal_ids[iid].split("/")[-1])
            if name.endswith(".bundle"):
                bundle_key_to_real[key] = name

    # 资源 key -> 所属 bundle 的真实文件名
    key_to_bundle = {}
    for _iid, _prov, dep, _x, _y, pk, _w in entries:
        key = keys[pk] if 0 <= pk < len(keys) else None
        dep_key = keys[dep] if 0 <= dep < len(keys) else None
        if isinstance(key, str) and isinstance(dep_key, str) and dep_key.endswith(".bundle"):
            key_to_bundle[key] = bundle_key_to_real.get(dep_key, dep_key)

    return keys, key_to_bundle


def decrypt_bundle(data, password):
    """按 C9SecretAssetBundleProvider 的方式解密 bundle：
    key = SHA512(UTF8(password))[0:32]，IV = SHA512(...)[32:48]，AES-256-CBC。"""
    import hashlib
    from Crypto.Cipher import AES
    sha = hashlib.sha512(password.encode("utf-8")).digest()
    plain = AES.new(sha[:32], AES.MODE_CBC, sha[32:48]).decrypt(data)
    pad = plain[-1]
    if 1 <= pad <= 16 and plain[-pad:] == bytes([pad]) * pad:
        plain = plain[:-pad]
    return plain
