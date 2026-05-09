import customtkinter as ctk
# modo oscuro tipo launcher gaming
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ventana principal
app = ctk.CTk()
app.title("Stella Client")
app.geometry("900x500")

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