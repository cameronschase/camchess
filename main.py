'''
Docstring for main
This runs everything from GUI in a root window
Cameron Chase
cameron.chase@gmail.com
December 31, 2025
'''

import chess
import random
import tkinter as tk
from gui import ChessApp

def main():
    root = tk.Tk()
    root.title("Cam Chess")
    # Fullscreen on start
    root.state("zoomed")
    #Exit with escape key
    HUMAN_COLOR = random.choice([chess.WHITE, chess.BLACK]) #Randomly select colors
    DEPTH = 3 #Default engine depth
    ChessApp(root, human_color = HUMAN_COLOR, depth = DEPTH)
    root.mainloop()

if __name__ == "__main__":
    main()