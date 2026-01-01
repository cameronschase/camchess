'''
Docstring for eval.py
This class is everything that has to do with calculating the evaluation of a position on the board.
Cameron Chase
cameron.chase@gmail.com
December 31, 2025
'''

import chess

PIECE_VALUES = {chess.PAWN: 100, chess.KNIGHT: 300, chess.BISHOP: 325, chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0} #Material score for a piece * 100 --> GM Bobby Fischer believes that Bishop ≈ 3.25 > Knight ≈ 3

PIECE_SQUARE_TABLE = { #Heuristic for placement of a given piece
    chess.PAWN: [
         0,  0,  0,  0,  0,  0,  0,  0,
         50, 50, 50, 50, 50, 50, 50, 50,
         10, 10, 20, 30, 30, 20, 10, 10,
         5,  5, 10, 25, 25, 10,  5,  5,
         0,  0,  0, 20, 20,  0,  0,  0,
         5, -5,-10,  0,  0,-10, -5,  5,
         5, 10, 10,-20,-20, 10, 10,  5,
         0,  0,  0,  0,  0,  0,  0,  0,
    ],
    chess.KNIGHT: [ #Knights are more useful when in the center since they control more squares
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  0,  0,  0,-20,-40,
        -30,  0, 10, 15, 15, 10,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  0, 15, 20, 20, 15,  0,-30,
        -30,  5, 10, 15, 15, 10,  5,-30,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -50,-40,-30,-30,-30,-30,-40,-50,
    ],
    chess.BISHOP: [ #Bishops are more useful when in the center since they control more squares
        -20,-10,-10,-10,-10,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5, 10, 10,  5,  0,-10,
        -10,  5,  5, 10, 10,  5,  5,-10,
        -10,  0, 10, 10, 10, 10,  0,-10,
        -10, 10, 10, 10, 10, 10, 10,-10,
        -10,  5,  0,  0,  0,  0,  5,-10,
        -20,-10,-10,-10,-10,-10,-10,-20,
    ],
    chess.ROOK: [ #Rooks are most useful when attacking enemy pawns or in the center targeting the opposing king/protecting their own king 
         0,  0,  0,  0,  0,  0,  0,  0,
         5, 10, 10, 10, 10, 10, 10,  5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
         0,  0,  0,  5,  5,  0,  0,  0,
    ],
    chess.QUEEN: [ #Queens are most useful in the center
        -20,-10,-10, -5, -5,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5,  5,  5,  5,  0,-10,
         -5,  0,  5,  5,  5,  5,  0, -5,
          0,  0,  5,  5,  5,  5,  0, -5,
        -10,  5,  5,  5,  5,  5,  0,-10,
        -10,  0,  5,  0,  0,  0,  0,-10,
        -20,-10,-10, -5, -5,-10,-10,-20,
    ],
    chess.KING: [ #Kings are best when castled and protected in their corners
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -20,-30,-30,-40,-40,-30,-30,-20,
        -10,-20,-20,-20,-20,-20,-20,-10,
         20, 20,  0,  0,  0,  0, 20, 20,
         20, 30, 10,  0,  0, 10, 30, 20,
    ],
}

MATE_SCORE = 10_000 #Constant for checkmate
DRAW_SCORE = 0 #Constant for draw-like positions such as stalemate, insufficient material, etc.

def pieceSquareTableValue(piece_type: chess.Piece, square: chess.Square, color: chess.Color) -> int:
    '''
    Docstring for pieceSquareTableValue
    Returns the value of the piece given its color, type, and the square it's on
    
    :param piece_type: Which piece it is
    :param square: Which square it's on number 0-63 from matrices above
    :param color: White or Black
    '''
    table = PIECE_SQUARE_TABLE[piece_type]
    index = square if color == chess.WHITE else chess.square_mirror(square)
    return table[index]

def evaluate(board: chess.Board) -> int:
    '''
    Docstring for evaluate
    Returns the evaluated score of the position --> Positive means white is winning
    :param board: The chess board
    '''
    if board.is_checkmate():
        return -MATE_SCORE if board.turn == chess.WHITE else MATE_SCORE #Whoevers turn it is has lost, return +/- mate score depending on whose turn it is
    if board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw(): #If draw, then score is draw
        return DRAW_SCORE
    score = 0 #Game is still going, calculate score
    for square, piece in board.piece_map().items(): #Add all the scores of pieces on a square
        value = PIECE_VALUES[piece.piece_type] + pieceSquareTableValue(piece.piece_type, square, piece.color)
        score += value if piece.color == chess.WHITE else -value #Add white, subtract black
    #Mobility Heuristic: More legal moves means better positioning for person whose turn it is
    mobility = board.legal_moves.count()
    score += mobility if board.turn == chess.WHITE else -mobility
    return score