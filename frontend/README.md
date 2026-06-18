# WS Juego - Connect 4 WebSocket

Juego multijugador de Conecta 4 desarrollado con:

* Backend: FastAPI
* Frontend: Angular
* Comunicación en tiempo real mediante WebSockets

## Estructura del proyecto


ws-juego/
├── backend/
├── frontend/
├── PROJECT_CONTEXT.md
└── README.md


## Requisitos

* Python 3.12+
* Node.js 22+
* Angular CLI

## Ejecutar Backend


cd backend

pip install -r requirements.txt

uvicorn main:app --reload


Backend disponible en:


http://localhost:8000


## Ejecutar Frontend

cd frontend

npm install

ng serve

Frontend disponible en:

http://localhost:4200

## Tecnologías

### Backend

* FastAPI
* WebSockets
* Python

### Frontend

* Angular
* TypeScript
* Signals

## Estado del proyecto

### Backend

* Sistema de partidas
* Gestión de turnos
* WebSockets
* Validación de movimientos

### Frontend

* Conexión WebSocket
* Tipado de mensajes
* Interfaz en desarrollo

## Documentación

* `frontend/AGENTS.md` → reglas para asistentes IA
* `PROJECT_CONTEXT.md` → contexto funcional del proyecto
