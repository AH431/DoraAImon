@echo off
:: 切換到專案目錄
cd /d "C:\Users\archi\OneDrive\Desktop\DoraAImon"

echo 正在啟動 DoraAImon 智慧助教...
echo 如果啟動有問題，請查看同目錄下的 error.log 檔案。

:: 啟動 Python 程式，並將錯誤輸出到 error.log
python app.py 2> error.log

:: 如果啟動失敗，顯示錯誤訊息並等待人工確認
if %errorlevel% neq 0 (
    echo.
    echo ==========================================================
    echo [錯誤] 程式執行失敗！
    echo 錯誤詳細資訊已儲存至 error.log，請打開該檔案查看。
    echo ==========================================================
    pause
)
