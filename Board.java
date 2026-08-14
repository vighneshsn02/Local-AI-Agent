@author Your Name
public class Board {
    private Piece[][] pieces;
    
    public Board() {
        // Initialize chess board and pieces
        pieces = new Piece[8][8];
        for (int i = 0; i < 8; i++) {
            for (int j = 0; j < 8; j++) {
                if ((i + j) % 2 == 0) {
                    pieces[i][j] = new Pawn();
                } else {
                    pieces[i][j] = new Knight();
                }
            }
        }
    }

    public Piece getPiece(int row, int col) {
        return pieces[row][col];
    }
}