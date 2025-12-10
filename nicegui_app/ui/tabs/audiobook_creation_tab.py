from nicegui import ui
from nicegui_app.logic.app_state import get_state
from nicegui_app.ui.common_ui import get_bound_model_column
from nicegui_app.ui.models.chatterbox_ui import chatterbox_controls
from nicegui_app.ui.styles import Style
import re


def generate_lines_list(
    text_area: ui.textarea,
    lines_container: ui.column,
    voice_options: list,
    speaker_list_container: ui.column,
):

    # 1. Build speaker-voice map from the UI elements in speaker_list_container
    speaker_voice_map = {}
    if hasattr(speaker_list_container, "default_slot"):
        for row in speaker_list_container.default_slot.children:
            speaker_label = None
            voice_select = None
            for child in row.default_slot.children:
                if isinstance(child, ui.label):
                    speaker_label = child
                elif isinstance(child, ui.select):
                    voice_select = child

            if speaker_label and voice_select:
                speaker_name = speaker_label.text
                selected_voice = voice_select.value
                speaker_voice_map[speaker_name] = selected_voice

    lines_container.clear()
    script = text_area.value.strip()

    if not script:
        ui.notify("Text area is empty.", type="warning")
        return

    lines = script.split("\n")

    has_speaker_tags = any(
        re.match(r"^\s*\[([A-Za-z0-9\s]+)\]", line) for line in lines
    )
    if not has_speaker_tags:
        ui.notify(
            "No speaker tags found in the format [Speaker]. Cannot generate lines list.",
            type="warning",
        )
        return

    with lines_container:
        ui.label("Generated lines list:").classes("text-lg font-semibold")

        # Define grid layout
        cols = "auto 130px minmax(150px, 1fr) auto auto 110px 3fr"
        with ui.grid(columns=cols).classes("items-center w-full gap-x-10 gap-y-1"):
            # Header
            ui.label("Exclude").classes(Style.list_header_center)
            ui.label("Speaker").classes(Style.list_header_center)
            ui.label("Voice (dropdown)").classes(Style.list_header_center)
            ui.label("▶ Play").classes(Style.list_header_center)
            ui.label("🔁 Regenerate").classes(Style.list_header_center)
            ui.label("Pause [s]").classes(Style.list_header_center)
            ui.label("Line text").classes(Style.list_header_left)

            # Header separator
            ui.separator().classes("my-1 col-span-full")

            # Data Rows
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                match = re.match(r"^\s*\[([A-Za-z0-9\s]+)\]\s*(.*)", line)
                if match:
                    speaker, text = [x.strip() for x in match.groups()]
                    speaker_capitalized = speaker.capitalize()

                    assigned_voice = speaker_voice_map.get(
                        speaker_capitalized, voice_options[0]
                    )

                    # Grid cells for a single line
                    with ui.row().classes(Style.centered_row):
                        ui.checkbox()
                    ui.label(speaker).classes("text-center")
                    ui.select(options=voice_options, value=assigned_voice).classes(
                        "w-full"
                    ).props("outlined dense")
                    with ui.row().classes(Style.centered_row):
                        ui.button(
                            icon="play_arrow",
                            on_click=lambda s=text: ui.notify(f"Play: {s[:30]}..."),
                        ).props("flat round color=primary")
                    with ui.row().classes(Style.centered_row):
                        ui.button(
                            icon="sync",
                            on_click=lambda s=speaker: ui.notify(f"Regenerate for {s}"),
                        ).props("flat round color=secondary")
                    ui.number(value=0.5, format="%.1f", step=0.1, min=0).classes(
                        "w-full"
                    ).props("outlined dense")
                    ui.label(text).classes("text-left")

                    # Separator for each line
                    ui.separator().classes("col-span-full")

    ui.notify("Generated new audio parts list.", type="positive")


def detect_speakers(
    textarea_ref: ui.textarea,
    speaker_list_container: ui.column,
    results_container: ui.column,
    voice_options: list,
    single_voice_select: ui.select,
):
    script = textarea_ref.value
    speaker_tags = set(re.findall(r"^\s*\[([A-Za-z0-9\s]+)\]", script, re.MULTILINE))

    new_speakers = {}

    for tag in sorted(list(speaker_tags)):
        normalized_tag = tag.capitalize()
        new_speakers[normalized_tag] = ""

    speaker_list_container.clear()

    if new_speakers:
        results_container.set_visibility(True)
        with speaker_list_container:
            for speaker, default_voice in new_speakers.items():
                speaker_row(
                    speaker,
                    voice_options,
                    default_voice,
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
    voice_options: list,
    default_voice: str,
    label_classes: str = "",
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

        row = (
            ui.select(options=voice_options, value=default_voice, label="Select Voice")
            .classes("flex-grow")
            .props("outlined dense color=indigo")
        )

    return row


def audiobook_creation_tab(tab_object: ui.tab):
    app_state = get_state()
    voice_options = ["", "Voice A (M)", "Voice B (F)", "Voice C (Child)"]

    with ui.tab_panel(tab_object).classes("w-full p-0 m-0"):
        with ui.column().classes("w-full gap-6 p-6"):
            with ui.row().classes(Style.standard_border + " items-center"):
                ui.label("Project:").classes("font-semibold text-gray-700")
                ui.input(value="", label="Select folder / project name").classes(
                    "flex-grow"
                ).props("outlined dense color=indigo")

            with ui.row().classes("flex flex-wrap justify-start w-full gap-6"):
                with ui.column().classes(Style.half_screen_column):
                    with ui.card().classes(Style.standard_border + " h-[460px]"):
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

                with ui.column().classes(Style.half_screen_column):
                    with ui.card().classes(Style.standard_border + " h-[460px]"):
                        speaker_list_container = None

                        single_voice_select = speaker_row(
                            "Single voice",
                            voice_options,
                            "",
                        )

                        ui.button(
                            "Detect Speakers",
                            on_click=lambda: detect_speakers(
                                text_input,
                                speaker_list_container,
                                results_container,
                                voice_options,
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
                                    text_input,
                                    lines_list_container,
                                    voice_options,
                                    speaker_list_container,
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
