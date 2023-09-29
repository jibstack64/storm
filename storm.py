# Import required libraries
import urllib.request as request
import tkinter as tk
import threading
import time
import json

class StormClient:
    "Manages HTTP requests to the storm server."
    
    def __init__(self, ip: str, port: int) -> None:
        self._ip, self._port = ip, port
        self._registered = False
        self._encoding, self._nick_length = "utf-8", 8

        self.messages: list[dict[str, dict | str]] = []

    @property
    def address(self) -> str:
        return f"http://{self._ip}:{self._port}"
    
    @property
    def registered(self) -> bool:
        return self._registered
    
    @property
    def encoding(self) -> str:
        return self._encoding

    @property
    def nick_length(self) -> int:
        return self._nick_length

    # http utilities

    def open_url(self, req: str | request.Request, *args, **kwargs):
        "A proxy for the `urllib` `urlopen` function. Useful for extra functionality."

        return request.urlopen(req, *args, **kwargs)

    def request(self, data: dict | list = None) -> request.Request:
        "Forms a `request.Request` object with the proper headers."
        
        return request.Request(
            self.address, data=json.dumps(data).encode(self.encoding) if data != None else data,
                headers={
                    "Content-Type": "application/json"
                }
            )

    def get(self) -> dict | list:
        "Sends a GET request to the server."

        return json.loads(request.urlopen(self.address).read())

    def post(self, data: dict | list = None) -> dict:
        "Sends a POST request alongside `data`."

        data = {} if data == None else data
        return json.loads(request.urlopen(self.request(data)).read())

    def patch(self, data: dict | list = None) -> dict:
        "Sends a PATCH request alongside `data`."

        data = {} if data == None else data
        r = self.request(data)
        r.get_header = lambda : "PATCH"
        return json.loads(request.urlopen(r).read())

    # etc...

    def register(self) -> bool:
        "Returns True if successfully registered."

        if self.registered:
            return True
        else:
            # Check through error
            r = None
            try:
                r = self.post()
            except:
                return True
            # Config
            if r.get("encoding") != None or r.get("status") == 400:
                self._encoding, self._nick_length = r["encoding"], r["nick_length"]
                return True
        return False
    
    def refresh(self) -> int:
        """Retrieves new messages and appends them to the `self.messages` list.
        Returns the number of new messages."""

        new = self.get()
        for n in new:
            self.messages.append(n)
        return len(new)
    
    def send(self, message: str) -> int:
        "Attempts to send a message and returns the status code."

        return self.post({
            "content": message
        })["status"]
    
    def every(self, seconds: int, func: object, alive: list[bool]) -> None:
        "Runs `func` every `seconds` until `alive[0]` is `False`."

        def repeat():
            while alive[0]:
                func()
                time.sleep(seconds)
        
        threading.Thread(target=repeat).start()


def create_client(font: tuple[str, int, str] = 
            ("arial", 12, "normal")) -> StormClient:
    """Opens a popup and prompts the user for an IP and port.
    Then attempts to retrieve the target server configuration.
    Repeats if the server does not exist or is invalid.
    If all goes well, returns a StormClient instance with all
    of the appropriate values."""

    # To be filled in
    global ip, port
    ip, port, encoding, nick_length = (None for x in range(0, 4))

    def stop_gui() -> None:
        global ip, port
        ip = ip_input.get()
        try:
            port = int(port_input.get())
        except ValueError:
            root.destroy()
            return create_client(font)
        root.destroy()

    root = tk.Tk()

    root.resizable(False, False)
    root.geometry("175x120")
    root.configure(background="#F0F8FF")
    root.title("Configuration")

    # Ip and port inputs
    ip_input, port_input = tk.Entry(root, width="10", font=font), tk.Entry(root, width="5", font=font)
    ip_input.place(x = 10, y = 35)
    port_input.place(x = 110, y = 35)

    # Ip and port labels
    tk.Label(root, text="IP:", bg="#F0F8FF", font=font).place(x=10, y=10)
    tk.Label(root, text="Port:", bg="#F0F8FF", font=font).place(x=110, y=10)

    # Submit button
    connect_button = tk.Button(root, text="Connect", font=font, command=stop_gui)
    connect_button.place(x = 40, y = 70) 

    root.mainloop()

    # Get configuration
    if None in [ip, port]:
        exit(0) # User closed window
    
    return StormClient(ip, port)

if __name__ == "__main__":
    client = create_client()

    # Attempt to register
    if not client.register():
        print("Failed to register on the server.")
        exit(1)

    # Refresh messages every 8 seconds
    alive = [True] # Eh.. pointer alternative
    client.every(8, client.refresh, alive)

    root = tk.Tk()

    root.resizable(False, False)
    root.geometry("500x500")
    root.configure(background="#F0F8FF")
    root.title("Chat")

    root.mainloop()
    
    alive[0] = False # Deactive refresh

