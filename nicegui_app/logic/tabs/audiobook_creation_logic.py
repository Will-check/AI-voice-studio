import os
import json
import re
import numpy as np
import scipy.io.wavfile as wavfile
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple

from nicegui import run
from nicegui_app.logic.app_state import get_state
from nicegui_app.models.chatterbox_wrapper import (
    generate_tts_audio,
    MAX_CHARS as CHATTERBOX_MAX_CHARS,
)
from nicegui_app.logic.common_logic import (
    DEFAULT_PROJECT_DIRECTORY,
    DEFAULT_OUTPUT_DIRECTORY,
)


def _split_text_preserving_words(text: str, max_length: int) -> List[str]:
    text = text.strip()
    if len(text) <= max_length:
        return [text]

    chunks = []
    while len(text) > max_length:
        split_index = text[:max_length].rfind(" ")

        if split_index == -1:
            # Sanity check, probably impossible situation where we have 1 large word
            # We're cutting hard on the limit
            split_index = max_length

        chunk = text[:split_index].strip()
        if chunk:
            chunks.append(chunk)

        text = text[split_index:].strip()

    if text:
        chunks.append(text)

    return chunks


@dataclass
class LineData:
    speaker: str
    text: str
    voice: Optional[str]
    file_name: Optional[str] = None
    pause: float = 0.5


def ensure_project_exists(
    project_name: str, directory_path: str = DEFAULT_PROJECT_DIRECTORY
):
    if not project_name:
        return
    project_path = os.path.join(directory_path, project_name)
    if not os.path.isdir(project_path):
        os.makedirs(project_path)
        return True
    return False


def get_existing_projects(directory_path: str = DEFAULT_PROJECT_DIRECTORY) -> List[str]:
    if not os.path.isdir(directory_path):
        os.makedirs(directory_path)

    projects_list = [
        name
        for name in os.listdir(directory_path)
        if os.path.isdir(os.path.join(directory_path, name))
    ]

    return projects_list


def load_project_metadata(project_name: str) -> List[LineData]:
    if not project_name:
        return []

    project_path = os.path.join(DEFAULT_PROJECT_DIRECTORY, project_name)
    metadata_path = os.path.join(project_path, "metadata.json")

    if not os.path.exists(metadata_path):
        return []

    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return [
            LineData(
                speaker=entry.get("speaker", "Unknown"),
                text=entry.get("text", ""),
                voice=entry.get("voice"),
                file_name=entry.get("file_name"),
                pause=entry.get("pause", 0.5),
            )
            for entry in data
        ]
    except Exception as e:
        print(f"Error loading metadata: {e}")
        return []


def update_metadata_entry(project_name, file_name, new_text, new_voice, new_params):
    project_path = os.path.join(DEFAULT_PROJECT_DIRECTORY, project_name)
    metadata_path = os.path.join(project_path, "metadata.json")

    if not os.path.exists(metadata_path):
        return

    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        updated = False
        for entry in data:
            if entry.get("file_name") == file_name:
                entry["text"] = new_text
                entry["voice"] = new_voice
                entry["params"] = new_params
                updated = True
                break

        if updated:
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

    except Exception as e:
        print(f"Error updating metadata: {e}")


def cleanup_temp_files(project_name: str):
    if not project_name:
        return

    project_path = os.path.join(DEFAULT_PROJECT_DIRECTORY, project_name)
    if not os.path.exists(project_path):
        return

    count = 0
    try:
        for filename in os.listdir(project_path):
            if filename.startswith("temp_"):
                file_path = os.path.join(project_path, filename)
                try:
                    os.remove(file_path)
                    count += 1
                except OSError as e:
                    print(f"Error removing temp file {filename}: {e}")

        if count > 0:
            print(f"Cleaned up {count} temporary files in project '{project_name}'.")

    except Exception as e:
        print(f"Error during cleanup: {e}")


def get_current_model_max_chars() -> int:
    app_state = get_state()
    model_name = app_state.active_model

    if model_name == "Chatterbox":
        return CHATTERBOX_MAX_CHARS

    return 300


def parse_lines(
    script: str,
    is_single_mode: bool,
    single_voice: str,
    voice_map: Dict[str, str],
    max_chars,
) -> List[LineData]:
    results = []
    for line in script.split("\n"):
        line = line.strip()
        if not line:
            continue

        if is_single_mode:
            chunks = _split_text_preserving_words(line, max_chars)
            for chunk in chunks:
                results.append(
                    LineData(speaker="Single voice", text=chunk, voice=single_voice)
                )
        else:
            match = re.match(r"^\s*\[([A-Za-z0-9\s]+)\]\s*(.*)", line)
            if match:
                speaker, text = [x.strip() for x in match.groups()]
                voice = voice_map.get(speaker.capitalize())
                chunks = _split_text_preserving_words(text, max_chars)

                for chunk in chunks:
                    results.append(LineData(speaker=speaker, text=chunk, voice=voice))
            else:
                # Optional handling of error line
                pass

    return results



def get_next_sequence_number(metadata_list: List[Dict], project_name: str) -> int:
    max_num = 0
    pattern = re.compile(rf"{re.escape(project_name)}_(\d+)")

    for entry in metadata_list:
        fname = entry.get("file_name", "")
        match = pattern.search(fname)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num

    return max_num + 1


def generate_and_save_audio(
    text: str, voice_path: str, output_path: str, language: str, controls: dict
):
    sr, audio_array = generate_tts_audio(
        text_input=text,
        language_id=language,
        audio_prompt_path_input=voice_path,
        exaggeration_input=controls["exaggeration"],
        temperature_input=controls["temperature"],
        seed_num_input=int(controls["seed"]),
        cfg_input=controls["cfg"],
        repetition_penalty_input=controls["repetition_penalty"],
        min_p_input=controls["min_p"],
        top_p_input=controls["top_p"],
    )
    wavfile.write(output_path, sr, audio_array)

    return {k: v for k, v in controls.items()}


def merge_and_save_audio(project_name: str, ui_lines: List[LineData]) -> Optional[str]:
    if not ui_lines:
        raise ValueError("No speaker lines available.")

    if not project_name:
        raise ValueError("No project selected.")

    metadata_lines = load_project_metadata(project_name)
    if not metadata_lines:
        raise ValueError("Project is empty or metadata missing.")

    ui_pauses = {line.file_name: line.pause for line in ui_lines if line.file_name}
    project_path = os.path.join(DEFAULT_PROJECT_DIRECTORY, project_name)

    if not os.path.exists(DEFAULT_OUTPUT_DIRECTORY):
        os.makedirs(DEFAULT_OUTPUT_DIRECTORY)

    combined_audio = []
    sample_rate = None

    for line in metadata_lines:
        if not line.file_name:
            continue

        file_path = os.path.join(project_path, line.file_name)
        if not os.path.exists(file_path):
            print(f"Skipping missing file: {line.file_name}")
            continue

        try:
            sr, data = wavfile.read(file_path)

            if sample_rate is None:
                sample_rate = sr

            combined_audio.append(data)
            pause_duration = ui_pauses.get(line.file_name, line.pause)

            if pause_duration > 0:
                silence_samples = int(pause_duration * sample_rate)
                if silence_samples > 0:
                    silence = np.zeros(silence_samples, dtype=data.dtype)
                    combined_audio.append(silence)

        except Exception as e:
            print(f"Error processing {line.file_name}: {e}")

    if not combined_audio:
        raise ValueError("No valid audio files found to merge.")

    final_wave = np.concatenate(combined_audio)
    output_filename = f"{project_name}_merged.wav"
    output_path = os.path.join(DEFAULT_OUTPUT_DIRECTORY, output_filename)

    wavfile.write(output_path, sample_rate, final_wave)
    return output_filename
