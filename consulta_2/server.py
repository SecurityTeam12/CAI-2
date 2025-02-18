import asyncio
import random
import uuid
import websockets
import json
import re

connected_clients = {}
clients_lock = asyncio.Lock()

undelivered_messages = {}
sent_messages = set()
MAX_CONNECTIONS = 100
MAX_MESSAGE_SIZE = 1024 
MAX_ROUTE_LENGTH = 60
HEARTBEAT_INTERVAL = 10
HEARTBEAT_TIMEOUT = 5



def create_traffic_message(active, carretera, tramo, motivo, estado):
    return {
        "event_id": str(uuid.uuid4()),
        "activo": active,
        "carretera": carretera,
        "tramo_afectado": tramo,
        "motivo": motivo,
        "estado": estado
    }

async def send_message(websocket, message):
    await websocket.send(message)

async def notify_clients(message, route):
    async with clients_lock:
        for client_info in connected_clients.items():
            client_route, message_queue = client_info
            if route.split() == client_route and message not in sent_messages:
                event_id = json.loads(message).get("event_id")
                sent_messages.add(event_id)
                await message_queue.put(message)

async def handle_connection(websocket, active=False):
    client_id = websocket.remote_address[0]
    try:
        message_queue = asyncio.Queue()
        
        async def message_sender():
            while True:
                message = await message_queue.get()
                try:
                    await send_message(websocket, message)
                except Exception as e:
                    print(f"Error sending message to {websocket}: {e}")
                    
                    if client_id not in undelivered_messages:
                        undelivered_messages[client_id] = []
                        
                    undelivered_messages[client_id].append(message)
                    await websocket.close()
                    break
        
        async def heartbeat(websocket, client_id):
            while True:
                try:
                    pong_waiter = await websocket.ping()
                    await asyncio.wait_for(pong_waiter, timeout=HEARTBEAT_TIMEOUT)
                    await asyncio.sleep(HEARTBEAT_INTERVAL)
                except asyncio.TimeoutError:
                    print(f"Heartbeat timeout for {client_id}")
                    await websocket.close()
                    break

        sender_task = asyncio.create_task(message_sender())
        heartbeat_task = asyncio.create_task(heartbeat(websocket, client_id))
        
        if client_id in undelivered_messages:
            for message in undelivered_messages[client_id]:
                await message_queue.put(message)
            del undelivered_messages[client_id]
            
        if len(connected_clients) >= MAX_CONNECTIONS:
            await websocket.send("Servidor lleno.")
            await websocket.close()
            return

        initial_message = await websocket.recv()
        if len(initial_message) > MAX_MESSAGE_SIZE:
            raise ValueError("Mensaje demasiado largo.")
        
        def validate_route(route):
            if len(route) > MAX_ROUTE_LENGTH:
                raise ValueError("La ruta es demasiado larga.")
            if not re.match(r'^[a-zA-Z\s]+$', route):
                raise ValueError("La ruta contiene caracteres no permitidos.")
            return route
        
        route = validate_route(initial_message)
        
        async with clients_lock:
            connected_clients[websocket] = (route.split(), message_queue)

        await websocket.send("Conexión establecida. Monitoreando cortes en tu ruta.")

        boolean_activation = True #Just for testing
        while True:
            await asyncio.sleep(5)
            message = create_traffic_message(boolean_activation, "A-4", "Km 127 al 135", "Obras en la vía", "Tránsito interrumpido")
            
            event_id = message.get("event_id")
            if active != message.get("activo") and event_id not in sent_messages:
                await notify_clients(json.dumps(message), route)
                
                
                
                active = message.get("activo")
            boolean_activation = not boolean_activation
            
            
            
    except websockets.exceptions.ConnectionClosed:
        print("Conexión cerrada")
    except ValueError as e:
        await websocket.send(f"Error: {e}")
    finally:
        async with clients_lock:
            connected_clients.pop(websocket, None)
        
async def main():
    async with websockets.serve(handle_connection, "localhost", 8765):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
