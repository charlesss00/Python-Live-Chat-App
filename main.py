from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, emit, SocketIO
import random
from string import ascii_uppercase
import uuid 

app = Flask(__name__)
app.config["SECRET_KEY"] = "hjhjsdahhds"
socketio = SocketIO(app)

rooms = {}

def generate_unique_code(length):
    while True:
        code = "".join(random.choice(ascii_uppercase) for _ in range(length))
        if code not in rooms:
            break
    return code

@app.route("/", methods=["POST", "GET"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)

        if join != False and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)
        
        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)
        
        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("home.html")

@app.route("/room")
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))
    return render_template("room.html", code=room, messages=rooms[room]["messages"])

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return
    
    message_id = str(uuid.uuid4()) 
    content = {
        "messageId": message_id,
        "name": session.get("name"),
        "message": data["data"],
        "is_edited": False
    }
    rooms[room]["messages"].append(content)
    send(content, to=room)
    print(f"{session.get('name')} said: {data['data']}")

@socketio.on("update_message")
def update_message(data):
    room = session.get("room")
    if room not in rooms:
        return
    
    message_id = data.get("messageId")
    new_message = data.get("newMessage")
    if not message_id or not new_message:
        return

    for msg in rooms[room]["messages"]:
        if msg["messageId"] == message_id:
            msg["message"] = new_message
            msg["is_edited"] = True
            emit("message_updated", msg, to=room)
            print(f"Message {message_id} updated in room {room}")
            break

@socketio.on("delete_message")
def delete_message(data):
    room = session.get("room")
    if room not in rooms:
        return
    
    message_id = data.get("messageId")
    if not message_id:
        return

    messages = rooms[room]["messages"]
    for i, msg in enumerate(messages):
        if msg["messageId"] == message_id:
            del messages[i]
            emit("message_deleted", {"messageId": message_id}, to=room)
            print(f"Message {message_id} deleted from room {room}")
            break

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    
    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
    
    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")

if __name__ == "__main__":
    socketio.run(app, debug=True)
