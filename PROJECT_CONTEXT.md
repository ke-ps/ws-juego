# Connect 4 WebSocket Game

## Architecture

Backend:
- FastAPI
- WebSocket endpoint: /ws/pvp

Frontend:
- Angular
- Standalone Components
- Signals

## WebSocket Protocol

Server -> Client
{
  type: string,
  data: object
}

Client -> Server
{
  type: string,
  payload: object
}

## Server Messages

- connected
- waiting
- game_start
- turn
- move
- invalid_move
- game_over
- opponent_disconnected
- error

## Client Messages

Move:

{
  type: "move",
  payload: {
    col: number
  }
}

## Rules

- Do not modify the protocol.
- Do not rename message types.
- Do not change payload structure.
- Frontend must adapt to backend, never the opposite.

## Current Progress

✅ Backend complete
✅ WebSocket service connected
✅ Message typings implemented
⏳ Board UI in progress
⏳ Game interaction pending