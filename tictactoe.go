package main

import (
	"fmt"
)

const boardSize = 3

type Player rune
const (
	X Player = 'X'
	O Player = 'O'
	Empty Player = ' '
)

type Board [boardSize][boardSize]Player

func newBoard() Board {
	var b Board
	for i := 0; i < boardSize; i++ {
		for j := 0; j < boardSize; j++ {
			b[i][j] = Empty
		}
	}
	return b
}

func (b *Board) print() {
	fmt.Println("\n--- Board ---")
	for i := 0; i < boardSize; i++ {
		for j := 0; j < boardSize; j++ {
			fmt.Printf(" %c ", b[i][j])
			if j < boardSize-1 {
				fmt.Print("|")
			}
		}
		fmt.Println()
		if i < boardSize-1 {
			fmt.Println("---|---|---")
		}
	}
	fmt.Println("-------------")
}

func (b *Board) makeMove(row, col int, p Player) bool {
	if row < 0 || row >= boardSize || col < 0 || col >= boardSize {
		fmt.Println("Error: Invalid row or column.")
		return false
	}
	if b[row][col] != Empty {
		fmt.Println("Error: This cell is already occupied.")
		return false
	}
	b[row][col] = p
	return true
}

func (b *Board) checkWin(p Player) bool {
	// Check rows
	for i := 0; i < boardSize; i++ {
		if b[i][0] == p && b[i][1] == p && b[i][2] == p {
			return true
		}
	}

	// Check columns
	for j := 0; j < boardSize; j++ {
		if b[0][j] == p && b[1][j] == p && b[2][j] == p {
			return true
		}
	}

	// Check diagonals (top-left to bottom-right)
	if b[0][0] == p && b[1][1] == p && b[2][2] == p {
		return true
	}

	// Check diagonals (top-right to bottom-left)
	if b[0][2] == p && b[1][1] == p && b[2][0] == p {
		return true
	}

	return false
}

func (b *Board) checkTie() bool {
	for i := 0; i < boardSize; i++ {
		for j := 0; j < boardSize; j++ {
			if b[i][j] == Empty {
				return false
			}
		}
	}
	return true
}

func main() {
	board := newBoard()
	currentPlayer := X
	var row, col int
	gameOver := false

	fmt.Println("👋 Welcome to Tic-Tac-Toe!")
	fmt.Println("Enter row and column numbers (0, 1, or 2) to make a move.")

	for !gameOver {
		board.print()
		
		fmt.Printf("➡️ Player %c, your turn (Row Column): ", currentPlayer)
		
		_, err := fmt.Scanf("%d %d", &row, &col)
		
		if err != nil {
			fmt.Println("Error: Please enter two numbers (Row and Column).")
			fmt.Scanln() 
			continue
		}

		if board.makeMove(row, col, currentPlayer) {

			if board.checkWin(currentPlayer) {
				board.print()
				fmt.Printf("🎉 Player %c Wins! Congratulations!\n", currentPlayer)
				gameOver = true
			} else if board.checkTie() {
				board.print()
				fmt.Println("🤝 Tie! Game over.")
				gameOver = true
			} else {
				if currentPlayer == X {
					currentPlayer = O
				} else {
					currentPlayer = X
				}
			}
		}
	}

	fmt.Println("\nGame finished. Run the program again to play another round.")
}