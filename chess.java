@author Your Name
public class Chess {
    public static void main(String[] args) {
        // Initialize chess board and pieces
        Board board = new Board();
        Piece[][] pieces = new Piece[8][8];
        
        // Game loop
        while (true) {
            System.out.println("Your turn!");
            System.out.print("Enter row and column (e.g. 1-8, 1-8): ");
            String[] input = scanner.nextLine().split(" ");
            int row = Integer.parseInt(input[0]) - 1;
            int col = Integer.parseInt(input[1]) - 1;
            Piece piece = board.getPiece(row, col);
            if (piece != null) {
                // Move or capture piece
                piece.move(row, col);
                System.out.println("Piece moved!");
            } else {
                System.out.println("Invalid move!");
            }
        }
    }
}