@ECHO OFF
for /L %%n in (1,1,1) do call :CopyFiles %%n
goto End

:CopyFiles
	set fname=_blockchain%1
	set /A port = 24130 + %1
	rmdir /S /Q "%fname%"
	mkdir "%fname%"
	for /f %%a in ('dir /b') do call :CopyDir %%a
	set node_type=payload_node
	if %1%==2 (
	    set node_type=miner_only
	)
	start "Thread for port %port%" /b "cmd /c .\venv\Scripts\python.exe %fname%/main.py %node_type% %port%"

goto :eof

:CopyDir
	set filename=%1
	set filext=%filename:~0,1%
	if "%filext%" neq "." ( if "%filext%" neq "_" ( if "%filename%" neq "venv" ( if "%filename%" neq "start.bat" (
		xcopy "%filename%" "%fname%/%filename%" /E /H /C /I
		copy /Y "%filename%" "%fname%/%filename%"
	))))
goto :eof

:End