#!/bin/bash
# Starts both Django (port 8000) and React dev server (port 5173)

echo "Starting Breathe ESG..."

# Activate venv and start Django
cd "$(dirname "$0")"
source venv/Scripts/activate

echo "Starting Django API on http://localhost:8000 ..."
python manage.py runserver 8000 &
DJANGO_PID=$!

echo "Starting React frontend on http://localhost:5173 ..."
cd frontend
export PATH="$PATH:/c/Program Files/nodejs"
npm run dev &
REACT_PID=$!

echo ""
echo "=========================================="
echo "  Breathe ESG is running!"
echo "  Frontend:  http://localhost:5173"
echo "  API:       http://localhost:8000/api/"
echo "  Admin:     http://localhost:8000/admin/"
echo "  Login:     analyst / analyst123"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop both servers."

trap "kill $DJANGO_PID $REACT_PID 2>/dev/null; exit" INT TERM
wait
