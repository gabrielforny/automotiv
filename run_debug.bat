@echo off
cd /d %~dp0
call .venv\Scripts\activate
python main.py --excel "data\solicitacao_orcamento_exemplo.xlsx" --dry-run
pause
