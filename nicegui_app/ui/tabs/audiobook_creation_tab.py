from dataclasses import dataclass
from typing import Optional, List, Dict

from nicegui import ui, run
from nicegui_app.logic.app_state import get_state
from nicegui_app.models.chatterbox_wrapper import generate_tts_audio
from nicegui_app.logic.common_logic import (
    get_audio_files,
    update_language_dropdown,
    DEFAULT_PROJECT_DIRECTORY,
    DEFAULT_VOICE_LIBRARY,
)
from nicegui_app.ui.common_ui import (
    get_bound_model_column,
    render_saved_profiles_dropdown,
)
from nicegui_app.ui.models.chatterbox_ui import chatterbox_controls
from nicegui_app.ui.styles import Style

import json
import os
import re
import scipy.io.wavfile as wavfile
import time


@dataclass
class LineData:
    speaker: str
    text: str
    voice: Optional[str]
    file_name: Optional[str] = None
    pause: float = 0.5


def _ensure_project_exists(
    project_name: str, directory_path: str = DEFAULT_PROJECT_DIRECTORY
):
    if not project_name:
        return
    project_path = os.path.join(directory_path, project_name)
    if not os.path.isdir(project_path):
        os.makedirs(project_path)
        ui.notify(f"Created new project: {project_name}", type="positive")


def _load_project_metadata(project_name: str) -> List[LineData]:
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
        ui.notify(f"Error loading metadata: {e}", type="negative")
        return []


def on_project_change(
    event, lines_container: ui.column, directory_path: str = DEFAULT_PROJECT_DIRECTORY
):
    project_name = event.value

    _ensure_project_exists(project_name=project_name)

    loaded_lines = _load_project_metadata(project_name)
    _render_lines_grid(lines_container, loaded_lines, project_name)


def get_existing_projects(directory_path: str = DEFAULT_PROJECT_DIRECTORY) -> List[str]:
    if not os.path.isdir(directory_path):
        os.makedirs(directory_path)

    projects_list = [
        name
        for name in os.listdir(directory_path)
        if os.path.isdir(os.path.join(directory_path, name))
    ]

    return projects_list


def refresh_project_options(select_element: ui.select):
    current_projects = get_existing_projects()
    select_element.options = current_projects
    select_element.update()


def _get_voice_map_from_ui(container: ui.column) -> Dict[str, str]:
    voice_map = {}
    if not hasattr(container, "default_slot"):
        return voice_map

    for row in container.default_slot.children:
        speaker_lbl = next(
            (c for c in row.default_slot.children if isinstance(c, ui.label)), None
        )
        voice_sel = next(
            (c for c in row.default_slot.children if isinstance(c, ui.select)), None
        )

        if speaker_lbl and voice_sel and voice_sel.value:
            voice_map[speaker_lbl.text] = voice_sel.value
    return voice_map


def _parse_lines(
    script: str, is_single_mode: bool, single_voice: str, voice_map: Dict[str, str]
) -> List[LineData]:
    results = []
    for line in script.split("\n"):
        line = line.strip()
        if not line:
            continue

        if is_single_mode:
            results.append(
                LineData(speaker="Single voice", text=line, voice=single_voice)
            )
        else:
            match = re.match(r"^\s*\[([A-Za-z0-9\s]+)\]\s*(.*)", line)
            if match:
                speaker, text = [x.strip() for x in match.groups()]
                voice = voice_map.get(speaker.capitalize())
                results.append(LineData(speaker=speaker, text=text, voice=voice))
            else:
                ui.notify(f"Skipped line without tag: {line}", type="negative")

    return results


def _render_line_row(item: LineData, project_name: str):
    with ui.row().classes(Style.centered_row):
        ui.checkbox()

    ui.label(item.speaker).classes("text-center")

    ui.select(options=get_audio_files(), value=item.voice).classes("w-full").props(
        "outlined dense"
    )

    def play_line():
        if not item.file_name:
            ui.notify("No audio file generated for this line.", type="warning")
            return

        # Adding ?t=time, to bypass browser cache
        source_url = f"/projects/{project_name}/{item.file_name}?t={time.time()}"

        ui.run_javascript(
            f"""
            if (window.currentAudio) {{
                window.currentAudio.pause();
                window.currentAudio.currentTime = 0;
            }}
            window.currentAudio = new Audio("{source_url}");
            window.currentAudio.play();
        """
        )

    with ui.row().classes(Style.centered_row):
        ui.button(icon="play_arrow", on_click=play_line).props(
            "flat round color=primary"
        )

    with ui.row().classes(Style.centered_row):
        ui.button(
            icon="sync", on_click=lambda: ui.notify(f"Regen {item.speaker}")
        ).props("flat round color=secondary")

    ui.number(value=0.5, format="%.1f", step=0.1, min=0).classes("w-full").props(
        "outlined dense"
    )

    ui.label(item.text).classes("text-left")

    ui.separator().classes("col-span-full")


def _render_lines_grid(container: ui.column, lines: List[LineData], project_name: str):
    container.clear()

    if not lines:
        return

    with container:
        ui.label(f"Project content ({len(lines)} lines):").classes(Style.standard_label)

        cols = "auto 130px minmax(150px, 1fr) auto auto 110px 3fr"
        with ui.grid(columns=cols).classes("items-center w-full gap-x-10 gap-y-1"):
            headers = [
                "Exclude",
                "Speaker",
                "Voice",
                "▶ Play",
                "🔁 Regen",
                "Pause [s]",
                "Line text",
            ]
            for h in headers:
                ui.label(h).classes(
                    Style.list_header_center
                    if h != "Line text"
                    else Style.list_header_left
                )
            ui.separator().classes("my-1 col-span-full")

            for item in lines:
                _render_line_row(item, project_name)


def _get_next_sequence_number(metadata_list: List[Dict], project_name: str) -> int:
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


def _generate_and_save_task(
    text: str, voice_path: str, output_path: str, language: str, controls: dict
):
    exaggeration = controls["exaggeration"].value
    temperature = controls["temperature"].value
    cfg_val = controls["cfg"].value
    seed_val = int(controls["seed"].value)
    top_p_val = controls["top_p"].value
    min_p_val = controls["min_p"].value
    rep_penalty_val = controls["repetition_penalty"].value

    sr, audio_array = generate_tts_audio(
        text_input=text,
        language_id=language,
        audio_prompt_path_input=voice_path,
        exaggeration_input=exaggeration,
        temperature_input=temperature,
        seed_num_input=seed_val,
        cfg_input=cfg_val,
        repetition_penalty_input=rep_penalty_val,
        min_p_input=min_p_val,
        top_p_input=top_p_val,
    )

    wavfile.write(output_path, sr, audio_array)

    return {
        "language": language,
        "temperature": temperature,
        "exaggeration": exaggeration,
        "cfg": cfg_val,
        "seed": seed_val,
        "top_p": top_p_val,
        "min_p": min_p_val,
        "repetition_penalty": rep_penalty_val,
    }


async def _process_audio_generation(
    project_name: str, lines: List[LineData], controls_dict: dict, language: str
):
    if not language:
        ui.notify("Please select a language before generating.", type="warning")
        return

    required_keys = [
        "exaggeration",
        "temperature",
        "cfg",
        "seed",
        "top_p",
        "min_p",
        "repetition_penalty",
    ]
    if not all(k in controls_dict for k in required_keys):
        ui.notify("Missing control settings in UI.", type="negative")
        return

    project_path = os.path.join(DEFAULT_PROJECT_DIRECTORY, project_name)
    if not os.path.isdir(project_path):
        ui.notify("Project folder not found.", type="negative")

    metadata_path = os.path.join(project_path, "metadata.json")

    metadata_list = []
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata_list = json.load(f)
        except json.JSONDecodeError:
            metadata_list = []

    current_index = _get_next_sequence_number(metadata_list, project_name)

    new_entries = []

    ui.notify(f"Starting generation of {len(lines)} lines...", type="info")

    for line in lines:
        if not line.voice:
            ui.notify(
                f"Skipping line: '{line.text[:20]}...' due to missing voice.",
                type="warning",
            )
            continue

        file_name = f"{project_name}_{current_index:03d}.wav"
        file_path = os.path.join(project_path, file_name)
        voice_path = os.path.join(DEFAULT_VOICE_LIBRARY, line.voice)

        try:
            # Call the wrapper function with values from UI
            generation_params = await run.io_bound(
                _generate_and_save_task,
                text=line.text,
                voice_path=voice_path,
                output_path=file_path,
                language=language,
                controls=controls_dict,
            )

            line.file_name = file_name

            entry = {
                "file_name": file_name,
                "speaker": line.speaker,
                "text": line.text,
                "voice": line.voice,
                "pause": line.pause,
                "params": generation_params,
            }
            new_entries.append(entry)
            current_index += 1

            ui.notify(
                f"✅ Generated: {line.text[:20]}...",
                type="positive",
                position="bottom-right",
            )
        except Exception as e:
            ui.notify(f"Error on line '{line.text[:10]}...': {str(e)}", type="negative")
            print(f"Gen Error: {e}")
            continue

    if new_entries:
        metadata_list.extend(new_entries)
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata_list, f, indent=4, ensure_ascii=False)
        ui.notify(f"Successfully generated {len(new_entries)} files.", type="positive")


async def generate_lines_list(
    text_area: ui.textarea,
    single_voice_profile: ui.select,
    lines_container: ui.column,
    speaker_list_container: ui.column,
    project_input: ui.input,
    controls_dict: dict,
    language_val: str,
):
    if project_input.value is None:
        ui.notify("Missing project selection.", type="negative")
        return

    script = text_area.value.strip()

    if not script:
        ui.notify("Text area is empty.", type="negative")
        return

    lines_container.clear()

    is_single_mode = single_voice_profile.enabled
    single_voice_val = single_voice_profile.value
    voice_map = {}

    if is_single_mode:
        if not single_voice_val:
            ui.notify("Missing single speaker voice.", type="negative")
            return
    elif speaker_list_container.visible:
        voice_map = _get_voice_map_from_ui(speaker_list_container)
        if not voice_map:
            ui.notify("No speakers configured or voices missing.", type="negative")

    parsed_lines = _parse_lines(script, is_single_mode, single_voice_val, voice_map)

    try:
        await _process_audio_generation(
            project_input.value, parsed_lines, controls_dict, language_val
        )
    except Exception as e:
        ui.notify(f"Error generating audio: {str(e)}", type="negative")
        return

    _render_lines_grid(lines_container, parsed_lines, project_input.value, audio_player)


def detect_speakers(
    textarea_ref: ui.textarea,
    speaker_list_container: ui.column,
    results_container: ui.column,
    single_voice_select: ui.select,
):
    script = textarea_ref.value
    speaker_tags = set(re.findall(r"^\s*\[([A-Za-z0-9\s]+)\]", script, re.MULTILINE))

    new_speakers = set()

    for tag in sorted(list(speaker_tags)):
        normalized_tag = tag.capitalize()
        new_speakers.add(normalized_tag)

    speaker_list_container.clear()

    if new_speakers:
        results_container.set_visibility(True)
        with speaker_list_container:
            for speaker in new_speakers:
                speaker_row(
                    speaker_name=speaker,
                    list_container=speaker_list_container,
                    single_voice_select=single_voice_select,
                    results_container=results_container,
                )
        single_voice_select.disable()
    else:
        results_container.set_visibility(False)
        single_voice_select.enable()

    results_container.update()
    speaker_list_container.update()
    ui.notify(f"Detected {len(new_speakers)} speakers.", type="positive")


def reset_speakers(
    speaker_list_container: ui.column,
    single_voice_select: ui.select,
    results_container: ui.column,
):
    speaker_list_container.clear()
    speaker_list_container.update()
    single_voice_select.enable()
    results_container.set_visibility(False)
    results_container.update()


def remove_speaker(
    row_to_remove: ui.row,
    list_container: ui.column,
    single_voice_select: ui.select,
    results_container: ui.column,
):
    row_to_remove.delete()
    list_container.update()

    if not list_container.default_slot.children:
        reset_speakers(list_container, single_voice_select, results_container)


def speaker_row(
    speaker_name: str,
    label_classes: str = None,
    list_container: ui.column = None,
    single_voice_select: ui.select = None,
    results_container: ui.column = None,
):
    with ui.row().classes(Style.flex_between_centered + " gap-2") as row_container:
        if list_container is not None:
            ui.button(
                "X",
                on_click=lambda: remove_speaker(
                    row_container,
                    list_container,
                    single_voice_select,
                    results_container,
                ),
            ).classes("flex-shrink-0 w-8 h-8 p-0").props("color=red flat round")

        default_label_classes = "font-medium text-gray-700 w-24 truncate"
        ui.label(speaker_name).classes(
            default_label_classes if not label_classes else label_classes
        )
        profile_select = render_saved_profiles_dropdown("flex-grow")
        profile_select.props("outlined dense color=indigo")

    return profile_select


def audiobook_creation_tab(tab_object: ui.tab):
    app_state = get_state()

    with ui.tab_panel(tab_object).classes("w-full p-0 m-0"):
        with ui.column().classes("w-full gap-6 p-6"):
            with ui.row().classes(Style.standard_border + " items-center"):
                ui.label("Project:").classes("font-semibold text-gray-700")
                project_select = (
                    ui.select(
                        options=get_existing_projects(),
                        label="Select folder / project name",
                        with_input=True,
                        on_change=lambda e: on_project_change(e, lines_list_container),
                    )
                    .classes("flex-grow")
                    .props("outlined dense color=indigo new-value-mode='add-unique'")
                    .on("focus", lambda: refresh_project_options(project_select))
                )

            with ui.row().classes("flex flex-wrap justify-start w-full gap-6"):
                with ui.column().classes(Style.half_screen_column):
                    with ui.card().classes(Style.standard_border + " h-[510px]"):
                        ui.label("Text to synthesize").classes(Style.standard_label)
                        text_input = (
                            ui.textarea(
                                value="[Narrator] In a dark forest, full of mysteries, stood a small house.\n"
                                "[Alice] Is this where the forest sprite lives?\n"
                                "[Boris] I don't think so. Let's ask.\n"
                                "[NARRATOR] Suddenly, a quiet rustle was heard.\n"
                                "[Alice] Who is there?",
                                placeholder="Enter text here in the format [Speaker] Text...",
                            )
                            .classes("w-full h-full")
                            .props("rows=20 outlined dense")
                        )

                        language_select = (
                            ui.select(options=[], value=None, label="Language")
                            .classes("w-full mb-2")
                            .props("outlined dense")
                        )

                        model_watcher = ui.input().classes("hidden")
                        model_watcher.bind_value_from(app_state, "active_model")
                        model_watcher.on_value_change(
                            lambda e: update_language_dropdown(language_select, e.value)
                        )
                        update_language_dropdown(
                            language_select, app_state.active_model
                        )

                with ui.column().classes(Style.half_screen_column):
                    with ui.card().classes(Style.standard_border + " h-[510px]"):
                        speaker_list_container = None

                        single_voice_select = speaker_row("Single voice")

                        ui.button(
                            "Detect Speakers",
                            on_click=lambda: detect_speakers(
                                text_input,
                                speaker_list_container,
                                results_container,
                                single_voice_select,
                            ),
                        ).classes(Style.small_button + " w-full").props("color=indigo")

                        results_container = ui.column().classes("w-full gap-2")
                        results_container.clear()
                        results_container.set_visibility(False)

                        with results_container:
                            ui.label("Speaker list").classes(
                                Style.standard_label + " mt-4"
                            )

                            with ui.scroll_area().classes(
                                Style.standard_border + " h-52"
                            ):
                                speaker_list_container = ui.column().classes(
                                    "w-full gap-1"
                                )
                            ui.button(
                                "Remove speakers",
                                on_click=lambda: reset_speakers(
                                    speaker_list_container,
                                    single_voice_select,
                                    results_container,
                                ),
                            ).classes("w-full mt-2").props("color=red")

            with ui.row().classes("w-full gap-6"):
                get_bound_model_column(app_state, model_name=None)
                with get_bound_model_column(app_state, "Chatterbox"):
                    chatterbox_ui_controls = chatterbox_controls(
                        include_audio_input=False
                    )

                with ui.column().classes(Style.half_screen_column):
                    with ui.card().classes(Style.standard_border):
                        with ui.row().classes(Style.centered_row + " pt-4"):
                            ui.label("Output Audio").classes(Style.standard_label)
                            ui.audio("").classes("w-full")

                        with ui.row().classes(Style.centered_row + " pt-4"):
                            ui.button(
                                "Create audio parts",
                                on_click=lambda: generate_lines_list(
                                    text_area=text_input,
                                    single_voice_profile=single_voice_select,
                                    lines_container=lines_list_container,
                                    speaker_list_container=speaker_list_container,
                                    project_input=project_select,
                                    controls_dict=chatterbox_ui_controls,
                                    language_val=language_select.value,
                                ),
                            ).classes(Style.small_button + " flex-grow").props(
                                "color=indigo"
                            )
                            ui.button(
                                "Merge audio parts",
                                on_click=lambda: ui.notify(
                                    "Merge audio parts - not implemented yet!"
                                ),
                            ).classes(Style.small_button + " flex-grow").props(
                                "color=indigo"
                            )

                        lines_list_container = ui.column().classes("w-full mt-4")
