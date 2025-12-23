import os
from nicegui import ui
from typing import List

DEFAULT_VOICE_LIBRARY = "./voice_library"


def get_audio_files(directory_path: str = DEFAULT_VOICE_LIBRARY) -> List[str]:
    AUDIO_EXTENSIONS = (".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a")

    if not os.path.isdir(directory_path):
        print(f"Error: Directory '{directory_path}' does not exist.")
        return []

    audio_files: List[str] = []

    try:
        for filename in os.listdir(directory_path):
            full_path = os.path.join(directory_path, filename)

            if os.path.isfile(full_path) and filename.lower().endswith(
                AUDIO_EXTENSIONS
            ):
                audio_files.append(os.path.basename(full_path))

    except PermissionError:
        print(f"Error: Permission denied to read directory '{directory_path}'.")
        return []

    return audio_files


def update_audio_dropdown(
    target_select: ui.select, directory_path: str = DEFAULT_VOICE_LIBRARY
) -> None:
    files = get_audio_files(directory_path)

    if not files:
        target_select.options = {}
        target_select.value = None
    else:
        target_select.options = files

    target_select.update()


def load_audio_to_player(
    event, audio_player, player_container, uploader_container, profile_select=None
):
    selected_path = event.value
    if selected_path:
        web_source = selected_path.replace("./", "/")
        audio_player.source = web_source
        audio_player.update()

        player_container.visible = True
        player_container.update()

        uploader_container.visible = False
        uploader_container.update()

        if profile_select:
            profile_select.value = None
            profile_select.update()
