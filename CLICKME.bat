@echo off
chcp 65001 >nul
rem ============================================================
rem  Phigros 拆包工具 一键流程
rem  用法：把 Phigros 安装包改名为 base.apk 放进本目录，双击本文件
rem  流程：装依赖 → 导出信息表 → 提取全部资源 → ogg 转 wav →（可选）批量打包 .pez
rem  环境要求：Python 3.10~3.12（脚本会自动回退 py -3.12）、ffmpeg（转码用）
rem ============================================================

if not exist base.apk (
    echo [错误] 未找到 base.apk —— 请先把 Phigros 安装包改名为 base.apk 放到本目录。
    pause
    exit /b 1
)

rem 选择可用的 Python（默认 python 缺 UnityPy 时回退 py -3.12）
set PY=python
python -c "import UnityPy" >nul 2>&1
if errorlevel 1 (
    py -3.12 -c "import UnityPy" >nul 2>&1
    if errorlevel 1 (
        echo [提示] 未找到带依赖的 Python，先尝试安装依赖...
        python -m pip install -r requirements.txt
    ) else (
        set PY=py -3.12
    )
)
echo 使用解释器: %PY%

%PY% -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo.
echo [1/4] 导出曲目信息表...
%PY% gameInformation.py base.apk || goto :fail
echo.
echo [2/4] 提取全部资源（谱面/曲绘/音频/头像，约 1~3 分钟）...
%PY% resource.py base.apk || goto :fail
echo.
echo [3/4] ogg 转 wav（保留 ogg 源）...
%PY% ogg2wav.py || goto :fail
echo.
set /p PACK=是否现在批量打包 .pez 到 phira\ 目录？[y/N]:
if /i "%PACK%"=="y" (
    %PY% phira.py || goto :fail
) else (
    echo 跳过批量打包。之后可随时运行: python phira.py（批量）或 python phira_gui.py（选曲打包）
)

echo.
echo ============================================================
echo 全部完成！产出目录：
echo   chart\          谱面 JSON     music_ogg\   原始音频 ogg
echo   music_wav\      无损 wav      illustration*\  曲绘
echo   avatar\         头像          info\        曲目信息表
echo   phira\          （若已打包）.pez 文件
echo ============================================================
pause
exit /b 0

:fail
echo.
echo [错误] 流程中断。若为 Python 版本问题（^>=3.13 无 UnityPy），
echo        请安装 Python 3.12 后重试，或把本文件中的 python 改为 py -3.12。
pause
exit /b 1
