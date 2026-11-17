@echo off
title Photo/video requests - watching
cd /d "%~dp0"
echo Watching https://photo-video-studio-gamma.vercel.app for new requests.
echo New requests are downloaded to "..\client-requests". Keep this window open.
echo.
node local\agent.mjs watch
pause
