@echo off
rem 需要 Python 3.10~3.12（UnityPy 1.10.x 无 3.13+ 轮子）与 requirements.txt 依赖
rem 若默认 python 版本过高，请改用：py -3.12
python -m pip install -r requirements.txt
python gameInformation.py base.apk
python resource.py base.apk
python ogg2wav.py
pause
