@echo off
rem 需要 Python3 与 requirements.txt 中的依赖（UnityPy / fsb5 / pydub / pycryptodome）
pip install -r requirements.txt
python gameInformation.py base.apk
python resource.py base.apk
python ogg2wav.py
pause
