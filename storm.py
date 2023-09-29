# Import required libraries
import urllib.request as request
import tkinter as tk
import json

class StormClient:
    "Manages HTTP requests to the storm server."
    
    def __init__(self, ip: str, port: int) -> None:
        self._ip, self._port = ip, port
        self._registered = False
        self._encoding, self._nick_length = None, None

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

    def request(self, data: dict | list = None) -> request.Request:
        "Forms a `request.Request` object with the proper headers."
        
        return request.Request(self.address, data=data, headers={
            "Content-Type": "application/json"
        })

    def get(self) -> dict | list:
        "Sends a GET request to the server."

        return json.loads(request.urlopen(self.address).read())

    def post(self, data: dict | list) -> dict:
        "Sends a POST request alongside `data`."

        return json.loads(request.urlopen(self.request(data)).read())

    def patch(self, data: dict | list) -> dict:
        "Sends a PATCH request alongside `data`."

        r = self.request(data)
        r.get_header = lambda : "PATCH"
        return json.loads(request.urlopen(r).read())

    # etc...

    def register(self) -> bool:
        "Returns True if successfully registered."

        if self.registered:
            return True
        else:
            if self.post({})["status"] != 201:
                return False
    

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
    
    
    return (ip, port, "", 0)

if __name__ == "__main__":
    client = create_client()
