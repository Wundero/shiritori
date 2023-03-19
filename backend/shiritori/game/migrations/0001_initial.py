# Generated by Django 4.1.7 on 2023-03-10 23:17

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models

import shiritori.game.utils
import shiritori.utils.id_generator
import shiritori.utils.nano_id_field


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Game",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    shiritori.utils.nano_id_field.NanoIdField(
                        default=shiritori.utils.id_generator.generate_id,
                        editable=False,
                        max_length=5,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("WAITING", "Waiting"),
                            ("PLAYING", "Playing"),
                            ("FINISHED", "Finished"),
                        ],
                        default="WAITING",
                        max_length=8,
                    ),
                ),
                ("current_turn", models.IntegerField(default=0)),
                ("turn_time_left", models.IntegerField(default=0)),
                (
                    "last_word",
                    models.CharField(
                        blank=True,
                        default=shiritori.game.utils.generate_random_letter,
                        max_length=255,
                        null=True,
                    ),
                ),
            ],
            options={
                "db_table": "game",
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="GameSettings",
            fields=[
                (
                    "id",
                    shiritori.utils.nano_id_field.NanoIdField(
                        default=shiritori.utils.id_generator.generate_id,
                        editable=False,
                        max_length=21,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                (
                    "locale",
                    models.CharField(choices=[("en", "English")], default="en", max_length=10),
                ),
                (
                    "word_length",
                    models.IntegerField(
                        default=3,
                        validators=[
                            django.core.validators.MinValueValidator(3),
                            django.core.validators.MaxValueValidator(5),
                        ],
                    ),
                ),
                (
                    "turn_time",
                    models.IntegerField(
                        default=60,
                        validators=[
                            django.core.validators.MinValueValidator(30),
                            django.core.validators.MaxValueValidator(120),
                        ],
                    ),
                ),
                (
                    "max_turns",
                    models.IntegerField(
                        default=10,
                        validators=[
                            django.core.validators.MinValueValidator(5),
                            django.core.validators.MaxValueValidator(20),
                        ],
                    ),
                ),
            ],
            options={
                "db_table": "game_settings",
            },
        ),
        migrations.CreateModel(
            name="GameWord",
            fields=[
                (
                    "id",
                    shiritori.utils.nano_id_field.NanoIdField(
                        default=shiritori.utils.id_generator.generate_id,
                        editable=False,
                        max_length=21,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("word", models.CharField(blank=True, max_length=255, null=True)),
                ("score", models.FloatField(default=0)),
                ("duration", models.FloatField(default=0)),
            ],
            options={
                "db_table": "game_word",
            },
        ),
        migrations.CreateModel(
            name="Player",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    shiritori.utils.nano_id_field.NanoIdField(
                        default=shiritori.utils.id_generator.generate_id,
                        editable=False,
                        max_length=21,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("HUMAN", "human"),
                            ("BOT", "bot"),
                            ("SPECTATOR", "spectator"),
                            ("WINNER", "winner"),
                        ],
                        default="HUMAN",
                        max_length=25,
                    ),
                ),
                ("is_current", models.BooleanField(default=False)),
                ("is_host", models.BooleanField(default=False)),
                (
                    "session_key",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
            ],
            options={
                "db_table": "player",
                "ordering": ["created_at"],
            },
        ),
        migrations.CreateModel(
            name="Word",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("word", models.CharField(max_length=255)),
                (
                    "locale",
                    models.CharField(choices=[("en", "English")], default="en", max_length=10),
                ),
            ],
            options={
                "db_table": "word",
            },
        ),
        migrations.AddIndex(
            model_name="word",
            index=models.Index(fields=["word", "locale"], name="word_word_6db7bd_idx"),
        ),
        migrations.AddIndex(
            model_name="word",
            index=models.Index(fields=["locale"], name="word_locale_6dbaa7_idx"),
        ),
        migrations.AddIndex(
            model_name="word",
            index=models.Index(fields=["word"], name="word_word_4bc093_idx"),
        ),
        migrations.AddConstraint(
            model_name="word",
            constraint=models.UniqueConstraint(fields=("word", "locale"), name="unique_word_locale"),
        ),
        migrations.AddField(
            model_name="player",
            name="game",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to="game.game"),
        ),
        migrations.AddField(
            model_name="gameword",
            name="game",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="game.game"),
        ),
        migrations.AddField(
            model_name="gameword",
            name="player",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="game.player",
            ),
        ),
        migrations.AddField(
            model_name="game",
            name="settings",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="game.gamesettings",
            ),
        ),
        migrations.AddIndex(
            model_name="player",
            index=models.Index(fields=["game", "type"], name="player_game_id_9256ce_idx"),
        ),
        migrations.AddIndex(
            model_name="player",
            index=models.Index(fields=["game", "session_key"], name="player_game_id_d5f250_idx"),
        ),
        migrations.AddIndex(
            model_name="player",
            index=models.Index(fields=["game", "name"], name="player_game_id_8e0217_idx"),
        ),
        migrations.AddConstraint(
            model_name="player",
            constraint=models.UniqueConstraint(fields=("game", "session_key"), name="unique_session_key"),
        ),
        migrations.AddConstraint(
            model_name="player",
            constraint=models.UniqueConstraint(fields=("game", "name"), name="unique_name"),
        ),
        migrations.AddConstraint(
            model_name="player",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_current", True)),
                fields=("game", "is_current"),
                name="unique_current_player",
            ),
        ),
        migrations.AddConstraint(
            model_name="player",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_host", True)),
                fields=("game", "is_host"),
                name="unique_host",
            ),
        ),
        migrations.AddConstraint(
            model_name="player",
            constraint=models.UniqueConstraint(
                condition=models.Q(("type", "WINNER")),
                fields=("game", "type"),
                name="unique_winner",
            ),
        ),
        migrations.AddIndex(
            model_name="gameword",
            index=models.Index(fields=["game", "player"], name="game_word_game_id_33ec00_idx"),
        ),
        migrations.AddIndex(
            model_name="gameword",
            index=models.Index(fields=["game", "word"], name="game_word_game_id_93ffb9_idx"),
        ),
        migrations.AddIndex(
            model_name="gameword",
            index=models.Index(fields=["game", "score"], name="game_word_game_id_4e0b0c_idx"),
        ),
        migrations.AddIndex(
            model_name="gameword",
            index=models.Index(fields=["player", "score", "word"], name="game_word_player__dac2d0_idx"),
        ),
        migrations.AddConstraint(
            model_name="gameword",
            constraint=models.UniqueConstraint(
                condition=models.Q(("word__isnull", False)),
                fields=("game", "word"),
                name="unique_word",
            ),
        ),
    ]
