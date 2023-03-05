from typing import Iterable, Optional, Union

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import QuerySet, Sum, F, Q, Count

from shiritori.game.utils import calculate_score, generate_random_letter
from shiritori.utils import NanoIdField
from shiritori.utils.abstract_model import AbstractModel, NanoIdModel


class GameStatus(models.TextChoices):
    WAITING = 'WAITING', 'Waiting'
    PLAYING = 'PLAYING', 'Playing'
    FINISHED = 'FINISHED', 'Finished'


class GameLocales(models.TextChoices):
    EN = 'en', 'English'


class PlayerType(models.TextChoices):
    HOST = 'HOST', 'host'
    HUMAN = 'HUMAN', 'human'
    BOT = 'BOT', 'bot'
    SPECTATOR = 'SPECTATOR', 'spectator'


class Game(AbstractModel):  # pylint: disable=too-many-public-methods
    id: int = NanoIdField(max_length=5)
    status: str = models.CharField(
        max_length=8,
        choices=GameStatus.choices,
        default=GameStatus.WAITING,
    )
    current_turn: int = models.IntegerField(default=0)
    current_player: Optional['Player'] = models.ForeignKey(
        'Player',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_player',
    )
    winner: Optional['Player'] = models.ForeignKey(
        'Player',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='winner',
    )
    settings: Optional['GameSettings'] = models.ForeignKey(
        'GameSettings',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    turn_time_left: int | F = models.IntegerField(default=0)
    last_word: str = models.CharField(max_length=255, null=True, blank=True, default=generate_random_letter)

    class Meta:
        ordering = ('-created_at',)
        db_table = 'game'

    def __str__(self) -> str:
        return f'Game {self.id}'

    @staticmethod
    def get_start_able_games() -> 'QuerySet[Game]':
        """
        Get a QuerySet of games that can be started.
        :return: QuerySet[Game]
        """
        player_filter = Q(player__type=PlayerType.HUMAN) | Q(player__type=PlayerType.HOST)
        return Game.objects.annotate(
            total_players=Count('player', filter=player_filter)
        ).filter(status=GameStatus.WAITING, total_players=2)

    @staticmethod
    def get_startable_game_by_id(game_id: str) -> 'QuerySet[Game]':
        """
        Get a queryset of a Game that can be started by ID.
        :param game_id: str - Game ID
        :return: QuerySet[Game]
        """
        return Game.get_start_able_games().filter(id=game_id)

    @property
    def players(self) -> 'QuerySet[Player]':
        return self.player_set.all().exclude(type=PlayerType.SPECTATOR)

    @property
    def words(self) -> 'QuerySet[GameWord]':
        return self.gameword_set.all()

    @property
    def host(self) -> Optional['Player']:
        return self.player_set.filter(type=PlayerType.HOST).first()

    @property
    def player_count(self) -> int:
        return self.players.count()

    @property
    def word_count(self) -> int:
        return self.gameword_set.count()

    @property
    def last_used_word(self) -> Optional['GameWord']:
        return self.gameword_set.last()

    @property
    def is_finished(self) -> bool:
        return self.status == GameStatus.FINISHED

    @is_finished.setter
    def is_finished(self, value: bool) -> None:
        self.status = GameStatus.FINISHED if value else GameStatus.PLAYING

    @property
    def is_started(self) -> bool:
        return self.status == GameStatus.PLAYING

    @property
    def leaderboard(self) -> QuerySet['Player']:
        return self.player_set.annotate(
            total_score=Sum('gameword__score'),
        ).order_by('-total_score')

    def save(
        self,
        force_insert: bool = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        has_settings_changed = False
        if self.settings is None:
            self.settings = GameSettings.objects.create()
            has_settings_changed = True
        if self.settings and not self.settings.pk:
            self.settings.save()
            has_settings_changed = True
        if (
            has_settings_changed
            and update_fields
            and isinstance(update_fields, list)
            and 'settings' not in update_fields
        ):
            update_fields.append('settings')
        super().save(force_insert, force_update, using, update_fields)

    def join(self, player: Union['Player', str]) -> 'Player':
        """Add a player to the game."""
        if self.is_started or self.is_finished:
            raise ValidationError('Game has already started or is finished.')
        if isinstance(player, str):
            player = Player(name=player, game=self, type=PlayerType.HUMAN if self.player_count > 0 else PlayerType.HOST)
        else:
            player.game = self
            player.type = PlayerType.HUMAN if self.player_count > 0 else PlayerType.HOST
        player.save(update_fields=['name', 'game', 'type', 'session_key'])
        return player

    def leave(self, player: Union['Player', str]) -> None:
        """Remove a player from the game."""
        if isinstance(player, str):
            player = self.player_set.get(session_key=player)
        player.delete()
        if player.type == PlayerType.HOST:
            try:
                self.recalculate_host()
            except ValidationError:
                self.status = GameStatus.FINISHED
        if self.status == GameStatus.PLAYING:
            try:
                self.calculate_current_player(save=False)
            except ValidationError:
                self.status = GameStatus.FINISHED
        self.save(update_fields=['status', 'current_player'])

    def start(self, session_key: str = None, *, save: bool = True) -> None:
        """
        Start the game.
        :param session_key: str - The session key of the player starting the game.
        :param save: bool - Whether to save the game after starting.
        :return: None
        :raises ValidationError: If there are less than 2 players in the game.
        """
        if self.status != GameStatus.WAITING:
            raise ValidationError('Cannot start a game that is not waiting.')
        if session_key and self.host.session_key != session_key:
            raise ValidationError('Only the host can start the game.')
        if self.player_count < 2:
            raise ValidationError('Cannot start a game with less than 2 players.')
        self.status = GameStatus.PLAYING
        self.calculate_current_player(save=False)
        self.turn_time_left = self.settings.turn_time
        if save:
            self.save(update_fields=['status', 'current_player', 'turn_time_left'])

    def calculate_current_player(self, *, save: bool = True) -> None:
        """
        Calculates the current player given the current turn.
        :param save: bool - Whether to save the game after calculating the current player.
        :return: None
        :raises ValidationError: If there are no players in the game.
        """
        player_count = self.player_count
        if player_count == 0:
            raise ValidationError('Cannot calculate current player when there are no players.')
        if player_count == 1:
            raise ValidationError('Cannot calculate current player when there is only 1 player.')

        if self.current_turn == 0:
            self.current_player = self.host
        else:
            self.current_player = self.players[self.current_turn % self.player_count]

        if save:
            self.save(update_fields=['current_player'])

    def recalculate_host(self, *, save: bool = True) -> None:
        """
        Recalculates the host of the game.
        :param save: bool - Whether to save the game after recalculating the host.
        :return: None
        :raises ValidationError: If there are no players in the game.
        """
        host = self.host
        players = self.players

        # If no players raise ValidationError
        if not players.exists():
            raise ValidationError('Cannot recalculate host when there are no players.')

        if not host:
            if first := self.players.first():
                first.type = PlayerType.HOST
                if save:
                    first.save(update_fields=['type'])

    def can_take_turn(self, session_key: str, *, timeout: bool = False) -> None:
        """
        Checks if a player can take a turn.
        Checks the following criteria:
        1. The game is in progress.
        2. The player is the current player.
        3. The player has not exceeded their turn time.

        :param session_key: str - The session key of the player.
        :param timeout: bool - Whether to check if the player has exceeded their turn time.
        :return: None
        :raises ValidationError: If the player cannot take a turn.
        """
        if self.status != GameStatus.PLAYING:
            raise ValidationError('Game is not in progress.')
        if self.current_player.session_key != session_key:
            raise ValidationError('It is not your turn.')
        if not timeout and self.turn_time_left <= 0:
            raise ValidationError('Turn time has expired.')

    def take_turn(self, session_key: str, word: str | None, duration: int, *, save: bool = True) -> None:
        """
        Take a turn in the game.
        :param session_key: The session key of the player requesting to take a turn.
        :param word: The word the player submitted.
        :param duration: The duration of the turn.
        :param save: bool - Whether to save the game after taking the turn.
        :return: None
        :raises ValidationError: If the player cannot take a turn.
        """
        timed_out = self.turn_time_left <= 0
        self.can_take_turn(session_key, timeout=timed_out)
        game_word = GameWord(
            game=self,
            player=self.current_player,
            word=word,
            duration=duration,
        )
        game_word.save()
        if word:
            self.last_word = word
        if self.current_turn + 1 > self.settings.max_turns:
            self.status = GameStatus.FINISHED
            self.save(update_fields=['status', 'last_word', 'current_turn'])
            return
        self.current_turn += 1
        self.calculate_current_player(save=False)
        self.turn_time_left = self.settings.turn_time
        if save:
            self.save(
                update_fields=[
                    'current_turn',
                    'last_word',
                    'turn_time_left',
                    'current_player'
                ]
            )

    def end_turn(self, duration: int = None) -> None:
        """
        End the current turn. and start the next turn.
        This is usually called when the turn time has expired.

        This will submit an empty word and a duration of 0.
        Resulting in a negative score.

        :param duration: The duration of the turn. Defaults to the turn time of the game.
        :return: None
        """
        duration = duration or self.settings.turn_time
        self.take_turn(self.current_player.session_key, None, duration)

    def get_winner(self) -> Optional['Player']:
        """
        Get the winner of the game.
        To be called when the game is finished.
        For a player to be determined as the winner they must have the highest score.

        :return: Optional[Player] - The winner of the game.
        :raises ValidationError: If the game is not finished or started.
        """
        if not self.is_finished:
            raise ValidationError('Cannot get winner of a game that is not finished.')
        if not self.is_started:
            raise ValidationError('Cannot get winner of a game that has not started.')

        return self.leaderboard.first()


class Player(AbstractModel, NanoIdModel):
    name = models.CharField(max_length=255)
    game = models.ForeignKey(
        'Game',
        on_delete=models.CASCADE,
        null=True,
    )
    type = models.CharField(
        max_length=10,
        choices=PlayerType.choices,
        default=PlayerType.HUMAN,
    )
    session_key = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'player'
        constraints = [
            models.UniqueConstraint(name='unique_session_key', fields=['game', 'session_key'], ),
            models.UniqueConstraint(name='unique_name', fields=['game', 'name'], ),
            # There can only be one host per game.
            models.UniqueConstraint(name='unique_host',
                                    fields=['game', 'type'], condition=models.Q(type=PlayerType.HOST),
                                    ),
        ]
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['game', 'type']),
            models.Index(fields=['game', 'session_key']),
            models.Index(fields=['game', 'name'])
        ]

    def __str__(self):
        return self.name

    @property
    def score(self):
        return self.gameword_set.aggregate(models.Sum('score')).get('score__sum') or 0

    @property
    def words(self) -> 'QuerySet[GameWord]':
        return self.gameword_set.all()


class GameWord(NanoIdModel):
    word = models.CharField(max_length=255, null=True, blank=True)
    score = models.FloatField(default=0)
    game = models.ForeignKey(
        'Game',
        on_delete=models.CASCADE,
    )
    player = models.ForeignKey(
        'Player',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    duration = models.FloatField(default=0)

    class Meta:
        db_table = 'game_word'
        indexes = [
            models.Index(fields=['game', 'player']),
            models.Index(fields=['game', 'word']),
            models.Index(fields=['game', 'score']),
            models.Index(fields=['player', 'score', 'word'])
        ]
        constraints = [
            models.UniqueConstraint(name='unique_word', fields=['game', 'word'],
                                    condition=models.Q(word__isnull=False)),
        ]

    @property
    def calculated_score(self):
        return calculate_score(self.word, self.duration)

    def save(
        self,
        force_insert: bool = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        if self.word:
            self.word = self.word.lower()  # Normalize the word.
            if not self.validate():
                raise ValidationError(f'Word "{self.word}" is not valid for locale "{self.game.settings.locale}"')
            self.score = self.calculated_score
        else:
            self.score = -.25 * self.duration
        super().save(force_insert, force_update, using, update_fields)

    def validate(self) -> bool:
        """
        Validates that the word meets the following criteria:

        1. The word starts with the last word's last letter.
        2. The word is not already in the game.
        3. The word is in the dictionary for the game's locale.

        :return: bool - Whether the word is valid.
        """
        if self.game.last_word and self.word[0] != self.game.last_word[-1]:
            return False
        if self.game.gameword_set.filter(word=self.word).exists():
            return False
        if len(self.word) < self.game.settings.word_length:
            return False
        return Word.validate(self.word, self.game.settings.locale)


class GameSettings(NanoIdModel):
    locale = models.CharField(max_length=10, choices=GameLocales.choices, default=GameLocales.EN)
    word_length = models.IntegerField(default=3, validators=[MinValueValidator(3), MaxValueValidator(5)])
    turn_time = models.IntegerField(default=60, validators=[MinValueValidator(30), MaxValueValidator(120)])
    max_turns = models.IntegerField(default=10, validators=[MinValueValidator(5), MaxValueValidator(20)])

    class Meta:
        db_table = 'game_settings'

    @staticmethod
    def get_default_settings() -> dict:
        all_fields = GameSettings._meta.get_fields()  # noqa pylint: disable=protected-access
        fields = filter(lambda f: hasattr(f, 'default') and f.name != 'id', all_fields)
        # inspect the fields and create a dict of the defaults.
        return {field.name: field.default for field in fields}

    @classmethod
    def from_defaults(cls) -> 'GameSettings':
        return cls.objects.create(**cls.get_default_settings())


class Word(models.Model):
    word = models.CharField(max_length=255)
    locale = models.CharField(max_length=10, choices=GameLocales.choices, default=GameLocales.EN)

    class Meta:
        db_table = 'word'
        indexes = [
            models.Index(fields=['word', 'locale']),
            models.Index(fields=['locale']),
            models.Index(fields=['word']),
        ]
        constraints = [
            models.UniqueConstraint(name='unique_word_locale', fields=['word', 'locale']),
        ]

    def __str__(self):
        return f"{self.word} ({self.locale})"

    @classmethod
    def validate(cls, word: str, locale: GameLocales | str = GameLocales.EN) -> bool:
        """Validate that the word is in the dictionary for the given locale."""
        return cls.objects.filter(word__iexact=word, locale=locale).exists()
