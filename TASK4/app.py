import asyncio
import websockets
import json

# Store the connected clients and rooms
clients = {}
rooms = {}

async def register_user(websocket, username):
    """Register a new user and add them to the clients list"""
    clients[websocket] = {'username': username, 'room': None}
    print(f"{username} connected")

async def unregister_user(websocket):
    """Remove a user when they disconnect"""
    user = clients.pop(websocket, None)
    if user and user['room']:
        room = user['room']
        rooms[room].remove(websocket)
        await broadcast_room_message(room, f"[System] {user['username']} has left the room.")
        await update_user_list(room)

async def join_room(websocket, username, room_name):
    """Add a user to a room and notify others in the room"""
    if room_name not in rooms:
        rooms[room_name] = []
    
    clients[websocket]['room'] = room_name
    rooms[room_name].append(websocket)
    
    await broadcast_room_message(room_name, f"[System] {username} has joined the room.")
    await update_user_list(room_name)

async def send_room_message(websocket, message):
    """Send a message to the current room"""
    user = clients[websocket]
    room_name = user['room']
    if room_name:
        username = user['username']
        await broadcast_room_message(room_name, f"[{username}] {message}")

async def broadcast_room_message(room_name, message):
    """Send a message to all users in the room"""
    if room_name in rooms:
        for client in rooms[room_name]:
            await client.send(json.dumps({"type": "message", "room": room_name, "from": "System", "message": message}))

async def send_private_message(websocket, recipient_username, message):
    """Send a private message to another user"""
    recipient = None
    for client, data in clients.items():
        if data['username'] == recipient_username:
            recipient = client
            break
    if recipient:
        await recipient.send(json.dumps({
            "type": "private_message",
            "from": clients[websocket]['username'],
            "message": message
        }))
    else:
        await websocket.send(json.dumps({"type": "error", "message": "User not found"}))

async def update_user_list(room_name):
    """Update the list of users in the room and send it to all users"""
    if room_name in rooms:
        users = [clients[client]['username'] for client in rooms[room_name]]
        for client in rooms[room_name]:
            await client.send(json.dumps({"type": "user_list", "room": room_name, "users": users}))

async def handle_typing(websocket):
    """Notify others in the room when a user is typing"""
    user = clients[websocket]
    room_name = user['room']
    if room_name:
        username = user['username']
        await broadcast_room_message(room_name, {"type": "typing", "username": username})

async def websocket_handler(websocket, path):
    """Handle incoming WebSocket connections and messages"""
    try:
        # Initial registration
        message = await websocket.recv()
        data = json.loads(message)
        username = data['username']
        await register_user(websocket, username)
        
        # Main loop to handle room joining, messages, and typing
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            action = data['action']
            
            if action == 'join_room':
                room_name = data['room_name']
                await join_room(websocket, username, room_name)
            elif action == 'send_room_message':
                message = data['message']
                await send_room_message(websocket, message)
            elif action == 'send_private_message':
                recipient_username = data['recipient']
                message = data['message']
                await send_private_message(websocket, recipient_username, message)
            elif action == 'typing':
                await handle_typing(websocket)

    except websockets.exceptions.ConnectionClosed as e:
        print(f"Connection closed: {e}")
    finally:
        await unregister_user(websocket)

async def main():
    """Start the WebSocket server"""
    server = await websockets.serve(websocket_handler, 'localhost', 6789)
    print("Server started on ws://localhost:6789")
    await server.wait_closed()

if __name__ == '__main__':
    asyncio.run(main())
