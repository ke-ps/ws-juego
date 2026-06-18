"""Script para iniciar servidor y ejecutar test."""
import subprocess
import sys
import time
import asyncio
import os

# Change to backend directory
os.chdir(os.path.dirname(__file__))

# Start server
print("Iniciando servidor...")
server = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

# Wait for server to start
time.sleep(3)

# Check if server is running
if server.poll() is not None:
    print("Server failed to start:")
    print(server.stdout.read())
    sys.exit(1)

print("Servidor iniciado, esperando mensajes...")

# Print server output in a separate thread-like way
def read_output():
    try:
        for line in iter(server.stdout.readline, ''):
            if line:
                print(f"[SERVER] {line.rstrip()}")
    except:
        pass

import threading
t = threading.Thread(target=read_output, daemon=True)
t.start()

# Run the test
print("\nEjecutando test...")
result = subprocess.run(
    [sys.executable, "test_game_logic.py"],
    capture_output=True,
    text=True
)

print("\n" + "=" * 60)
print("OUTPUT DEL TEST:")
print("=" * 60)
print(result.stdout)
if result.stderr:
    print("STDERR:")
    print(result.stderr)
print("=" * 60)

# Kill server
server.terminate()
server.wait()

sys.exit(result.returncode)
