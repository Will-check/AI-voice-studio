from nicegui import ui
from nicegui_app.ui.styles import Style
from nicegui_app.logic.common_logic import update_audio_dropdown, load_audio_to_player
import os


# Dictionary to manage temporary audio file paths per client session
temp_audio_files = {}


def render_empty_model_state():
    with ui.column().classes(
        Style.standard_border + " items-center justify-center h-[470px]"
    ):
        ui.icon("info", size="2xl").classes("text-orange-500")
        ui.label("No Model Selected").classes("text-xl font-bold text-gray-700")
        ui.label(
            "Please select a valid model from the dropdown menu to enable specific controls."
        ).classes("text-center text-gray-500")


def get_bound_model_column(app_state, classes, model_name: str = None):
    column = ui.column().classes(classes)

    if model_name:
        is_model_selected = lambda v: v == model_name
        column.bind_visibility_from(app_state, "active_model", is_model_selected)
    else:
        is_no_model = lambda v: v == "No Model Selected"
        column.bind_visibility_from(app_state, "active_model", is_no_model)

        with column:
            render_empty_model_state()

    return column


def render_saved_profiles_dropdown(classes = ""):
    profile_select = (
        ui.select(
            options={},
            label="Select Profile",
        )
        .classes(classes)
        .props("outlined dense")
    )
    update_audio_dropdown(profile_select)
    return profile_select


def handle_reset(
    upload_component,
    player_container,
    audio_player,
    dropdowns_list=None,
):
    client_id = ui.context.client.id
    if client_id in temp_audio_files and os.path.exists(temp_audio_files[client_id]):
        try:
            os.remove(temp_audio_files[client_id])
            del temp_audio_files[client_id]
        except Exception:
            pass

    audio_player.run_method("pause")
    audio_player.source = ""
    audio_player.update()

    player_container.visible = False
    player_container.update()

    upload_component.visible = True
    upload_component.update()

    if dropdowns_list:
        for dropdown in dropdowns_list:
            dropdown.value = None
            dropdown.update()


def render_reference_audio_component(
    controls, profile_select=None, external_dropdowns=None
):
    if external_dropdowns is None:
        external_dropdowns = []

    ui.label("Reference Audio").classes(Style.standard_label)

    with ui.column().classes("relative w-full"):
        uploader_container = ui.element("div").classes("relative w-full h-40 group")

        with ui.row().classes("w-full") as player_container_row:
            player_container_row.visible = False
            with ui.row().classes(Style.flex_between_centered):
                audio_player = ui.audio("").classes("flex-grow")
                controls["audio_player"] = audio_player

                def on_clear_click():
                    dropdowns_to_reset = []
                    if profile_select:
                        dropdowns_to_reset.append(profile_select)
                    dropdowns_to_reset.extend(external_dropdowns)

                    handle_reset(
                        uploader_container,
                        player_container_row,
                        audio_player,
                        dropdowns_to_reset,
                    )

                ui.icon("clear", size="sm").classes(
                    "text-gray-500 hover:text-red-500 cursor-pointer"
                ).tooltip("Clear reference audio").on("click", on_clear_click)

        with uploader_container:
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
                ui.label("CLICK TO UPLOAD").classes("text-sm font-bold text-orange-400")

            async def on_upload_handler(e):
                if profile_select:
                    profile_select.value = None
                for d in external_dropdowns:
                    d.value = None

                await handle_file_upload(
                    e, uploader_container, player_container_row, audio_player
                )

            uploader = (
                ui.upload(
                    auto_upload=True,
                    on_upload=on_upload_handler,
                    on_rejected=lambda: ui.notify(
                        "Invalid file format. Supported: MP3, WAV, FLAC.",
                        type="negative",
                    ),
                    max_files=1,
                    max_file_size=10_000_000,
                )
                .props(
                    'flat no-shadow accept=".mp3,.wav,.flac,audio/*" hide-upload-btn'
                )
                .classes("absolute inset-0 z-10 w-full h-full opacity-0 cursor-pointer")
            )
            uploader.on("click", lambda: uploader.run_method("pickFiles"))

    return audio_player, uploader_container, player_container_row


async def handle_file_upload(
    e, upload_component, player_container, audio_player, profile_select=None
):
    client_id = e.client.id
    file_name = f"ref_{client_id}_{e.file.name}"

    # Reset the upload component
    e.sender.reset()

    # Clean up old file if it exists (simple session management)
    if client_id in temp_audio_files and os.path.exists(temp_audio_files[client_id]):
        os.remove(temp_audio_files[client_id])

    # Create a temporary file path
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_filepath = os.path.join(temp_dir, file_name)

    # Save the uploaded file chunk
    try:
        await e.file.save(temp_filepath)

        temp_audio_files[client_id] = temp_filepath

        audio_player.source = temp_filepath
        audio_player.update()

        player_container.visible = True
        upload_component.visible = False

        if profile_select:
            profile_select.value = None

        ui.notify(
            f"Reference file uploaded: {e.file.name}", type="positive", timeout=2000
        )

        if upload_component and player_container:
            upload_component.visible = False
            player_container.visible = True

    except Exception as err:
        ui.notify(f"Error saving file: {err}", type="negative")
        upload_component.visible = True
