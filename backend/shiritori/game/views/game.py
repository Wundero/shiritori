from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.fields import CharField
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.viewsets import ReadOnlyModelViewSet

from shiritori.game.auth import RequiresSessionAuth
from shiritori.game.models import Game
from shiritori.game.serializers import (
    CreateStartGameSerializer,
    EmptySerializer,
    JoinGameSerializer,
    ShiritoriGameSerializer,
    ShiritoriTurnSerializer,
)
from shiritori.game.tasks import start_game_task

__all__ = ("GameViewSet",)


class GameViewSet(ReadOnlyModelViewSet):
    queryset = Game.objects.all()
    serializer_class = ShiritoriGameSerializer
    authentication_classes = []
    permission_classes = []

    def handle_exception(self, exc: Exception) -> Response:
        if isinstance(exc, ValidationError):
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"detail": exc.message})
        return super().handle_exception(exc)

    @staticmethod
    def get_success_headers(data):
        try:
            return {"Location": str(data[api_settings.URL_FIELD_NAME])}
        except (TypeError, KeyError):
            return {}

    def get_serializer_class(self):
        match self.action:
            case "create":
                return ShiritoriGameSerializer
            case "start":
                return CreateStartGameSerializer
            case "turn":
                return ShiritoriTurnSerializer
            case "join":
                return JoinGameSerializer
            case "leave":
                return EmptySerializer
            case _:
                return super().get_serializer_class()

    @extend_schema(responses={201: ShiritoriGameSerializer})
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_201_CREATED, data=serializer.data)

    @action(detail=True, methods=["post"], authentication_classes=[SessionAuthentication])
    def start(self, request, pk=None):
        game = self.get_object()
        session_key = request.session.session_key
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        game_settings = serializer.save()
        game.prepare_start(session_key, game_settings=game_settings)
        start_game_task.delay(game.id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], authentication_classes=[SessionAuthentication])
    def restart(self, request, pk=None):
        game = self.get_object()
        session_key = request.session.session_key
        game.restart(session_key)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={201: inline_serializer("Player", {"id": CharField(read_only=True)})})
    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        if not request.session or not request.session.session_key:
            request.session.save()

        game = self.get_object()
        serializer: JoinGameSerializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        player = game.join(player=serializer.validated_data["name"], session_key=request.session.session_key)

        headers = self.get_success_headers(serializer.validated_data)
        return Response(
            data={"id": player.id},
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @action(detail=True, methods=["post"], authentication_classes=[RequiresSessionAuth])
    def turn(self, request, pk=None):
        game = self.get_object()
        serializer: ShiritoriTurnSerializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        game.take_turn(request.session.session_key, **serializer.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], authentication_classes=[RequiresSessionAuth])
    @extend_schema(responses={204: {}})
    def leave(self, request, pk=None):
        session_key = request.session.session_key
        game = self.get_object()
        game.leave(session_key)
        return Response(status=status.HTTP_204_NO_CONTENT)
