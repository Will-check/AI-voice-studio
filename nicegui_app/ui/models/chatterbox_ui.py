from nicegui import ui
from nicegui_app.ui.common_ui import handle_file_upload, handle_reset
from nicegui_app.ui.styles import Style
from nicegui_app.logic.common_logic import update_audio_dropdown, load_audio_to_player
from nicegui_app.models.chatterbox_wrapper import (
    exaggeration,
    cfg,
    temperature,
    top_p,
    min_p,
    repetition_penalty,
)


def chatterbox_controls():
    controls = {}

    with ui.column().classes(Style.standard_border):
        ui.label("Saved Voice Profiles").classes(Style.standard_label)
        profile_select = (
            ui.select(
                options={},
                label="Select Profile",
            )
            .classes("w-full mb-4")
            .props("outlined dense")
        )
        update_audio_dropdown(profile_select)

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

        ui.label("Reference Audio").classes(Style.standard_label)

        with ui.column().classes("relative w-full"):
            # Grouping container to keep both UI and functional elements together.
            uploader_container = ui.element("div").classes("relative w-full h-40 group")

            with ui.row().classes("w-full") as reference_audio_player_container:
                reference_audio_player_container.visible = False
                with ui.row().classes(Style.flex_between_centered):
                    audio_player = ui.audio("").classes("flex-grow")
                    controls["audio_player"] = audio_player

                    ui.icon("clear", size="sm").classes(
                        "text-gray-500 hover:text-red-500 cursor-pointer"
                    ).tooltip("Clear reference audio").on(
                        "click",
                        lambda: handle_reset(
                            uploader_container,
                            reference_audio_player_container,
                            audio_player,
                            profile_select,
                            model_voices_select,
                        ),
                    )

            profile_select.on_value_change(
                lambda e: load_audio_to_player(
                    e,
                    audio_player,
                    reference_audio_player_container,
                    uploader_container,
                    model_voices_select,
                )
            )

            model_voices_select.on_value_change(
                lambda e: load_audio_to_player(
                    e,
                    audio_player,
                    reference_audio_player_container,
                    uploader_container,
                    profile_select,
                )
            )
            with uploader_container:
                # UI layer
                with ui.column().classes(
                    "w-full h-full border-2 border-dashed border-slate-300 rounded-lg "
                    "items-center justify-center bg-slate-50 transition-colors "
                    "group-hover:bg-slate-100 group-hover:border-slate-400 gap-1"
                ):
                    ui.icon("cloud_upload", size="2rem", color="slate-400").classes(
                        "transition-transform group-hover:scale-110"
                    )
                    ui.label("Drop Audio Here").classes(
                        "text-slate-500 text-base font-medium"
                    )
                    ui.label("- or -").classes("text-xs text-slate-300")
                    ui.label("CLICK TO UPLOAD").classes(
                        "font-bold text-orange-400 text-sm"
                    )

                # Functional layer
                uploader = (
                    ui.upload(
                        auto_upload=True,
                        on_upload=lambda e: handle_file_upload(
                            e,
                            uploader_container,
                            reference_audio_player_container,
                            audio_player,
                            profile_select,
                        ),
                        on_rejected=lambda: ui.notify(
                            "Invalid file format. Supported: MP3, WAV, FLAC.",
                            type="negative",
                        ),
                        max_files=1,
                        max_file_size=10_000_000,  # 10MB limit
                    )
                    .props(
                        'flat no-shadow accept=".mp3,.wav,.flac,audio/*" hide-upload-btn'
                    )
                    .classes(
                        # Opacity to show the custom UI element
                        "absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                    )
                )
                uploader.on("click", lambda: uploader.run_method("pickFiles"))

        # Sliders for Generation Control
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
                        ui.slider(
                            min=min_val, max=max_val, step=step, value=default_val
                        )
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
            "repetition_penality",
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

    return controls
