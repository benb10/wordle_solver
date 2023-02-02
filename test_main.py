from main import Colour, Guess


def test_create_guess_from_word_green():
    guess = Guess.create_from_word("abbbb", "acccc")
    assert [char.letter for char in guess.chars] == ["a", "b", "b", "b", "b"]
    assert [char.colour for char in guess.chars] == [
        Colour.GREEN,
        Colour.GREY,
        Colour.GREY,
        Colour.GREY,
        Colour.GREY,
    ]


def test_create_guess_from_word_yellow():
    guess = Guess.create_from_word("abbbb", "cccac")
    assert [char.colour for char in guess.chars] == [
        Colour.YELLOW,
        Colour.GREY,
        Colour.GREY,
        Colour.GREY,
        Colour.GREY,
    ]


def test_create_guess_from_word_duplicate_chars():
    guess = Guess.create_from_word("boots", "piano")
    # First "o" should be yellow and second "o" should be grey.
    # See examples here https://nerdschalk.com/wordle-same-letter-twice-rules-explained-how-does-it-work/
    assert [char.colour for char in guess.chars] == [
        Colour.GREY,
        Colour.YELLOW,
        Colour.GREY,
        Colour.GREY,
        Colour.GREY,
    ]
