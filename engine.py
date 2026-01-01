'''
Docstring for engine.py
This file is everything that has to do with the engine (computer) including the MiniMax algorithm with alpha-beta pruning implemented for optimal decision making.
Cameron Chase
cameron.chase@gmail.com
December 31, 2025
'''

import chess
import math
from dataclasses import dataclass
from eval import evaluate, PIECE_VALUES

@dataclass
class SearchResult:
    score: int #Best eval
    move: chess.Move | None #Best move (none if no legal moves)

def move_ordering(board: chess.Board) -> list:
    '''
    Docstring for move_ordering
    Returns a list of legal moves sorted so best are tried first
    :param board: The current chess board
    '''
    moves = list(board.legal_moves) #List of legal moves

    def key(move: chess.Move) -> int:
        '''
        Docstring for key
        Returns the score evaluation of the move for heuristic
        :param move: The move
        '''
        score = 0
        if board.is_capture(move): #Always prioiritizes captures, promotions, and checks
            capturedPiece = board.piece_at(move.to_square)
            attackingPiece = board.piece_at(move.from_square)
            if capturedPiece:
                score += 10_000 + PIECE_VALUES[capturedPiece.piece_type] * 10 #Bonus for capturing
            if attackingPiece:
                score -= PIECE_VALUES[attackingPiece.piece_type]
        if move.promotion:
            score += 9_000 + PIECE_VALUES.get(move.promotion, 0) #Bonus for promoting
        board.push(move)
        if board.is_check():
            score += 500 #Bonus for checking
        board.pop() #Undo the move to try the next move
        return score
    
    moves.sort(key = key,  reverse = True) #Sort so the highest score is played in the end
    return moves

class MiniMaxEngine:
    def __init__(self):
        self.tt = {} #Cache to avoid reevaluating same positions --> Memoization DP
        self.nodes = 0 #Count nodes evaluated
    
    def _hash(self, board: chess.Board):
        #Hashed the current board position
        if hasattr(board, "transposition_key"):
            return board.transposition_key()
        if hasattr(board, "zobrist_hash"):
            return board.zobrist_hash()
        return hash(board.fen())
    
    def minimax(self, board: chess.Board, depth: int, alpha: int, beta: int) -> int:
        '''
        Docstring for minimax algorithm
        Returns the scores of the moves for each player
        :param alpha: Best score for maximizing player
        :param beta: Best score for minimizing player
        '''
        self.nodes += 1
        key = (self._hash(board), depth, board.turn) #Add key to cache
        if key in self.tt: #Check cache before evaluating to save time
            return self.tt[key]
        if depth == 0 or board.is_game_over(claim_draw = True): #Base case
            val = evaluate(board)
            self.tt[key] = val
            return val
        if board.turn == chess.WHITE: #Maximize white
            best = -math.inf
            for mv in move_ordering(board):
                board.push(mv)
                val = self.minimax(board, depth - 1, alpha, beta)
                board.pop()
                best = max(best, val)
                alpha = max(alpha, best)
                if beta <= alpha:
                    break
        else: #Maximize black
            best = math.inf
            for mv in move_ordering(board):
                board.push(mv)
                val = self.minimax(board, depth - 1, alpha, beta)
                board.pop()
                best = min(best, val)
                beta = min(beta, best)
                if beta <= alpha:
                    break
        self.tt[key] = int(best) #Store score in cache
        return int(best)
    
    def best_move(self, board: chess.Board, depth: int) -> SearchResult:
        '''
        Docstring for best_move
        Returns the chosen move and its score
        '''
        self.nodes = 0
        best_move = None
        if board.turn == chess.WHITE: #Choose move with highest score for white
            best_score = -math.inf
            for move in move_ordering(board):
                board.push(move)
                score = self.minimax(board, depth - 1, -math.inf, math.inf)
                board.pop()
                if score > best_score:
                    best_score = score
                    best_move = move
        else: #Choose move with highest score for black
            best_score = math.inf
            for move in move_ordering(board):
                board.push(move)
                score = self.minimax(board, depth - 1, -math.inf, math.inf)
                board.pop()
                if score < best_score:
                    best_score = score
                    best_move = move
        return SearchResult(score = int(best_score), move = best_move)