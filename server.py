# Import required libraries
import http.server, os
import socketserver
import datetime
import random
import string
import json
import sys

# Configuration
MESSAGES_FILE, USERS_FILE = "messages.json", "users.json"
MESSAGES_MAX = 100
NICK_LENGTH = 8
TOKEN_LENGTH = 16
ENCODING = "utf-8"
AMNESIA = True
PORT = 8080 if len(sys.argv) == 1 else int(sys.argv[1])

# Status strings
NOT_REGISTERED = ("Client not registered.", 403)
REGISTERED = lambda token : ({ # REGISTERED data contains config info for the client
    "nick_length": NICK_LENGTH,
    "encoding": ENCODING,
    "token": token
}, 201)

CHANGE_NICK = ("Nickname changed.", 201)
REJECT_NICK = (f"Nickname is inappropriate, over {NICK_LENGTH} characters long or is taken.", 400)

MESSAGE_CREATED = ("Message created.", 201)

INVALID = ("Invalid request.", 400)
SUCCESS = ("Success.", 200)
ERROR = ("Internal error.", 500)

# Global variables
users: list["StormUser"] = []
messages: list["StormMessage"] = []

def get(l: list[object], attr: str, value: object) -> object | None:
    "Finds the object in `l` where `l[x].attr` is equal to `value`."

    for n in l:
        if n.__getattribute__(attr) == value:
            return n
    return None

def generate(l: int = NICK_LENGTH):
    "Generates a random string (characters and digits) of `l` length."

    return "".join([random.choice(string.ascii_letters + string.digits) for _ in range(0, l)])

def once(l: list[object], runnable: object) -> object:
    """Runs `runnable` until the output of `runnable` is no longer present in
    `l` and returns the resulting value.
    
    Only use this for randomisation and whatnot, otherwise thread-locking!!"""

    o = runnable()
    while o in l:
        o = runnable()
    return o

def time() -> str:
    "Returns the current time as a string."

    return datetime.datetime.now().strftime("%H:%M")

class StormObject:
    "Represents a generic storm JSONifiable object (e.g. users, messages)."

    def __init__(self) -> None:
        pass

    def to_json(self, secure: bool = False) -> dict:
        """Translates the StormObject to a dictionary. If `secure`, remove
        sensitive/authorisation information."""

        data = {}
        for k in self.__dir__():
            if k[0] != "_":
                attr = self.__getattribute__(k)
                if not callable(attr):
                    data[k] = attr
        return data
    
    def from_json(data: dict) -> "StormObject":
        "Translates a dictionary to a StormObject."

        o = StormObject()
        for k, v in data.items():
            o.__setattr__(k, v)
        return o

class StormUser(StormObject):
    "Simply behaves as storage for a user's IP and nickname."
    
    def __init__(self, ip: str, nickname: str, token: str = None) -> None:
        super().__init__()

        self._ip, self.nickname = ip, nickname
        self._token = generate(TOKEN_LENGTH) if token == None else token

    @property
    def ip(self) -> str:
        return self._ip
    
    @property
    def token(self) -> str:
        return self._token
    
    def to_json(self, secure: bool = False) -> dict:
        return {
            "ip": self.ip,
            "nickname": self.nickname,
            "token": None if secure else self.token
        }
    
    def from_json(data: dict) -> StormObject:
        return StormUser(data["ip"], data["nickname"], data.get("token"))
    
class StormMessage(StormObject):
    "A container for a message's content and user."

    def __init__(self, content: str, user: StormUser, time: str) -> None:
        super().__init__()

        self._user, self.content = user, content
        self._time = time

    @property
    def user(self) -> StormUser:
        return self._user
    
    @property
    def time(self) -> str:
        return self._time
    
    def to_json(self, secure: bool = False) -> dict:
        return {
            "user": self.user.to_json(secure),
            "content": self.content,
            "time": self.time
        }
    
    def from_json(data: dict) -> StormObject:
        return StormMessage(
            data["content"],
            get(users, "token", data["user"].get("token")) or get(users, "ip", data["user"]["ip"]),
            data["time"]
        )

class StormHandler(http.server.BaseHTTPRequestHandler):
    "The storm HTTP request handler."

    def __init__(self, request: object,
                client_address: tuple[str, int],
                server: socketserver.BaseServer) -> None:
        super().__init__(request, client_address, server)

    @property
    def address(self) -> str:
        "I made it a property because, I mean, cmon Python standard libs!!!"

        return ":".join([str(x) for x in self.client_address])
    
    @property
    def token(self) -> str | None:
        "The client's token."

        return self.headers.get("Token", "")

    def respond(self, data: bytes | str | dict | list, code: int = 200,
                **headers) -> None:
        "A clean function that runs the boilerplate response code."

        data = json.dumps({
            "status": code,
            "reason": data
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
        user: StormUser = get(users, "token", self.token)
        if user == None:
            return self.respond(*NOT_REGISTERED)
        
        # Give the user the messages
        self.respond([m.to_json(True) for m in messages])

    def do_POST(self) -> None:
        # Register the user if they're not already
        user: StormUser = get(users, "token", self.token)
        if user == None:
            users.append(
                StormUser(self.address,
                    once([u.nickname for u in users], generate)
                )
            )
            return self.respond(*REGISTERED(users[-1].token))
        
        # Add their message, given that it's valid
        data = self.read(True)
        if not isinstance(data, dict):
            return self.respond(*INVALID)

        # Ensure proper request
        content = data.get("content")
        if content == None:
            return self.respond(*INVALID)
        else:
            messages.append(
                StormMessage(content, user, time())
            )
            return self.respond(*MESSAGE_CREATED)
    
    def do_PATCH(self) -> None:
        # Check if the user is registered
        user: StormUser = get(users, "token", self.token)
        if user == None:
            return self.respond(*NOT_REGISTERED)
        
        # Get the patch data
        data = self.read(True)
        if not isinstance(data, dict):
            return self.respond(*INVALID)
        
        # Get the new nickname
        nickname = data.get("nickname")
        if nickname == None or len(nickname) > NICK_LENGTH or nickname in [u.nickname for u in users]:
            return self.respond(*REJECT_NICK)
        else:
            user.nickname = nickname
            return self.respond(*CHANGE_NICK)

# Run the HTTP server
if __name__ == "__main__":
    try:
        # Attempt to load the messages and users
        if not AMNESIA and os.path.isfile(USERS_FILE) and os.path.isfile(MESSAGES_FILE):
            users = [StormUser.from_json(u) for u in json.load(open(USERS_FILE, "r"))]
            messages = [StormMessage.from_json(m) for m in json.load(open(MESSAGES_FILE, "r"))]
        with socketserver.TCPServer(("", PORT), StormHandler) as httpd:
            print(f"Serving at port '{PORT}'.")
            httpd.serve_forever()
    except KeyboardInterrupt: # Allow graceful exit
        # Write the messages and users to files
        if not AMNESIA:
            json.dump([m.to_json(False) for m in messages], open(MESSAGES_FILE, "w"), indent=4)
            json.dump([u.to_json(False) for u in users], open(USERS_FILE, "w"), indent=4)
