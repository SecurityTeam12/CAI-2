import asyncio
import websockets
import json

SERVER_URI = "ws://localhost:8765"
TEST_ROUTE = "Andalucia CastillaLaMancha Madrid Aragon"
INVALID_ROUTE = "Andalucia123 CastillaLaMancha Madrid Aragon"
LONG_ROUTE = "A" * 61

async def test_connection():
    async with websockets.connect(SERVER_URI) as websocket:
        await websocket.send(TEST_ROUTE)
        response = await websocket.recv()
        print(f"Conexión establecida: {response}")

async def test_invalid_route():
    async with websockets.connect(SERVER_URI) as websocket:
        await websocket.send(INVALID_ROUTE)
        response = await websocket.recv()
        print(f"Respuesta a ruta inválida: {response}")

async def test_long_route():
    async with websockets.connect(SERVER_URI) as websocket:
        await websocket.send(LONG_ROUTE)
        response = await websocket.recv()
        print(f"Respuesta a ruta demasiado larga: {response}")

async def test_message_reception():
    async with websockets.connect(SERVER_URI) as websocket:
        await websocket.send(TEST_ROUTE)
        response = await websocket.recv()
        print(f"Conexión establecida: {response}")
        try:
            while True:
                message = await websocket.recv()
                print(f"Mensaje recibido: {message}")
        except websockets.ConnectionClosed:
            print("Conexión cerrada por el servidor.")

async def test_reconnection():
    async with websockets.connect(SERVER_URI) as websocket:
        await websocket.send(TEST_ROUTE)
        response = await websocket.recv()
        print(f"Conexión establecida: {response}")
        await websocket.close()
        print("Conexión cerrada, intentando reconectar...")
        await asyncio.sleep(5)
        async with websockets.connect(SERVER_URI) as websocket:
            await websocket.send(TEST_ROUTE)
            response = await websocket.recv()
            print(f"Reconexión establecida: {response}")

async def main():
    print("Probando conexión...")
    await test_connection()
    print("\nProbando ruta inválida...")
    await test_invalid_route()
    print("\nProbando ruta demasiado larga...")
    await test_long_route()
    print("\nProbando reconexión...")
    await test_reconnection()
    print("\nProbando recepción de mensajes...")
    await test_message_reception()


if __name__ == "__main__":
    asyncio.run(main())