import os
from pydub import AudioSegment

def convert_ogg_to_wav(input_dir, output_dir=None, remove_original=False):
    """
    将 input_dir 下所有 .ogg 文件转换为 .wav

    参数:
        input_dir: 包含 .ogg 文件的文件夹路径
        output_dir: 输出文件夹路径（默认与 input_dir 相同）
        remove_original: 是否删除原始文件（默认 False）
    """

    if output_dir is None:
        output_dir = input_dir

    # 确保输出文件夹存在
    os.makedirs(output_dir, exist_ok=True)

    # 遍历输入文件夹
    for filename in os.listdir(input_dir):
        if filename.lower().endswith('.ogg'):
            ogg_path = os.path.join(input_dir, filename)
            wav_name = os.path.splitext(filename)[0] + '.wav'
            wav_path = os.path.join(output_dir, wav_name)

            try:
                # 读取 ogg 并导出为 wav
                audio = AudioSegment.from_ogg(ogg_path)
                audio.export(wav_path, format='wav')
                print(f"转换成功: {ogg_path} -> {wav_path}")

                if remove_original:
                    os.remove(ogg_path)
                    print(f"已删除原始文件: {ogg_path}")
            except Exception as e:
                print(f"转换失败 {ogg_path}: {e}")

if __name__ == "__main__":
    # 将 music 与 c9s 文件夹下的 ogg 全部转成 wav
    for folder in ("./music", "./c9s"):
        if os.path.isdir(folder):
            convert_ogg_to_wav(folder, folder, True)
