import io
import base64
import scipy.io.wavfile

from nicegui import ui, run
from nicegui_app.logic.app_state import get_state
from nicegui_app.models.chatterbox_wrapper import (
    LANGUAGES,
    MAX_CHARS,
    generate_tts_audio,
)
from nicegui_app.ui.common_ui import get_bound_model_column
from nicegui_app.ui.models.chatterbox_ui import chatterbox_controls
from nicegui_app.ui.styles import Style


async def handle_generation_logic(
    text_component: ui.textarea,
    language_component: ui.select,
    controls_dict: dict,
    audio_player_component: ui.audio,
):
    text = text_component.value
    if not text:
        ui.notify("Please enter text to synthesize.", type="warning")
        return

    language = language_component.value
    if not language:
        ui.notify("Please select a language.", type="warning")
        return

    ref_player = controls_dict.get("audio_player")
    if not ref_player or not ref_player.source:
        ui.notify("Please select or upload a reference audio.", type="warning")
        return

    audio_prompt_path = ref_player.source

    try:
        exaggeration_val = controls_dict["exaggeration"].value
        temperature_val = controls_dict["temperature"].value
        cfg_val = controls_dict["cfg"].value
        seed_val = int(controls_dict["seed"].value)
        top_p_val = controls_dict["top_p"].value
        min_p_val= controls_dict["min_p"].value
        rep_penalty_val = controls_dict["repetition_penalty"].value
    except KeyError as e:
        ui.notify(f"Missing control {e}", type="negative")
        return

    ui.notify("Starting generation...", type="info")

    try:
        sr, wav_data = await run.io_bound(
            generate_tts_audio,
            text_input=text,
            language_id=language,
            audio_prompt_path_input=audio_prompt_path,
            exaggeration_input=exaggeration_val,
            temperature_input=temperature_val,
            seed_num_input=seed_val,
            cfg_input=cfg_val,
            repetition_penalty_input=rep_penalty_val,
            min_p_input=min_p_val,
            top_p_input=top_p_val
        )

        byte_io = io.BytesIO()
        scipy.io.wavfile.write(byte_io, sr, wav_data)
        wav_bytes = byte_io.getvalue()
        base64_audio = base64.b64encode(wav_bytes).decode("ascii")

        audio_player_component.set_source(f"data:audio/wav;base64,{base64_audio}")
        ui.notify("Audio generated successfully!", type="positive")

    except Exception as e:
        ui.notify(f"Error during generation: {str(e)}", type="negative")
        print(f"Generation Error: {e}")


def single_generation_tab(tab_object: ui.tab):
    app_state = get_state()
    is_any_model_selected = lambda v: v != "No Model Selected"

    with ui.tab_panel(tab_object).classes("w-full"):
        with ui.row().classes("w-full gap-6"):
            get_bound_model_column(app_state, model_name=None)
            with get_bound_model_column(app_state, "Chatterbox"):
                chatterbox_ui_controls = chatterbox_controls()

            # --- Right Column: Input and Output
            with ui.column().classes(Style.half_screen_column):
                # Text Input, Language, Generate Button, Audio Output
                with ui.column().classes(Style.standard_border + " gap-6"):

                    # 1. Text Input Area
                    ui.label(f"Text to synthesize (max: chars {MAX_CHARS})").classes(
                        Style.standard_label
                    )
                    text_input_area = (
                        ui.textarea(placeholder="Enter text here...")
                        .props("rows=4 outlined dense")
                        .classes("w-full h-24")
                    )

                    # 2. Language Dropdown
                    ui.label("Language").classes(Style.standard_label)
                    language_dropdown = (
                        ui.select(
                            options=[],
                            value=None,
                            label="Select Language",
                        )
                        .classes("w-full")
                        .props("outlined dense")
                    )

                    language_dropdown.bind_enabled_from(
                        app_state, "active_model", is_any_model_selected
                    )

                    def update_language_options(model_name):
                        if model_name == "Chatterbox":
                            language_dropdown.options = LANGUAGES
                            if "en" in LANGUAGES:
                                language_dropdown.value = "en"
                            elif LANGUAGES:
                                language_dropdown.value = LANGUAGES[0]
                        else:
                            language_dropdown.options = []
                            language_dropdown.value = None

                        language_dropdown.update()

                    update_language_options(app_state.active_model)

                    model_watcher = ui.input().classes("hidden")
                    model_watcher.bind_value_from(app_state, "active_model")
                    model_watcher.on_value_change(
                        lambda e: update_language_options(e.value)
                    )

                    ui.label("Output Audio").classes(Style.standard_label)
                    output_audio_player = ui.audio("").classes("w-full")

                    generate_button = (
                        ui.button(
                            "Generate",
                            on_click=lambda: handle_generation_logic(
                                text_component=text_input_area,
                                language_component=language_dropdown,
                                controls_dict=chatterbox_ui_controls,
                                audio_player_component=output_audio_player,
                            ),
                        )
                        .classes(Style.small_button + " w-full")
                        .props("color=indigo")
                    )

                    generate_button.bind_enabled_from(
                        app_state, "active_model", is_any_model_selected
                    )
