import pytest
from django.core.exceptions import ValidationError

from shiritori.game.models import Game, Player


@pytest.mark.django_db
def test_play_game(game: Game, player: Player, player2: Player, sample_words: list[str]) -> None:
    """Test that a player can take a turn."""
    # Join the game
    game.join(player)
    game.join(player2)
    # Start the game
    game.start()
    # Take a turn
    turn_orders = [player, player2, player, player2]
    expected_score = [(9, 0), (9, 22), (20, 22)]  # Expected score after each turn
    for index, (turn_word, turn_player) in enumerate(zip(sample_words, turn_orders)):
        game.take_turn(turn_player.session_key, turn_word, 5)
        assert game.current_player == turn_orders[index + 1]
        assert game.last_word == turn_word
        assert game.current_turn == index + 1
        assert player.score == expected_score[index][0]
        assert player2.score == expected_score[index][1]
    # Take a turn with an invalid word
    with pytest.raises(ValidationError):
        game.take_turn(player2.session_key, "invalid", 5)
    # Take a turn using a word that's already used
    game.last_word = sample_words[0]
    with pytest.raises(ValidationError):
        game.take_turn(player2.session_key, sample_words[1], 5)
    assert game.current_player == player2
    game.leave(player2)
    # Since there's only 2 players and one leaves, the game should end
    assert game.is_finished
