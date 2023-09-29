# Import required libraries
import tkinter as tk
import urllib

def get_config(font: tuple[str, int, str] = 
            ("arial", 12, "normal")) -> tuple[str, int, str, int]:
    """Opens a popup and prompts the user for an IP and port.
    Then attempts to retrieve the target server configuration.
    Repeats if the server does not exist or is invalid."""

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
            return get_config(font)
        root.destroy()

    root = tk.Tk()

    root.resizable(False, False)
    root.geometry("250x150")
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
    connect_button = tk.Button(root, text="Submit", font=font, command=stop_gui)
    connect_button.place(x = 100, y = 100) 

    root.mainloop()

    # Get configuration
    

    return (ip, port, "", 0)


# Configuration
IP, PORT, ENCODING, NICK_LENGTH = get_config()

print(IP, ":", PORT)

class StormClient:
    "Manages HTTP requests to the storm server."
    
    def __init__(self, ip: str) -> None:
        pass
