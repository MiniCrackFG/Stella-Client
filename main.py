import customtkinter as ctk
# modo oscuro tipo launcher gaming
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ventana principal
app = ctk.CTk()
app.title("Stella Client")
app.geometry("900x500")

# topbar
topbar = ctk.CTkFrame(
    app,
    height=50,
    fg_color="#111111"
)

topbar.pack(fill="x")

# account button
account = ctk.CTkLabel(
    topbar,
    text="Account",
    font=("Arial", 16)
)
account.pack(side="right", padx=20, pady=10)

# sidebar
sidebar = ctk.CTkFrame(
    app,
    width=220,
    fg_color="#111111"
)
sidebar.pack(side="left", fill="y")

# Settings button
settings = ctk.CTkLabel(
    sidebar,
    text="Settings",
    font=("Arial", 16)
)
settings.pack(side="bottom", anchor="w", padx=20, pady=20)

sidebar.pack(side="left", fill="y")

# titulo
title = ctk.CTkLabel(
    app,
    text="Stella Client",
    font=("Arial", 32)
)
title.pack(pady=40)

# boton play
def play():
    print("Launching Minecraft...")

play_button = ctk.CTkButton(
    app,
    text="PLAY",
    width=200,
    height=50,
    command=play
)
play_button.pack(pady=20)

app.mainloop()
