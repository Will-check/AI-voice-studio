
import json
import os
import re
import shutil
import time
import nicegui_app.logic.tabs.audiobook_creation_logic as acl

from nicegui import ui, run
from nicegui_app.logic.app_state import get_state
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
from typing import List, Dict


def extract_control_values(controls_ui: dict) -> dict:
    return {k: v.value for k, v in controls_ui.items()}


def refresh_project_options(select_element: ui.select):
    current_projects = acl.get_existing_projects()
    select_element.options = current_projects
    select_element.update()


def get_voice_map_from_ui(container: ui.column) -> Dict[str, str]:
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


def render_line_row(item: acl.LineData, project_name: str, generator_callback):
    with ui.row().classes(Style.centered_row):
        ui.checkbox()
    ui.label(item.speaker).classes("text-center font-medium")

    voice_select = (
        ui.select(options=get_audio_files(), value=item.voice)
        .classes("w-full")
        .props("outlined dense")
    )

    def play_audio_file(fname):
        if not fname:
            return
        url = f"/projects/{project_name}/{fname}?t={time.time()}"
        ui.run_javascript(f"var a = new Audio('{url}'); a.play();")

    with ui.row().classes(Style.centered_row):
        ui.button(
            icon="play_arrow", on_click=lambda: play_audio_file(item.file_name)
        ).props("flat round color=primary")

    with ui.row().classes("items-center justify-center gap-1 min-w-[120px]"):
        candidate_state = {"path": None, "params": None}
        regen_btn = (
            ui.button(icon="sync")
            .props("flat round color=secondary")
            .tooltip("Regenerate")
        )
        spinner = ui.spinner(size="2em")
        spinner.visible = False
        actions_row = ui.row().classes("hidden gap-1")

        with actions_row:
            ui.button(
                icon="volume_up",
                on_click=lambda: play_audio_file(
                    os.path.basename(candidate_state["path"])
                ),
            ).props("flat round color=green").tooltip("Listen to the new file")

            async def on_save():
                if candidate_state["path"] and os.path.exists(candidate_state["path"]):
                    original_path = os.path.join(
                        DEFAULT_PROJECT_DIRECTORY, project_name, item.file_name
                    )
                    shutil.move(candidate_state["path"], original_path)

                    acl.update_metadata_entry(
                        project_name,
                        item.file_name,
                        text_input.value,
                        voice_select.value,
                        candidate_state["params"],
                    )

                    actions_row.set_visibility(False)
                    regen_btn.set_visibility(True)
                    ui.notify("Replaced!", type="positive", timeout=1000)

            ui.button(icon="check", on_click=on_save).props(
                "flat round color=green"
            ).tooltip("Overwrite")

            def on_cancel():
                actions_row.set_visibility(False)
                regen_btn.set_visibility(True)

                temp_path = candidate_state.get("path")
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                        candidate_state["path"] = None
                    except Exception as e:
                        print(f"Error removing temp file: {e}")

            ui.button(icon="close", on_click=on_cancel).props(
                "flat round color=red"
            ).tooltip("Reject")

        async def on_regen_click():
            regen_btn.set_visibility(False)
            actions_row.set_visibility(False)
            spinner.set_visibility(True)

            try:
                result = await generator_callback(
                    text=text_input.value,
                    voice=voice_select.value,
                    original_filename=item.file_name,
                )

                if result:
                    candidate_state["path"] = result["path"]
                    candidate_state["params"] = result["params"]
                    spinner.set_visibility(False)
                    actions_row.set_visibility(True)
                else:
                    spinner.set_visibility(False)
                    regen_btn.set_visibility(True)
            except Exception:
                spinner.set_visibility(False)
                regen_btn.set_visibility(True)

        regen_btn.on("click", on_regen_click)

    ui.number(value=item.pause, format="%.1f", step=0.1, min=0).classes("w-full").props(
        "outlined dense"
    ).on_value_change(lambda e: setattr(item, "pause", e.value))

    current_limit = acl.get_current_model_max_chars()
    text_input = (
        ui.textarea(value=item.text)
        .props(f"rows=1 autogrow outlined dense maxlength='{current_limit}' counter")
        .classes("w-full text-sm")
    )

    ui.separator().classes("col-span-full")


def render_lines_grid(
    container: ui.column, lines: List[acl.LineData], project_name: str, regen_handler
):
    container.clear()

    if not lines:
        return

    with container:
        ui.label(f"Project content ({len(lines)} lines):").classes(Style.standard_label)

        cols = "auto 130px minmax(150px, 1fr) auto auto 45px 3fr"
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
                render_line_row(item, project_name, regen_handler)


def on_project_change(
    event,
    lines_container: ui.column,
    regen_handler,
    ui_lines: List[acl.LineData],
):
    project_name = event.value
    created = acl.ensure_project_exists(project_name=project_name)
    if created:
        ui.notify(f"Created new project: {project_name}", type="positive")

    acl.cleanup_temp_files(project_name)
    new_lines = acl.load_project_metadata(project_name)
    ui_lines.clear()
    ui_lines.extend(new_lines)
    render_lines_grid(lines_container, ui_lines, project_name, regen_handler)


async def process_audio_generation(
    project_name: str, lines: List[acl.LineData], controls_dict: dict, language: str
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

    current_index = acl.get_next_sequence_number(metadata_list, project_name)

    new_entries = []

    ui.notify(f"Starting generation of {len(lines)} lines...", type="info")

    control_values = extract_control_values(controls_dict)

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
                acl.generate_and_save_audio,
                text=line.text,
                voice_path=voice_path,
                output_path=file_path,
                language=language,
                controls=control_values,
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
    regen_handler,
    ui_lines: List[acl.LineData],
):
    if project_input.value is None:
        ui.notify("Missing project selection.", type="negative")
        return

    script = text_area.value.strip()

    if not script:
        ui.notify("Text area is empty.", type="negative")
        return

    is_single_mode = single_voice_profile.enabled
    single_voice_val = single_voice_profile.value
    voice_map = {}

    if is_single_mode:
        if not single_voice_val:
            ui.notify("Missing single speaker voice.", type="negative")
            return
    elif speaker_list_container.visible:
        voice_map = get_voice_map_from_ui(speaker_list_container)
        if not voice_map:
            ui.notify("No speakers configured or voices missing.", type="negative")
            return

    max_chars = acl.get_current_model_max_chars()
    parsed_lines = acl.parse_lines(
        script, is_single_mode, single_voice_val, voice_map, max_chars
    )
    ui_lines.clear()
    ui_lines.extend(parsed_lines)

    try:
        await process_audio_generation(
            project_input.value, ui_lines, controls_dict, language_val
        )
    except Exception as e:
        ui.notify(f"Error generating audio: {str(e)}", type="negative")
        return

    full_project_lines = acl.load_project_metadata(project_input.value)
    ui_lines.clear()
    ui_lines.extend(full_project_lines)

    lines_container.clear()
    render_lines_grid(lines_container, ui_lines, project_input.value, regen_handler)


def confirm_delete_project(project_select: ui.select, lines_list_container: ui.column):
    name = project_select.value
    if not name:
        ui.notify("No project selected", type="warning")
        return

    with ui.dialog() as dialog, ui.card():
        ui.label(f"Are you sure you want to delete proejct '{name}'?").classes(
            "text-lg font-bold"
        )
        ui.label("This operation would remove all files from this project.").classes(
            "text-red-500"
        )

        def perform_delete():
            project_path = os.path.join(DEFAULT_PROJECT_DIRECTORY, name)
            if os.path.exists(project_path):
                try:
                    shutil.rmtree(project_path)
                    ui.notify(f"Project '{name}' has been deleted.", type="positive")

                    project_select.value = None
                    refresh_project_options(project_select)

                    if lines_list_container:
                        lines_list_container.clear()

                except Exception as e:
                    ui.notify(f"Delete error: {e}", type="negative")
            dialog.close()

        with ui.row().classes("w-full justify-end"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Delete", color="red", on_click=perform_delete)

    dialog.open()


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


async def handle_merge_click(
    project_select: ui.select, audio_player: ui.audio, current_ui_lines: List[acl.LineData]
):
    project_name = project_select.value
    if not project_name:
        ui.notify("Please select a project first.", type="negative")
        return

    ui.notify("Merging audio files...", type="info")

    result_filename = await run.io_bound(
        acl.merge_and_save_audio, project_name, current_ui_lines
    )

    if result_filename:
        new_url = f"/output/{result_filename}?t={time.time()}"
        audio_player.source = new_url
        audio_player.update()


def audiobook_creation_tab(tab_object: ui.tab):
    app_state = get_state()
    current_lines: List[acl.LineData] = []

    with ui.tab_panel(tab_object).classes("w-full p-0 m-0"):
        with ui.column().classes("w-full gap-6 p-6"):
            with ui.row().classes(Style.standard_border + " items-center"):
                ui.label("Project:").classes("font-semibold text-gray-700")
                project_select = (
                    ui.select(
                        options=acl.get_existing_projects(),
                        label="Select folder / project name",
                        with_input=True,
                        on_change=lambda e: on_project_change(
                            e,
                            lines_list_container,
                            row_generation_callback,
                            current_lines,
                        ),
                    )
                    .classes("flex-grow")
                    .props("outlined dense color=indigo new-value-mode='add-unique'")
                    .on("focus", lambda: refresh_project_options(project_select))
                )

                ui.button(
                    icon="delete",
                    color="red",
                    on_click=lambda: confirm_delete_project(
                        project_select, lines_list_container
                    ),
                ).props("flat round").tooltip("Delete project")

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
                with ui.column().classes("w-full"):
                    with ui.card().classes(Style.standard_border):

                        async def row_generation_callback(
                            text, voice, original_filename
                        ):
                            if not language_select.value:
                                ui.notify("Select language!", type="negative")
                                return None

                            project_name = project_select.value
                            temp_filename = (
                                f"temp_{int(time.time())}_{original_filename}"
                            )
                            temp_path = os.path.join(
                                DEFAULT_PROJECT_DIRECTORY, project_name, temp_filename
                            )
                            voice_path = os.path.join(DEFAULT_VOICE_LIBRARY, voice)

                            ctrl_values = extract_control_values(
                                chatterbox_ui_controls
                            )

                            try:
                                params = await run.io_bound(
                                    acl.generate_and_save_audio,
                                    text=text,
                                    voice_path=voice_path,
                                    output_path=temp_path,
                                    language=language_select.value,
                                    controls=ctrl_values,
                                )
                                return {"path": temp_path, "params": params}
                            except Exception as e:
                                ui.notify(f"Error: {e}", type="negative")
                                return None

                        with ui.row().classes(Style.centered_row + " pt-4"):
                            ui.label("Output Audio").classes(Style.standard_label)
                            output_audio_player = ui.audio("").classes("w-full")

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
                                    regen_handler=row_generation_callback,
                                    ui_lines=current_lines,
                                ),
                            ).classes(Style.small_button + " flex-grow").props(
                                "color=indigo"
                            )

                            ui.button(
                                "Merge audio parts",
                                on_click=lambda: handle_merge_click(
                                    project_select, output_audio_player, current_lines
                                ),
                            ).classes(Style.small_button + " flex-grow").props(
                                "color=indigo"
                            )

                        lines_list_container = ui.column().classes("w-full mt-4")

                get_bound_model_column(app_state, "w-full", model_name=None)
                with get_bound_model_column(app_state, "w-full", "Chatterbox"):
                    chatterbox_ui_controls = chatterbox_controls(
                        include_audio_input=False
                    )
