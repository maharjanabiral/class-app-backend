import os
from dataclasses import dataclass
from app.core.config import settings
from livekit import api


@dataclass
class JoinCredentials:
    token: str
    ws_url: str
    room_name: str


def _client() -> api.LiveKitAPI:
    http_url = settings.LIVEKIT_URL.replace("wss://", "https://").replace("ws://", "http://")
    return api.LiveKitAPI(url=http_url, api_key=settings.LIVEKIT_API_KEY, api_secret=settings.LIVEKIT_API_SECRET)

async def create_room(room_name: str, empty_timeout_sec: int = 300) -> str:
    """Idempotent-ish room creation. LiveKit no-ops if the room already exists
    and is active, so this is safe to call defensively."""
    lkapi = _client()
    try:
        await lkapi.room.create_room(
            api.CreateRoomRequest(
                name=room_name,
                empty_timeout=empty_timeout_sec,
                max_participants=0,  # 0 = unlimited
            )
        )
    finally:
        await lkapi.aclose()
    return room_name


async def delete_room(room_name: str) -> None:
    lkapi = _client()
    try:
        await lkapi.room.delete_room(api.DeleteRoomRequest(room=room_name))
    finally:
        await lkapi.aclose()


async def start_recording(room_name: str, output_url: str) -> str:
    """Kicks off room composite recording. output_url is wherever your
    egress is configured to write to (S3/GCS bucket path). Returns the
    egress ID so you can correlate the completion webhook later."""
    lkapi = _client()
    try:
        req = api.RoomCompositeEgressRequest(
            room_name=room_name,
            layout="speaker",
            file_outputs=[api.EncodedFileOutput(filepath=output_url)],
        )
        egress_info = await lkapi.egress.start_room_composite_egress(req)
        return egress_info.egress_id
    finally:
        await lkapi.aclose()


def generate_student_token(room_name: str, user_id: int, display_name: str) -> JoinCredentials:
    token = (
        api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity(str(user_id))
        .with_name(display_name)
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
                can_publish_sources=["camera", "microphone", "screen_share"],
            )
        )
    )
    return JoinCredentials(token=token.to_jwt(), ws_url=settings.LIVEKIT_URL, room_name=room_name)


def generate_teacher_token(room_name: str, user_id: int, display_name: str) -> JoinCredentials:
    token = (
        api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity(str(user_id))
        .with_name(display_name)
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                room_admin=True,           # mute/remove participants
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
                can_publish_sources=["camera", "microphone", "screen_share"],
            )
        )
    )
    return JoinCredentials(token=token.to_jwt(), ws_url=settings.LIVEKIT_URL, room_name=room_name)
