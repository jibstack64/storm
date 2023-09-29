# Import required libraries
import http.server, os
import socketserver
import subprocess
import random
import socket
import string
import json

# Configuration
NICK_LENGTH = 8
ENCODING = "utf-8"
PORT = 8080

# Status strings
NOT_REGISTERED = ("Client not registered.", 403)
REGISTERED = ({ # REGISTERED data contains config info for the client
    "nick_length": NICK_LENGTH,
    "encoding": ENCODING
}, 201)

CHANGE_NICK = ("Nickname changed.", 201)
REJECT_NICK = (f"Nickname is inappropriate or over {NICK_LENGTH} characters long.", 400)

MESSAGE_CREATED = ("Message created.", 201)

INVALID = ("Invalid request.", 400)
SUCCESS = ("Success.", 200)
ERROR = ("Internal error.", 500)

def get(l: list[object], attr: str, value: object) -> object | None:
    "Finds the object in `l` where `l[x].attr` is equal to `value`."

    for n in l:
        if n.__getattribute__(attr) == value:
            return n
    return None

def generate(l: int = NICK_LENGTH):
    "Generates a random string (characters and digits) of `l` length."

    return "".join([random.choice(string.printable.strip(string.whitespace)) for _ in range(0, l)])

def once(l: list[object], runnable: object) -> object:
    """Runs `runnable` until the output of `runnable` is no longer present in
    `l` and returns the resulting value.
    
    Only use this for randomisation and whatnot, otherwise thread-locking!!"""

    o = runnable()
    while o in l:
        o = runnable()
    return o

class StormObject:
    "Represents a generic storm JSONifiable object (e.g. users, messages)."

    def __init__(self) -> None:
        pass

    def to_json(self) -> dict:
        "Translates the StormObject to a dictionary."

        data = {}
        for k in self.__dir__():
            if k[0] != "_":
                attr = self.__getattribute__(k)
                if not callable(attr):
                    data[k] = attr
        return data

class StormUser(StormObject):
    "Simply behaves as storage for a user's IP and nickname."
    
    def __init__(self, ip: str, nickname: str, messages: int) -> None:
        super().__init__()

        self._ip, self.nickname = ip, nickname
        self.has = messages

    @property
    def ip(self) -> str:
        return self._ip
    
    def to_json(self) -> dict:
        return {
            "ip": self.ip,
            "nickname": self.nickname
        }
    
class StormMessage(StormObject):
    "A container for a message's content and user."

    def __init__(self, content: str, user: StormUser) -> None:
        super().__init__()

        self._user, self.content = user, content

    @property
    def user(self) -> StormUser:
        return self._user
    
    def to_json(self) -> dict:
        return {
            "user": self.user.to_json(),
            "content": self.content
        }

class StormHandler(http.server.BaseHTTPRequestHandler):
    "The storm HTTP request handler."

    def __init__(self, request: object,
                client_address: tuple[str, int],
                server: socketserver.BaseServer) -> None:
        super().__init__(request, client_address, server)

        self.users: list[StormUser] = []
        self.messages: list[StormMessage] = []

        # A few small utilities
        self.is_registered = lambda ip : True in [u.ip == ip for u in self.users]

    @property
    def address_string(self) -> str:
        "I made it a property because, I mean, cmon Python standard libs!!!"

        return super().address_string()

    def respond(self, data: bytes | str | dict | list, code: int = 200,
                **headers) -> None:
        "A clean function that runs the boilerplate response code."

        data = json.dumps({
            "status": code,
            "message": data
        } if type(data) in [str, bytes] else data)

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        for h, v in headers.items():
            self.send_header(h, v)
        self.end_headers()
        self.wfile.write(bytes(data, ENCODING))

    def read(self, is_json: bool = False) -> str | dict | list:
        "Gets and returns the POST data."

        data = self.rfile.read(int(self.headers["Content-Length"])).decode(ENCODING)
        return json.loads(data) if is_json else data

    def do_GET(self) -> None:
        # Check if the user is registered
        user: StormUser = get(self.users, "ip", self.address_string)
        if user == None:
            return self.respond(*NOT_REGISTERED)
        
        # Give the user the messages
        self.respond([m.to_json() for m in self.messages[user.has:]])
        user.has = len(self.messages)

    def do_POST(self) -> None:
        # Register the user if they're not already
        user: StormUser = get(self.users, "ip", self.address_string)
        if user == None:
            self.users.append(
                StormUser(self.address_string,
                    once([u.nickname for u in self.users], generate),
                    len(self.messages)
                )
            )
            return self.respond(*REGISTERED)
        
        # Add their message, given that it's valid
        data = self.read(True)
        if not isinstance(data, dict):
            return self.respond(*INVALID)

        # Ensure proper request
        content = data.get("content")
        if content == None:
            return self.respond(*INVALID)
        else:
            self.messages.append(
                StormMessage(content, user)
            )
            return self.respond(*MESSAGE_CREATED)
    
    def do_PATCH(self) -> None:
        # Check if the user is registered
        user: StormUser = get(self.users, "ip", self.address_string)
        if user == None:
            return self.respond(*NOT_REGISTERED)
        
        # Get the patch data
        data = self.read(True)
        if not isinstance(data, dict):
            return self.respond(*INVALID)
        
        # Get the new nickname
        nickname = data.get("nickname")
        if nickname == None or len(nickname) > NICK_LENGTH:
            return self.respond(*REJECT_NICK)
        else:
            user.nickname = nickname
            return self.respond(*CHANGE_NICK)

# Run the HTTP server
if __name__ == "__main__":
    try:
        with socketserver.TCPServer(("", PORT), StormHandler) as httpd:
            print(f"Serving at port '{PORT}'.")
            httpd.serve_forever()
    except KeyboardInterrupt: # Allow graceful exit
        pass
