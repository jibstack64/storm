# Import required libraries
import tkinter.messagebox as msg
import urllib.request as request
import urllib.error as ulerror
import tkinter as tk
import subprocess
import threading
import atexit
import time
import json
import os

def screen_geometry() -> tuple[int, int]:
    "Calculates and returns the screen's width and height."

    root = tk.Tk()
    root.update_idletasks()
    root.attributes("-fullscreen", True)
    root.state("iconic")
    geometry = (root.winfo_width(), root.winfo_height())
    root.destroy()
    return geometry

def scale(n: int | str | tuple, p: str | None = "x") -> int | str | dict:
    "Scales `n` (a set of dimensions, scale, or other) based on the screen dimensions."

    t = type(n)
    if t == int:
        return int(round(n * (SCALE[0] if p == "x" else SCALE[1])))
    elif t == str:
        x, y, = n.split("x")
        return "x".join([str(int(round(int(x) * SCALE[0]))),
                        str(int(round(int(y) * SCALE[1])))])
    else:
        # For kwargs!! Cus I'm nice neat like that
        return {
            "x": int(round(n[0] * SCALE[0])),
            "y": int(round(n[1] * SCALE[1]))
        }
    
def run(command: str | tuple) -> int | str:
    """Runs `command`. Returns the code that the program provides, or the output
    if retrievable."""

    output = None
    try:
        output = subprocess.run(
            command if isinstance(command, tuple) else command.split(" "),
            stdout=subprocess.PIPE, text=True
        ).stdout
    except:
        output = os.system(command)
    return output

class Popup:
    "Houses functions that create simple popup messages."

    # general popups

    def error(message: str = "An error occured.", fatal: bool = False) -> None:
        msg.showerror("Error", message)
        if fatal:
            exit(1)

    def warning(message: str = "This may create errors.") -> None:
        msg.showwarning("Warning", message)

    def info(title: str, message: str) -> None:
        msg.showinfo(title, message)

    # conditional popups

    def yes_or_no(message: str, cancel: bool = False) -> bool | None:
        return msg.askyesnocancel(
            "Question", message
        ) if cancel else msg.askyesno(
            "Question", message
        )
    
    def proceed(message: str) -> bool:
        return msg.askokcancel("Proceed", message)
    
    # (Same as yes_or_no)
    #def question(message: str) -> str:
    #    return msg.askquestion("Question", message)


class StormClient:
    "Manages HTTP requests to the storm server."
    
    def __init__(self, ip: str, port: int) -> None:
        self._ip, self._port = ip, port
        self._encoding, self._nick_length = "utf-8", 8
        self._token = ""
        self._threads_alive = True

        # Automatically kill on exit
        atexit.register(self.kill)
        
        # on_error decorated functions
        self._on_error = []

        self.messages: list[dict[str, dict | str]] = []

    @property
    def address(self) -> str:
        return f"http://{self._ip}:{self._port}"
    
    @property
    def encoding(self) -> str:
        return self._encoding

    @property
    def nick_length(self) -> int:
        return self._nick_length
    
    @property
    def token(self) -> str:
        return self._token
    
    @property
    def registered(self) -> bool:
        return isinstance(self.get(), list)

    # http utilities

    def request(self, data: dict | list = None, method: str = None) -> request.Request:
        "Forms a `request.Request` object with the proper headers."
        
        return request.Request(
            self.address, data=json.dumps(data).encode(self.encoding) if data != None else data,
                headers={
                    "Content-Type": "application/json",
                    "Token": self.token
                },
                method=method
            )

    def get(self) -> dict | list | None:
        "Sends a GET request to the server."
        
        try:
            return json.loads(request.urlopen(self.request(None, "GET")).read())
        except Exception as e:
            return self.on_error(e)

    def post(self, data: dict | list = None) -> dict | None:
        "Sends a POST request alongside `data`."

        data = {} if data == None else data
        try:
            return json.loads(request.urlopen(self.request(data, "POST")).read())
        except Exception as e:
            return self.on_error(e)

    def patch(self, data: dict | list = None) -> dict:
        "Sends a PATCH request alongside `data`."

        data = {} if data == None else data
        r = self.request(data, "PATCH")
        try:
            return json.loads(request.urlopen(r).read())
        except Exception as e:
            return self.on_error(e)

    # etc...

    def on_error(self, f: object | Exception) -> None:
        """Can be implemented as a decorator to call a function when an error
        occurs. Is also called directly when an error occurs, where `f` is the
        exception object - the exception is then provided to all functions
        decorated with `on_error`."""

        # Implement as decorator
        if callable(f):
            self._on_error.append(f)
        # When called, call runners
        else:
            for r in self._on_error:
                r(f)

    def register(self) -> bool:
        "Returns `True` if successfully registered."

        if self.registered:
            return True
        else:
            # Check through error
            r = None
            try:
                r = self.post()
            except Exception as e:
                if type(e) == ulerror.HTTPError:
                    return True
                else:
                    self.on_error(e)
                    return False
            # Register + received config
            if r.get("nick_length") != None:
                self._encoding, self._nick_length, self._token = r["encoding"], r["nick_length"], r["token"]
                return True
        return False
    
    def nickname(self, new: str) -> dict | None:
        "Attempts to change the clients's nickname. Returns the response."

        new.replace(" ", "-")[:self.nick_length]
        r = None
        try:
            r = self.patch({
                "nickname": new
            })
        except Exception as e:
            return self.on_error(e)
        return r
    
    def refresh(self) -> None:
        "Retrieves new messages and appends them to the `self.messages` list."

        self.messages = self.get() or []
    
    def send(self, message: str) -> dict:
        "Attempts to send a message and returns the JSON response."

        return self.post({
            "content": message
        })
    
    def every(self, seconds: int, func: object) -> None:
        "Runs `func` every `seconds` until `alive[0]` is `False`."

        self._threads_alive = True

        def repeat():
            while self._threads_alive:
                time.sleep(seconds)
                func()
        
        threading.Thread(target=repeat).start()

    def load(self) -> str | None:
        "Reads the token from a `token` file if it exists."

        if os.path.isfile(TOKEN):
            with open(TOKEN, "r") as f:
                self._token = f.read().strip()
                f.close()
            return self.token
        return None

    def store(self) -> None:
        "Stores the current token in a `token` file."
        
        if self.token != "":
            with open(TOKEN, "w") as f:
                f.write(self.token)
                f.close()

    def kill(self) -> None:
        "Kills all running `every` loops and shuts the client down appropriately."

        self.store()
        self._threads_alive = False


def create_client() -> StormClient:
    """Opens a popup and prompts the user for an IP and port.
    Then attempts to retrieve the target server configuration.
    Repeats if the server does not exist or is invalid.
    If all goes well, returns a StormClient instance with all
    of the appropriate values."""

    # To be filled in
    global ip, port
    ip, port = None, None

    def stop_gui() -> None:
        global ip, port
        ip = ip_input.get()
        try:
            port = int(port_input.get())
        except ValueError:
            root.destroy()
            Popup.error("Port value must be an integer.")
            return create_client()
        root.destroy()

    root = tk.Tk()

    root.resizable(False, False)
    root.geometry(scale("170x120"))
    root.configure(background="#F0F8FF")
    root.title("Configuration")

    # Ip and port inputs
    ip_input, port_input = tk.Entry(root, width=10, font=FONT), tk.Entry(root, width=5, font=FONT)
    ip_input.place(**scale((10, 35)))
    port_input.place(**scale((110, 35)))

    # Ip and port labels
    tk.Label(root, text="IP:", bg="#F0F8FF", font=FONT).place(**scale((10, 10)))
    tk.Label(root, text="Port:", bg="#F0F8FF", font=FONT).place(**scale((110, 10)))

    # Submit button
    connect_button = tk.Button(root, text="Connect", font=FONT, command=stop_gui)
    connect_button.place(**scale((40, 70))) 

    root.mainloop()

    # Get configuration
    if None in [ip, port]:
        exit(0) # User closed window
    
    return StormClient(ip, port)

# Configuration
WIDTH, HEIGHT = screen_geometry()
SCALE = (
    WIDTH / 1920,
    HEIGHT / 1080
) if Popup.yes_or_no(
    """Your display is smaller/larger than a standard monitor.
    
Dynamic scaling will adjust the graphical interface to size correctly.
However, it may cause elements to be positioned incorrectly.
    
Enable it?""",
    False
) else (1, 1)
FONT = ("Arial", scale(12, "x"), "normal")
REFRESH = 5
TOKEN = "token"
TEXT_BG = "#181d26"
TEXT_FG = "#ffffff"
MAIN_BG = "#36393f"
BUTTON_BG = "#7289da"

if __name__ == "__main__":
    client = create_client()

    # Special / commands
    commands = {} # So that it can be accessed vvv
    commands = {
        "commands": lambda *args : Popup.info("Commands", ", ".join([f"/{c}" for c, _ in commands.items()])),
        "nick": lambda *args : Popup.info(
            "Nickname",
            (client.nickname(" ".join(args)) or {"reason": "Failed to change nickname."})["reason"]
        ),
        "login": lambda *args : (client.__setattr__("_token", args[0]), Popup.info("Token", "Token set.")),
        "run": lambda *args : Popup.info("Run", run(args))
    }

    # Error handler
    @client.on_error
    def on_error(e: Exception):
        if type(e) == ulerror.URLError:
            client.kill()
            Popup.error("There was a problem connecting to the server.", True)
        elif type(e) == ulerror.HTTPError:
            # We ignore 403 because it's incredibly common
            # + we need to detect it at multiple points
            if e.code != 403:
                Popup.warning(f"{e.code}: {e.msg}")
        else:
            Popup.error(e)

    # Check for old logins
    if client.load() != None:
        if client.registered:
            if not Popup.yes_or_no("You have a previous login stored.\n\nLogin with old account?"):
                client._token = ""

    # Attempt to register
    if not client.register():
        Popup.error("Failed to register on the server.", True)

    # Setup the window
    root = tk.Tk()
    root.resizable(False, False)
    root.geometry(scale("500x500"))
    root.configure(background=MAIN_BG)
    root.title("Chat")

    # Chat list
    chat = tk.Text(root, width=53, height=24, fg=TEXT_FG, bg=TEXT_BG,
                    wrap="word", state="disabled", font=FONT)   
    chat.place(**scale((10, 10)))

    # Fill chat automatically
    def add():
        client.refresh()

        # Make it writable
        chat.config(state="normal")

        chat.delete("1.0", tk.END) # Clear
        for m in range(1, len(client.messages)+1):
            message = client.messages[m-1]
            chat.insert(f"{m}.0", f"{message['user']['nickname']}\t | {message['content']}\n")
        
        # User shouldn't be able to modify!!
        chat.config(state="disabled")
        chat.yview(tk.END)

        root.after(REFRESH * 1000, add)

    add() # Start immediately

    # Message input
    message = tk.Entry(root, width=45, bg=TEXT_BG, fg=TEXT_FG, font=FONT)
    message.place(**scale((10, 472)))

    # Submit messages
    def send() -> None:

        data = message.get()
        message.delete(0, tk.END)

        # Message
        if not data.startswith("/"):
            client.send(data)
            client.refresh()
        # Command
        else:
            args = data[1:].split(" ")
            for k, f in commands.items():
                if args[0] == k:
                    return f(*args[1:])
            return Popup.error(f"That command does not exist.")

    # Message submit
    post_button = tk.Button(root, width=5, height=1, bg=BUTTON_BG, text="Post", command=send, font=FONT)
    post_button.place(**scale((430, 470)))

    root.mainloop()
    
    # Finalise
    client.kill()

