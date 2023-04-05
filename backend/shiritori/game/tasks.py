import time

from celery import Task, shared_task
from channels.exceptions import ChannelFull
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.db.models import Q

from shiritori.game.events import send_game_updated
from shiritori.game.models import Game, Player, Word
from shiritori.game.utils import mock_stream_closer

__all__ = (
    "send_game_updated_task",
    "game_worker_task",
    "start_game_task",
    "load_dictionary_task",
    "player_disconnect_task",
)

TASK_TIME_LIMIT = 60 * 60 * 24  # 24 hours


@shared_task(
    max_retries=3,
    time_limit=TASK_TIME_LIMIT,
    soft_time_limit=TASK_TIME_LIMIT,
    ignore_result=True,
    throws=(ChannelFull,),
)
def send_game_updated_task(game_id):
    game = Game.objects.filter(id=game_id)
    if not game.exists():
        return
    send_game_updated(game.first())


@shared_task(
    time_limit=TASK_TIME_LIMIT,
    soft_time_limit=TASK_TIME_LIMIT,
    ignore_result=True,
    bind=True,
)
def game_worker_task(self: Task, game_id):
    mock_stream_closer()
    Game.objects.filter(~Q(task_id=self.request.id), id=game_id).update(task_id=self.request.id)
    try:
        Game.run_turn_loop(game_id, self.request.id)
        Game.objects.filter(id=game_id, task_id=self.request.id).update(task_id=None)
    except ValidationError:
        pass
    except OperationalError:
        self.retry(countdown=5)


@shared_task(
    time_limit=TASK_TIME_LIMIT,
    soft_time_limit=TASK_TIME_LIMIT,
    ignore_result=True,
)
def start_game_task(game_id):
    game = Game.get_startable_game_by_id(game_id)
    if not game.exists():
        return
    game.first().start()
    send_game_updated_task.delay(game_id)
    game_worker_task.delay(game_id)


@shared_task(
    time_limit=TASK_TIME_LIMIT,
    soft_time_limit=TASK_TIME_LIMIT,
    ignore_result=True,
)
def load_dictionary_task(locale: str = "en"):
    words = Word.load_dictionary(locale)
    return {"status": "success", "word_count": len(words), "locale": locale}


@shared_task(
    time_limit=TASK_TIME_LIMIT,
    soft_time_limit=TASK_TIME_LIMIT,
    ignore_result=True,
)
def player_disconnect_task(player_id: str):
    time.sleep(5 if settings.DEBUG else 60)
    if player := Player.objects.filter(id=player_id, is_connected=False).first():
        player.delete()
