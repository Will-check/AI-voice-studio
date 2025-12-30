import os
from nicegui import ui
from nicegui_app.models.chatterbox_wrapper import LANGUAGES
from typing import List

DEFAULT_VOICE_LIBRARY = "./voice_library"
DEFAULT_PROJECT_DIRECTORY = "./projects"
DEFAULT_OUTPUT_DIRECTORY = "./output"

def update_language_dropdown(target_select: ui.select, model_name: str):
    if model_name == "Chatterbox":
        target_select.options = LANGUAGES
        if not target_select.value or target_select.value not in LANGUAGES:
            if "en" in LANGUAGES:
                target_select.value = "en"
            elif LANGUAGES:
                target_select.value = LANGUAGES[0]
        
        target_select.enable()
    else:
        target_select.options = []
        target_select.value = None
        target_select.disable()

    target_select.update()


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
    event, audio_player, player_container, uploader_container, base_path, profile_select=None,
):
    selected_file = event.value
    if selected_file:
        web_source = selected_file.replace("./", "/")
        full_path = os.path.join(base_path, web_source)

        audio_player.source = full_path
        audio_player.update()

        player_container.visible = True
        player_container.update()

        uploader_container.visible = False
        uploader_container.update()

        if profile_select:
            profile_select.value = None
            profile_select.update()
            