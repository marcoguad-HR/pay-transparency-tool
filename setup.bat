@echo off
REM setup.bat — Setup automatico per Pay Transparency Tool (Windows)
REM
REM Cosa fa:
REM 1. Crea un virtual environment Python (se non esiste)
REM 2. Installa le dipendenze da requirements.txt
REM 3. Verifica che tutti gli import critici funzionino
REM 4. Pre-scarica il modello FastEmbed (~91 MB, solo al primo avvio)
REM 5. Ricostruisce il vector database se mancante (ingestion PDF)
REM
REM Flags:
REM   /clean    Ricrea il venv da zero (nuclear option per problemi di dipendenze)
REM
REM Uso:
REM   setup.bat          &REM Setup normale
REM   setup.bat /clean   &REM Ricrea venv da zero

set CLEAN=false
if "%1"=="/clean" set CLEAN=true

echo === Pay Transparency Tool — Setup ===
echo.

REM --- 1. Virtual environment ---
if "%CLEAN%"=="true" (
    if exist ".venv" (
        echo Flag /clean: rimozione venv esistente...
        rmdir /s /q .venv
        echo Venv rimosso.
    )
)

if not exist ".venv" (
    echo Creazione virtual environment...
    python -m venv .venv
    echo Virtual environment creato in .venv\
) else (
    echo Virtual environment esistente trovato.
)

call .venv\Scripts\activate.bat

REM --- 2. Dipendenze ---
echo.
echo Installazione dipendenze...
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo Dipendenze installate.

REM --- 3. Verifica import critici ---
echo.
echo Verifica import critici...
python scripts\verify_imports.py
if errorlevel 1 (
    echo.
    echo ERRORE: Verifica import fallita. Prova: setup.bat /clean
    exit /b 1
)

REM --- 4. Pre-download modello FastEmbed ---
echo.
echo Download modello ML (solo al primo avvio, ~91 MB)...
python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='sentence-transformers/all-MiniLM-L6-v2')"
echo Modello pronto.

REM --- 5. Ricostruzione vector database ---
echo.
if not exist "data\vectordb\collection\eu_directive_2023_970" (
    echo Vector database non trovato. Ricostruzione dal PDF...
    if exist "data\documents\CELEX_32023L0970_EN_TXT.pdf" (
        python main.py ingest "data\documents\CELEX_32023L0970_EN_TXT.pdf" --reset
        echo Vector database ricostruito.
    ) else (
        echo ATTENZIONE: PDF non trovato in data\documents\CELEX_32023L0970_EN_TXT.pdf
        echo Scaricalo con:  python scripts\download_directive.py
        echo Poi esegui:     python main.py ingest data\documents\CELEX_32023L0970_EN_TXT.pdf --reset
    )
) else (
    echo Vector database esistente. Ricostruzione saltata.
)

REM --- Fine ---
echo.
echo === Setup completato! ===
echo.
echo Per iniziare:
echo   .venv\Scripts\activate.bat
echo   python main.py agent          # CLI interattiva
echo   uvicorn app:app --reload      # Web frontend
echo.
echo Se qualcosa non funziona:
echo   setup.bat /clean              # Ricrea il venv da zero
