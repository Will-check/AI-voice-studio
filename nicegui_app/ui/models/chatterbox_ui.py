from nicegui import ui

from nicegui_app.ui.common_ui import (
    render_saved_profiles_dropdown,
    render_reference_audio_component,
)
from nicegui_app.ui.styles import Style
from nicegui_app.models.chatterbox_wrapper import (
    exaggeration,
    cfg,
    temperature,
    top_p,
    min_p,
    repetition_penalty,
)
from nicegui_app.logic.common_logic import update_audio_dropdown, load_audio_to_player


def _render_chatterbox_sliders(controls):
    def create_labeled_slider(
        key_name, label_text, min_val, max_val, step, default_val
    ):
        def reset_slider(target_slider, target_input, default_value):
            target_slider.value = default_value
            target_input.value = default_value

        with ui.column().classes(Style.slider_box):
            with ui.row().classes(Style.flex_between_centered):
                ui.label(label_text).classes("text-sm")

                with ui.row().classes("items-center justify-end gap-1"):
                    number_input = (
                        ui.number(
                            value=default_val,
                            min=min_val,
                            max=max_val,
                            step=step,
                            format="%.2f",
                        )
                        .classes("w-14")
                        .props("dense outlined input-class=text-center")
                    )
                    ui.icon("refresh", size="sm").classes(
                        "text-gray-500 hover:text-indigo-500 cursor-pointer"
                    ).on(
                        "click",
                        lambda: reset_slider(slider, number_input, default_val),
                    )

            with ui.row().classes("items-center w-full"):
                slider = (
                    ui.slider(min=min_val, max=max_val, step=step, value=default_val)
                    .classes("w-full")
                    .props("color=indigo")
                )

            slider.bind_value_to(number_input, "value")
            number_input.bind_value_to(slider, "value")
            controls[key_name] = slider

    create_labeled_slider(
        "exaggeration",
        exaggeration["label"],
        exaggeration["min"],
        exaggeration["max"],
        exaggeration["step"],
        exaggeration["default"],
    )
    create_labeled_slider(
        "cfg", cfg["label"], cfg["min"], cfg["max"], cfg["step"], cfg["default"]
    )
    create_labeled_slider(
        "temperature",
        temperature["label"],
        temperature["min"],
        temperature["max"],
        temperature["step"],
        temperature["default"],
    )

    create_labeled_slider(
        "top_p",
        top_p["label"],
        top_p["min"],
        top_p["max"],
        top_p["step"],
        top_p["default"],
    )

    create_labeled_slider(
        "min_p",
        min_p["label"],
        min_p["min"],
        min_p["max"],
        min_p["step"],
        min_p["default"],
    )

    create_labeled_slider(
        "repetition_penalty",
        repetition_penalty["label"],
        repetition_penalty["min"],
        repetition_penalty["max"],
        repetition_penalty["step"],
        repetition_penalty["default"],
    )

    DEFAULT_SEED_VALUE = 0
    with ui.column().classes(
        "w-full mt-2 p-2 bg-gray-50 rounded-lg border border-gray-100"
    ):
        with ui.row().classes(Style.flex_between_centered):
            ui.label("Seed (0 for random)").classes("text-sm")

        seed_input = (
            ui.number(value=DEFAULT_SEED_VALUE, min=0, step=1, label="Seed Value")
            .classes("w-full")
            .props("dense outlined no-spinners")
        )
        controls["seed"] = seed_input


def chatterbox_controls(include_audio_input=True):
    controls = {}

    with ui.column().classes(Style.standard_border):
        if include_audio_input:
            profile_select = render_saved_profiles_dropdown()

            ui.label("Default Model Voices").classes(Style.standard_label)
            model_voices_select = (
                ui.select(
                    options={},
                    label="Select Profile",
                )
                .classes("w-full mb-4")
                .props("outlined dense")
            )
            update_audio_dropdown(model_voices_select, "models/chatterbox/samples")

            audio_player, uploader_div, player_row = render_reference_audio_component(
                controls,
                profile_select=profile_select,
                external_dropdowns=[model_voices_select],
            )

            profile_select.on_value_change(
                lambda e: load_audio_to_player(
                    e, audio_player, player_row, uploader_div, model_voices_select
                )
            )

            model_voices_select.on_value_change(
                lambda e: load_audio_to_player(
                    e, audio_player, player_row, uploader_div, profile_select
                )
            )

        _render_chatterbox_sliders(controls)

    return controls
