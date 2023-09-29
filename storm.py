# Import required libraries
import tkinter as tk
import urllib

# Create the main application window
app = tk.Tk()
app.title("Server information")

# Create a label
label = tk.Label(app, text="IP:")
label.pack()

# Create a text input field
entry = tk.Entry(app)
entry.pack()

# Create a button
button = tk.Button(app, text="Submit", command=lambda : output_label.config(text=entry.get()))
button.pack()

# Create a label to display the result
output_label = tk.Label(app, text="")
output_label.pack()

# Start the Tkinter main loop
app.mainloop()

# Configuration
ENCODING = "utf-8"

class StormClient:
    "Manages HTTP requests to the storm server."
    
    def __init__(self, ip: str) -> None:
        pass
