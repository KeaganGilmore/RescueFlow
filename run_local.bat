@echo off
echo Starting RescueFlow Local Server...
echo Open your browser to: http://localhost:8000
python -m http.server --directory docs
pause
