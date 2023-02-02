"""
Script to simulate games of Wordle (https://www.nytimes.com/games/wordle/index.html)
and automatically solve them.
"""
import json
import random
import statistics
import time

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Set, Tuple


# These hard coded frequencies were generated by the function print_letter_frequency
CHAR_TO_FREQUENCY = {
    "a": 0.0960,
    "b": 0.0249,
    "c": 0.0302,
    "d": 0.0368,
    "e": 0.1004,
    "f": 0.0167,
    "g": 0.0251,
    "h": 0.0268,
    "i": 0.0590,
    "j": 0.0046,
    "k": 0.0236,
    "l": 0.0509,
    "m": 0.0325,
    "n": 0.0468,
    "o": 0.0702,
    "p": 0.0328,
    "q": 0.0020,
    "r": 0.0635,
    "s": 0.0985,
    "t": 0.0499,
    "u": 0.0394,
    "v": 0.0108,
    "w": 0.0152,
    "x": 0.0044,
    "y": 0.0323,
    "z": 0.0068,
}


def print_letter_frequency() -> None:
    """Print a mapping from letter to its frequency in the word list.

    This is just a helper function to generate a hard coded mapping.
    """
    words = get_words()
    all_chars = [char for word in words for char in word]
    num_chars = len(all_chars)
    char_to_count = Counter(all_chars)
    char_to_frequency = {
        char: count / num_chars for char, count in char_to_count.items()
    }
    for char, frequency in sorted(char_to_frequency.items(), key=lambda t: t[0]):
        print(f'    "{char}": {round(frequency, 4)},')


def get_words() -> List[str]:
    """Return a list of words read in from a json file.

    short_word_list.json has 2_309 words
    long_word_list.json has 14_855 words

    These word lists were copied from the js code in https://www.nytimes.com/games/wordle/index.html
    using browser dev tools.  There seems to be a shorter list of more common words,
    and a longer, more comprehensive list.
    """
    return json.loads(Path("short_word_list.json").read_text())


class Colour(Enum):
    GREY = "grey"
    YELLOW = "yellow"
    GREEN = "green"


@dataclass
class Char:
    """A Character and the colour it is on the wordle board.

    Green -> correct letter in correct position
    Yellow -> correct letter in wrong position
    Grey -> incorrect letter
    """

    letter: str
    colour: Colour

    def get_print_str(self, use_colours: bool = True) -> str:
        """Return the given char with extra chars to show colour in the terminal.

        TODO: could look into other packages to print colour to terminal.
        For now using this method because it does not require any dependencies.
        """
        if not use_colours:
            return self.letter

        if self.colour == Colour.GREEN:
            colour_start = "\033[92m"
        elif self.colour == Colour.YELLOW:
            colour_start = "\033[93m"
        elif self.colour == Colour.GREY:
            colour_start = "\033[97m"
        else:
            raise ValueError(f"Unexpected colour: {self.colour}")

        colour_end = "\033[00m"
        return f"{colour_start}{self.letter}{colour_end}"


@dataclass
class Guess:
    """A word which has been guessed, which contains information on the colour of each letter."""

    chars: List[Char]

    @classmethod
    def create_from_word(cls, word: str, solution: str) -> "Guess":
        """Return a Guess instance for the given word and solution."""
        chars = []

        for i, (char, solution_char) in enumerate(zip(word, solution)):
            if char == solution_char:
                colour = Colour.GREEN
            elif char not in solution:
                colour = Colour.GREY
            else:
                # we don't know if this char is yellow or grey yet
                colour = None

            chars.append(Char(letter=char, colour=colour))

        # Process the remaining chars
        for i, char in enumerate(chars):
            if char.colour is not None:
                continue

            # Note: for duplicate chars, wordle marks chars yellow up to a maximum of the
            # number in the solution.
            # See examples here https://nerdschalk.com/wordle-same-letter-twice-rules-explained-how-does-it-work/
            # e.g. if the guess is "boots" and the solution is "piano"
            # the first "o" will be yellow, but the second will be grey.
            num_instances_in_solution = Counter(solution)[char.letter]
            num_instances_recognised_so_far = sum(
                1
                for other_char in chars
                if other_char.letter == char.letter
                and other_char.colour in (Colour.GREEN, Colour.YELLOW)
            )
            should_be_yellow = (
                num_instances_recognised_so_far < num_instances_in_solution
            )
            char.colour = Colour.YELLOW if should_be_yellow else Colour.GREY

        return cls(chars=chars)

    def print(self) -> None:
        """Print the guess to the screen with chars coloured in green/yellow/grey."""
        print("".join(char.get_print_str() for char in self.chars))

    @property
    def is_correct(self) -> bool:
        """Return True if the guess is correct, otherwise False."""
        return all(char.colour == Colour.GREEN for char in self.chars)


ALL_CHARS = set("abcdefghijklmnopqrstuvwxyz")


@dataclass
class Puzzle:
    """A single wordle puzzle.

    keeps track of the state of the game e.g. the solution, and what words have been guessed.
    """

    solution: str
    guesses: List[Guess]

    MAX_NUM_GUESSES = 6
    WORD_LENGTH = 5

    def enter_word(self, word: str) -> Guess:
        """Add the given word as a guess and return the guess object."""

        if len(self.guesses) >= self.MAX_NUM_GUESSES:
            raise ValueError(f"exceeded max number of guesses {self.MAX_NUM_GUESSES}")

        if len(word) != self.WORD_LENGTH:
            raise ValueError(f"Word {word} is not {self.WORD_LENGTH} chars long.")

        # normalise words to lowercase
        word = word.lower()

        unknown_chars = set(word) - ALL_CHARS
        if unknown_chars:
            raise ValueError(f"word {word} has unknown characters: {unknown_chars}")

        guess = Guess.create_from_word(word, self.solution)

        self.guesses.append(guess)
        return guess

    def print(self) -> None:
        """Print all guesses."""
        for guess in self.guesses:
            guess.print()

    @property
    def is_in_progress(self) -> bool:
        """Return True if the game is still in progress, otherwise False."""
        if self.won:
            return False

        return len(self.guesses) < self.MAX_NUM_GUESSES

    @property
    def won(self) -> bool:
        """Return True if the game is won, otherwise False."""
        if not self.guesses:
            return False

        return self.guesses[-1].is_correct


class ConstraintType(Enum):
    IN_SOME_POSITION = "in_some_position"
    NOT_IN_POSITIONS = "not_in_positions"


@dataclass
class Constraint:
    """A constraint on the possible solutions to the wordle puzzle.

    A constraint consists of:
    - a character e.g. "e"
    - a set of position indices e.g. {0, 2, 3, 4}
    - a type e.g. IN_SOME_POSITION

    type=IN_SOME_POSITION means that the given character is in one of the given positions.
    type=NOT_IN_POSITIONS means the given character is NOT in any of the given positions.
    """

    char: str
    positions: Set[int]
    type: ConstraintType

    def is_satisfied(self, word: str) -> bool:
        """Return True if this constraint is satisfied for the given word, otherwise False."""
        char_is_in_some_position = any(
            word[position] == self.char for position in self.positions
        )

        if self.type == ConstraintType.IN_SOME_POSITION:
            return char_is_in_some_position
        elif self.type == ConstraintType.NOT_IN_POSITIONS:
            return not char_is_in_some_position
        else:
            raise ValueError(f"Unknown constraint type: {self.type}")


def get_frequency_score(word: str) -> float:
    """Return the sum of letter frequencies of unique characters in the word.

    Higher score is good because we are more likely to get a char match (green or yellow guess).
    We only sum unique chars because repeating letters is not useful when we are
    trying to get as many green/yellow hits as possible.
    e.g. "later" (5 unique letters) is better than "eerie" (3 unique letters)
    """
    return sum(CHAR_TO_FREQUENCY[char] for char in set(word))


def get_word_to_guess(words: List[str], constraints: List[Constraint]) -> str:
    """Return a new word to guess based on the constraints.

    This function will filter the word list down to those which satisfy all constraints,
    then pick the most "popular" word based on letter frequencies.

    TODO: Investigate potential improvement to determine the answer faster.

    eg. consider the case where the solution is "eater"
    instead of guessing:

    later
    cater
    hater
    water
    eater

    we could potentially narrow down faser by guessing word(s) with "l", "c", "h", "w", "e"
    """
    # filter out any words that violate constraints
    words = [
        word
        for word in words
        if all(constraint.is_satisfied(word) for constraint in constraints)
    ]
    # Choose the word that has the most popular letters
    return max(words, key=get_frequency_score)


def update_constraints(
    constraints: List[Constraint], guess: Guess, word_length: int
) -> List[Constraint]:
    """Return an updated list of constraints to reflect the green/yellow/grey letters in this guess.

    Green -> char is in the word and in the correct position.
    Yellow -> char is in the word but in the wrong position.
    Grey -> char is not in the word.

    Remove/Add constraints based on what we have learned from the new guess.
    """
    new_constraints = deepcopy(constraints)

    for i, char in enumerate(guess.chars):
        if char.colour == Colour.GREEN:
            # This char is in the correct position.
            # Remove any existing constraint on this char,
            # and add a constraint that this char must be in this position
            new_constraints = [
                constraint
                for constraint in new_constraints
                if constraint.char != char.letter
            ]
            new_constraints.append(
                Constraint(
                    char=char.letter,
                    positions={i},
                    type=ConstraintType.IN_SOME_POSITION,
                )
            )
        elif char.colour == Colour.YELLOW:
            # Add a constraint so that this char must be somewhere else in the word
            new_constraints.append(
                Constraint(
                    char=char.letter,
                    positions={j for j in range(word_length) if j != i},
                    type=ConstraintType.IN_SOME_POSITION,
                )
            )
            # Add a constraint so that this char is not in this position
            new_constraints.append(
                Constraint(
                    char=char.letter,
                    positions={i},
                    type=ConstraintType.NOT_IN_POSITIONS,
                )
            )
        elif char.colour == Colour.GREY:
            # We need to be a little cautious here.  A char could be grey because:
            # 1. It is not in the word at all.
            # 2. It is a duplicate letter in the guess and there are fewer instances of the letter in the solution.
            # To make sure we don't add an incorrect constraint, lets add a lighter constraint for duplicate chars

            char_is_duplicate = (
                Counter(char.letter for char in guess.chars)[char.letter] > 1
            )

            if char_is_duplicate:
                new_constraints.append(
                    Constraint(
                        char=char.letter,
                        positions={i},
                        type=ConstraintType.NOT_IN_POSITIONS,
                    )
                )
            else:
                # The char is not in the word at all.
                # Remove any existing constraints on this char
                new_constraints = [
                    constraint
                    for constraint in new_constraints
                    if constraint.char != char.letter
                ]
                # Add constraint so that the char is never included
                new_constraints.append(
                    Constraint(
                        char=char.letter,
                        positions=set(range(word_length)),
                        type=ConstraintType.NOT_IN_POSITIONS,
                    )
                )
        else:
            raise ValueError(f"Unexpected colour: {char.colour}")

    return new_constraints


def simulate(words: Optional[List[str]] = None) -> Tuple[bool, Optional[int]]:
    """Simulate a game of wordle and print results to terminal.

    A random word is chosen as the solution.
    Each new guess takes into account the constraints we have learned from previous guesses.
    """
    if words is None:
        words = get_words()

    puzzle = Puzzle(
        solution=random.choice(words),
        guesses=[],
    )
    print(f"\nCreated new puzzle with solution {puzzle.solution}")

    constraints = []

    while puzzle.is_in_progress:
        word_to_guess = get_word_to_guess(words, constraints)
        guess = puzzle.enter_word(word_to_guess)
        guess.print()

        if guess.is_correct:
            break

        constraints = update_constraints(constraints, guess, puzzle.WORD_LENGTH)

    if puzzle.won:
        num_guesses = len(puzzle.guesses)
        print(f"CORRECT! Took {num_guesses} guesses")
        return True, num_guesses
    else:
        print(f"Ran out of guesses")
        return False, None


def run_simulations(num_simulations: int) -> None:
    """Run multiple simulations and print summary statistics."""
    start_time = time.time()
    num_won = 0
    guess_nums = []
    words = get_words()

    for i in range(num_simulations):
        won, num_guesses = simulate(words)

        if won:
            num_won += 1

        if num_guesses is not None:
            guess_nums.append(num_guesses)

    run_time = round(time.time() - start_time, 3)
    print(f"\nRan {num_simulations} simulation(s) in {run_time} seconds.")
    win_percentage = round(100 * num_won / num_simulations, 2)
    print(f"Won {num_won}/{num_simulations} ({win_percentage} %)")
    median_num_guesses = round(statistics.mean(guess_nums), 2)
    print(f"Average number of guesses (for winning games): {median_num_guesses}")


if __name__ == "__main__":
    run_simulations(100)
