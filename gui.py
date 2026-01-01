'''
Docstring for gui
This file is the majority of the work, creating a GUI for the game
Cameron Chase
cameron.chase@gmail.com
December 31, 2025
'''

import threading #Different thread for AI
import tkinter as tk
from tkinter import messagebox, ttk
import chess

from engine import MiniMaxEngine
from eval import evaluate, MATE_SCORE

UNICODE_PIECES = { #Pieces for GUI, uppercase white, lowercase black
    "P": "♙", "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
    "p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚",
}

PROMO_MAP = {"Q": chess.QUEEN, "R": chess.ROOK, "B": chess.BISHOP, "N": chess.KNIGHT} #Pieces you can promote to


class ChessApp(tk.Frame):
    def __init__(self, master: tk.Tk, human_color=chess.WHITE, depth=3):
        super().__init__(master) 
        self.master = master #Root window
        self.board = chess.Board() #Board
        self.engine = MiniMaxEngine() #Engine
        self.human_color = human_color #What color the player is

        self.depth = depth #Search depth for engine
        self.square_size = 150 #Board size
        self.margin = 50 #Margins
        self.flipped_default = (self.human_color == chess.BLACK) #Default orientation of board
        self.flipped = self.flipped_default

        self.selected = None #Select a piece to move
        self.legal_dests = set() #Squares a piece can move to
        self.game_over = False #Game status
        self.ai_thinking = False #Whose turn
        
        self.move_objs = [] #Moves
        self.move_sans = [] #SAN Strings for each move
        self.move_evals = [] #Evaluation for each move
        self.view_ply = None #Replay/analysis
        self._cached_view_board = None #Cache old board

        self._build_ui() #Build ui
        self._redraw() #Draw board

        if self.board.turn != self.human_color: #If human it's not the human's turn, engine plays first move
            self._start_ai_move()

    # ---------------- UI ---------------- #

    def _build_ui(self):
        #Window and Top Layout
        self.pack(padx = 10, pady = 10)
        top = tk.Frame(self)
        top.pack(fill = "x", pady = (0, 10))
        #Status label
        self.status_var = tk.StringVar()
        self.status = tk.Label(top, textvariable = self.status_var, anchor = "w")
        self.status.pack(side = "left", fill = "x", expand = True)
        #Buttons
        btns = tk.Frame(top)
        btns.pack(side = "right")
        #Draw button
        self.draw_btn = tk.Button(btns, text = "Draw", width = 10, command = self.offer_draw)
        self.draw_btn.pack(side = "left", padx = 5)
        #Resign button
        self.resign_btn = tk.Button(btns, text = "Resign", width = 10, command = self.resign)
        self.resign_btn.pack(side="left", padx=5)
        #Flip board button
        self.flip_btn = tk.Button(btns, text = "Flip", width = 10, command = self.flip_board)
        self.flip_btn.pack(side="left", padx=5)
        #New Game button
        self.new_btn = tk.Button(btns, text = "New Game", width = 10, command = self.new_game)
        self.new_btn.pack(side = "left", padx = 5)
        #Middle Layout
        mid = tk.Frame(self)
        mid.pack()
        #Board Canvas
        w = self.margin * 2 + self.square_size * 8
        h = self.margin * 2 + self.square_size * 8
        self.canvas = tk.Canvas(mid, width = w, height = h)
        self.canvas.pack(side = "left")
        self.canvas.bind("<Button-1>", self.on_click)
        #Sidebar
        side = tk.Frame(mid)
        side.pack(side = "left", padx = (10, 0), fill = "y")
        #Evaluation bar
        tk.Label(side, text = "Evaluation", anchor = "w").pack(fill = "x")
        self.eval_label_var = tk.StringVar(value = "0.00")
        tk.Label(side, textvariable=self.eval_label_var, anchor = "w").pack(fill = "x")
        self.eval_canvas = tk.Canvas(side, width = 40, height = 280, highlightthickness = 1, highlightbackground = "#444")
        self.eval_canvas.pack(pady = (0, 12))
        #Moves header + Go Live (Resume)
        hdr = tk.Frame(side)
        hdr.pack(fill = "x")
        tk.Label(hdr, text = "Moves (SAN)", anchor = "w").pack(side = "left", fill = "x", expand = True)
        self.live_btn = tk.Button(hdr, text = "Resume", command = self.go_live)
        self.live_btn.pack(side = "right")
        tk.Label(side, text = "Click a cell to jump", anchor = "w").pack(fill = "x", pady = (2, 6))
        #Columns: Move #, White, Black
        moves_frame = tk.Frame(side)
        moves_frame.pack(fill = "both", expand = True)
        self.moves_scroll = tk.Scrollbar(moves_frame)
        self.moves_scroll.pack(side = "right", fill = "y")
        self.moves_tree = ttk.Treeview(moves_frame, columns = ("#", "W", "B"), show = "headings", height = 18, yscrollcommand = self.moves_scroll.set)
        #Column Headers
        self.moves_tree.heading("#", text = "#", anchor = "center")
        self.moves_tree.heading("W", text = "White", ancho = "center")
        self.moves_tree.heading("B", text = "Black", anchor = "center")
        #Column Alignment
        self.moves_tree.column("#", width = 40, anchor = "center", stretch = False)
        self.moves_tree.column("W", width = 100, anchor = "center", stretch = False)
        self.moves_tree.column("B", width = 100, anchor = "center", stretch = False)
        self.moves_tree.pack(side = "left", fill = "both", expand = True)
        self.moves_scroll.config(command = self.moves_tree.yview)
        #History Button
        self.moves_tree.bind("<ButtonRelease-1>", self.on_moves_tree_click)
        #Initializations
        self._set_status()
        self._refresh_moves_table()
        self._update_eval_bar(self.board)

    def _center_window(self, win: tk.Toplevel):
        '''
        Docstring for _center_window
        Centers the game in a maximized window
        '''
        win.update_idletasks()
        w = win.winfo_width()
        h = win.winfo_height()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

    def _set_status(self, extra = ""):
        '''
        Docstring for _set_status
        Updates status bar text
        '''
        if self.view_ply is not None: #Always show history
            msg = f"Move {self.view_ply}/{len(self.move_objs)}"
            if self.game_over:
                msg += " (Game Over)"
            else:
                msg += " (In Analysis)"
            if extra:
                msg += f" — {extra}"
            self.status_var.set(msg)
            return
        if self.game_over:
            self.status_var.set("Game Over (click moves to review)")
            return
        #Live game status
        turn = "White" if self.board.turn == chess.WHITE else "Black"
        who = "You" if self.board.turn == self.human_color else "AI"
        msg = f"Turn: {turn} ({who})"
        if self.board.is_check():
            msg += " — Check!"
        if self.ai_thinking:
            msg += " — AI thinking..."
        if extra:
            msg += f" — {extra}"
        self.status_var.set(msg)

    # -------------- Controls -------------- #

    def new_game(self):
        '''
        Docstring for new_game
        Resets everything for a new game
        '''
        self.board.reset() #Reset board to starting position
        self.flipped = self.flipped_default #Flipped default
        self.selected = None #Clear selection
        self.legal_dests = set() #Clear legal moves
        self.game_over = False #Game is not over anymore
        self.ai_thinking = False #Not engine's turn initially (game hasn't started)
        #Reset history and cached old boards
        self.move_objs.clear()
        self.move_sans.clear()
        self.move_evals.clear()
        self.view_ply = None
        self._cached_view_board = None
        #Reenable Buttons
        self.draw_btn.config(state = "normal")
        self.resign_btn.config(state = "normal")
        #Refresh UI
        self._refresh_moves_table()
        self._update_eval_bar(self.board)
        self._set_status()
        self._redraw()
        #If not human's turn, engine plays first
        if self.board.turn != self.human_color:
            self._start_ai_move()

    def offer_draw(self):
        '''
        Docstring for offer_draw
        Human offers a draw and AI only agrees if it is down more than 5
        '''
        if self.game_over: #Game has to be ongoing
            return
        b = self._get_display_board()
        score = evaluate(b) #Get evaluation
        if abs(score) <= 500: #Only agree to draw if within 5 points of material
            self._end_game("Draw agreed.")
        else:
            messagebox.showinfo("No draws! There will be a clear winner.")

    def resign(self):
        '''
        Docstring for resign
        Human resigns
        '''
        if self.game_over: #Game must be ongoing
            return
        winner = "White" if self.human_color == chess.BLACK else "Black" #Compute who's the winner
        self._end_game(f"You resigned. {winner} wins.") #Popup message

    def flip_board(self):
        self.flipped = not self.flipped #Flip board
        self._redraw() #Flip board 180 degrees with coordinates

    def go_live(self):
        if self.game_over: #Can't go back to play a game that is over
            return
        #If game is ongoing, view live position
        self.view_ply = None
        self._cached_view_board = None
        self.selected = None
        self.legal_dests = set()
        #Clear legal moves for a selection
        for item in self.moves_tree.selection():
            self.moves_tree.selection_remove(item)
        #Update evaluation
        self._update_eval_bar(self.board)
        self._set_status("Back to live position")
        self._redraw()
        #If it's the engine's turn, start it
        if (not self.game_over and self.board.turn != self.human_color and not self.board.is_game_over(claim_draw=True) and not self.ai_thinking):
            self._start_ai_move()

    def _end_game(self, message: str):
        '''
        Docstring for _end_game
        End the game, disable buttons but allow analysis/review
        param message: the message to be printed at end of the game of who won
        '''
        #End game states
        self.game_over = True
        self.ai_thinking = False
        self.status_var.set("Game Over")
        #Disable buttons
        self.draw_btn.config(state = "disabled")
        self.resign_btn.config(state = "disabled")
        #Clear selections and legal moves
        self.selected = None
        self.legal_dests = set()
        self._redraw()
        messagebox.showinfo("Game Over", message)

    # -------------- Moves Analysis Table (White/Black columns) -------------- #
    def _refresh_moves_table(self):
        '''
        Docstring for _refresh_moves_table
        Shows old table based on SAN
        '''
        for item in self.moves_tree.get_children(): #Clear existing moves
            self.moves_tree.delete(item)
        rows = (len(self.move_sans) + 1) // 2 #Number of rows for table
        for i in range(rows):
            w = self.move_sans[2 * i] if 2 * i < len(self.move_sans) else "" #White SAN
            b = self.move_sans[2 * i + 1] if 2 * i + 1 < len(self.move_sans) else "" #Black SAN
            self.moves_tree.insert("", "end", iid = str(i + 1), values = (str(i + 1), w, b)) #Scrolling and selecting move by ID
        if rows > 0: #Scroll to bottom
            self.moves_tree.see(str(rows))
        #Highlight current row in live mode
        if self.view_ply is None and len(self.move_objs) > 0:
            curr = (len(self.move_objs) + 1) // 2
            self.moves_tree.selection_set(str(curr))

    def on_moves_tree_click(self, event):
        '''
        Docstring for on_moves_tree_click
        Shows move when clicked in analysis table
        '''
        if self.ai_thinking: #Don't allow during engine's turn
            return
        #Identitfy what was clicked
        row_id = self.moves_tree.identify_row(event.y)
        col_id = self.moves_tree.identify_column(event.x)
        if not row_id:
            return
        move_idx = int(row_id) - 1 #Move
        #Columns
        if col_id == "#2":
            ply_index = 2 * move_idx
        elif col_id == "#3":
            ply_index = 2 * move_idx + 1
        elif col_id == "#1":
            ply_index = min(2 * move_idx + 1, len(self.move_objs) - 1)
        else:
            return
        #Ignore clicking empty cells
        if ply_index < 0 or ply_index >= len(self.move_objs):
            return
        #Select row
        self.moves_tree.selection_set(row_id)
        #View and clear selection state
        self.view_ply = ply_index + 1
        self._cached_view_board = None
        self.selected = None
        self.legal_dests = set()
        #Update evaulation bar and reset board to before viewing
        vb = self._get_display_board()
        self._update_eval_bar(vb)
        self._set_status()
        self._redraw()

    # -------------- Evaluation Bar -------------- #

    def _format_eval_text(self, score: int) -> str:
        '''
        Docstring for _format_eval_text
        Display evaluation based on score, mate if close to mate score
        '''
        if abs(score) >= MATE_SCORE - 50:
            return "MATE"
        return f"{score / 100:.2f}"

    def _update_eval_bar(self, board: chess.Board):
        '''
        Docstring for _update_eval_bar
        Updating and displaying the visual evaluation bar
        '''
        score = evaluate(board)
        self.eval_label_var.set(self._format_eval_text(score))
        # Clip display to 10 pawns in either color's favor
        CLIP = 1000
        s = max(-CLIP, min(CLIP, score))
        frac = (s + CLIP) / (2 * CLIP)  # 0..1 (0 = black winning, 1 = white winning)
        #Clear old bar and reset size
        self.eval_canvas.delete("all")
        w = int(self.eval_canvas["width"])
        h = int(self.eval_canvas["height"])
        #Draw the bar itself
        white_h = int(h * frac)
        self.eval_canvas.create_rectangle(0, 0, w, white_h, fill = "#f5f5f5", outline = "")
        self.eval_canvas.create_rectangle(0, white_h, w, h, fill = "#222222", outline = "")
        self.eval_canvas.create_line(0, h // 2, w, h // 2, fill = "#888")

    # -------------- Display Board -------------- #

    def _get_display_board(self) -> chess.Board:
        '''
        Docstring for _get_display_board
        Returns the displayed board
        '''
        if self.view_ply is None: #Blank board if no moves yet
            return self.board
        if self._cached_view_board is not None: #Return cached board if exists
            return self._cached_view_board
        #Rebuild using move history
        b = chess.Board()
        for move in self.move_objs[:self.view_ply]:
            b.push(move)
        self._cached_view_board = b
        return b

    def _square_to_xy(self, square: chess.Square):
        '''
        Docstring for _square_to_xy
        Converts the matrix from square to coordinates
        '''
        file = chess.square_file(square) #Columns a-h
        rank = chess.square_rank(square) #Rows 1-7
        if not self.flipped: #Normal orientation
            col = file
            row = 7 - rank
        else: #Flipped orientation
            col = 7 - file
            row = rank
        x = self.margin + col * self.square_size
        y = self.margin + row * self.square_size
        return x, y #Returns coordinates

    def _xy_to_square(self, x, y):
        '''
        Docstring for _xy_to_square
        Converts coordinates to a square
        '''
        x -= self.margin
        y -= self.margin
        if x < 0 or y < 0:
            return None
        col = x // self.square_size
        row = y // self.square_size
        if col < 0 or col > 7 or row < 0 or row > 7:
            return None
        if not self.flipped: #Normal orientation
            file = int(col)
            rank = 7 - int(row)
        else: #Flipped orientation
            file = 7 - int(col)
            rank = int(row)
        return chess.square(file, rank) #Return chess square

# ---------------- Draw Board ---------------- #

    def _redraw(self):
        '''
        Docstring for _redraw
        Draws the chess board itself
        '''
        b = self._get_display_board() #Board in use
        self.canvas.delete("all") #Clear previous
        #Draw every square
        for square in chess.SQUARES:
            x, y = self._square_to_xy(square)
            x2, y2 = x + self.square_size, y + self.square_size
            file = chess.square_file(square)
            rank = chess.square_rank(square)
            light = (file + rank) % 2 == 1
            fill = "#EEEED2" if light else "#769656"
            self.canvas.create_rectangle(x, y, x2, y2, fill = fill, outline = "")
        #Highlight legal moves for a selected piece
        if self.view_ply is None:
            if self.selected is not None:
                x, y = self._square_to_xy(self.selected)
                self.canvas.create_rectangle(x, y, x + self.square_size, y + self.square_size, outline = "#FFD700", width = 4)
            for square in self.legal_dests:
                x, y = self._square_to_xy(square)
                self.canvas.create_oval(x + self.square_size * 0.35, y + self.square_size * 0.35, x + self.square_size * 0.65, y + self.square_size * 0.65, outline = "", fill = "#000000", stipple = "gray50")
        #Draw every piece
        for square, piece in b.piece_map().items():
            x, y = self._square_to_xy(square)
            symbol = piece.symbol()
            text = UNICODE_PIECES.get(symbol, symbol)
            self.canvas.create_text(x + self.square_size / 2, y + self.square_size / 2, text = text, font = ("Segoe UI Symbol", int(self.square_size * 0.6)))
        #Draw files
        for column in range(8):
            file_idx = (7 - column) if self.flipped else column
            cx = self.margin + column * self.square_size + self.square_size / 2
            cy = self.margin + 8 * self.square_size + self.margin / 2
            self.canvas.create_text(cx, cy, text = chr(ord("a") + file_idx), anchor = "center", font = ("Arial", 14))
        #Draw ranks
        for row in range(8):
            rank_num = (row + 1) if self.flipped else (8 - row)
            cx = self.margin / 2
            cy = self.margin + row * self.square_size + self.square_size / 2
            self.canvas.create_text(cx, cy, text = str(rank_num), anchor = "center", font = ("Arial", 14))

    # -------------- Move Handling -------------- #

    def on_click(self, event):
        '''
        Docstring for on_click
        Handles when user clicks a piece
        '''
        if self.game_over: #Game can't be over
            return
        if self.view_ply is not None: #Can't move when in analysis
            self._set_status("You’re viewing history. Click Resume to move.")
            return
        if self.board.turn != self.human_color: #Can't move out of turn
            return
        if self.ai_thinking: #Can't move when engine is thinking
            return
        #Click coordinate corresponds to a square
        sq = self._xy_to_square(event.x, event.y)
        if sq is None:
            return
        piece = self.board.piece_at(sq)
        #Select a piece
        if self.selected is None:
            if piece and piece.color == self.human_color:
                self.selected = sq
                self.legal_dests = self._legal_destinations_from(sq)
                self._set_status("Piece selected")
                self._redraw()
            return
        #Deselect piece
        if sq == self.selected:
            self.selected = None
            self.legal_dests = set()
            self._set_status()
            self._redraw()
            return
        #Create legal move from selected square
        mv = self._make_move_from_to(self.selected, sq)
        if mv is None: #If invalid, reselect
            if piece and piece.color == self.human_color:
                self.selected = sq
                self.legal_dests = self._legal_destinations_from(sq)
                self._set_status("Piece selected")
                self._redraw()
            return
        #SAN must be computed before moving, record to history for analysis
        san = self.board.san(mv)
        self.board.push(mv)
        self._record_ply(mv, san)
        #Show on board
        self.selected = None
        self.legal_dests = set()
        #Update evaluation bar and status and board
        self._update_eval_bar(self.board)
        self._set_status()
        self._redraw()
        #Make sure game didn't end
        if self._check_game_end():
            return
        #If game still ongoing, engine turn
        self._start_ai_move()

    def _record_ply(self, mv: chess.Move, san: str):
        '''
        Docstring for _record_ply
        Add move to history and refresh move table
        '''
        #Append move and notation
        self.move_objs.append(mv)
        self.move_sans.append(san)
        self.move_evals.append(evaluate(self.board))
        self._cached_view_board = None #No cached board of new position
        self._refresh_moves_table() #Refresh moves table

    def _legal_destinations_from(self, from_sq):
        '''
        Docstring for _legal_destinations_from
        Returns list of legal destinations for a selected piece
        '''
        dests = set()
        for mv in self.board.legal_moves:
            if mv.from_square == from_sq:
                dests.add(mv.to_square)
        return dests

    def _make_move_from_to(self, from_sq, to_sq):
        '''
        Docstring for _make_move_from_to
        Makes legal move, prompts promotion if applicable
        '''
        candidates = [mv for mv in self.board.legal_moves if mv.from_square == from_sq and mv.to_square == to_sq] #List of legal moves
        if not candidates: #No legal moves
            return None
        if len(candidates) == 1 and candidates[0].promotion is None: #Return move directly if move is forced and not a promotion
            return candidates[0]
        #Handle promotion
        promo_moves = [mv for mv in candidates if mv.promotion is not None]
        if promo_moves:
            choice = self._promotion_dialog()
            if choice is None:
                return None
            promo_piece = PROMO_MAP[choice]
            for mv in promo_moves:
                if mv.promotion == promo_piece:
                    return mv
            return promo_moves[0]
        return candidates[0] #At the end, return first candidate if choice needs to be made

    def _promotion_dialog(self):
        '''
        Docstring for _promotion_dialog
        Dialog for what piece to promote to
        '''
        dialog = tk.Toplevel(self.master)
        dialog.title("Promote pawn")
        dialog.resizable(False, False)
        tk.Label(dialog, text="Choose promotion:").pack(padx = 10, pady = 10)
        choice_var = tk.StringVar(value = "Q")
        row = tk.Frame(dialog)
        row.pack(padx=10, pady=10)
        for c in ["Q", "R", "B", "N"]:
            tk.Radiobutton(row, text = c, variable = choice_var, value = c).pack(side = "left", padx = 8)
        result = {"val": None}
        def ok(): #Continues with promotion
            result["val"] = choice_var.get()
            dialog.destroy()
        def cancel(): #Cancels promotion
            result["val"] = None
            dialog.destroy()
        btns = tk.Frame(dialog)
        btns.pack(pady = (0, 10))
        tk.Button(btns, text = "OK", width = 8, command = ok).pack(side = "left", padx = 5)
        tk.Button(btns, text = "Cancel", width = 8, command = cancel).pack(side = "left", padx = 5)
        dialog.transient(self.master)
        self._center_window(dialog)
        dialog.grab_set()
        self.master.wait_window(dialog)
        return result["val"]

    # -------------- Engine Move -------------- #

    def _start_ai_move(self):
        '''
        Docstring for _start_ai_move
        Engine searches for move using new thread
        '''
        if self.game_over or self.view_ply is not None:
            return
        self.ai_thinking = True
        self._set_status()
        self._redraw()
        def worker(): #Search for best move on new thread
            res = self.engine.best_move(self.board, self.depth)
            self.master.after(0, lambda: self._apply_ai_move(res.move))
        threading.Thread(target=worker, daemon=True).start() #Apply move on UI thread

    def _apply_ai_move(self, move):
        '''
        Docstring for _apply_ai_move
        Apply engine move to the game
        '''
        if self.game_over:
            return
        self.ai_thinking = False
        if self.view_ply is not None: #Don't update the board until user exits analysis mode
            self._set_status()
            return
        if move is None: #No moves means game is over
            self._check_game_end()
            return
        #Compute SAN before applying move
        san = self.board.san(move)
        self.board.push(move)
        self._record_ply(move, san) #Record move in history
        #Update evaluation bar, status, and redraw the board
        self._update_eval_bar(self.board)
        self._set_status()
        self._redraw()
        self._check_game_end() #See if game is over after engine move

    # -------------- (Stale?) Mate Detection -------------- #

    def _check_game_end(self) -> bool:
        '''
        Docstring for _check_game_end
        Checks if a mate or draw is on the board and handle
        '''
        if self.board.is_game_over(claim_draw=True):
            outcome = self.board.outcome(claim_draw=True)
            if outcome is None:
                self._end_game("Game over.")
                return True
            if outcome.winner is None:
                self._end_game("Draw.")
                return True
            winner = "White" if outcome.winner == chess.WHITE else "Black"
            self._end_game(f"{winner} wins.")
            return True
        return False
