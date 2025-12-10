from nicegui import ui
from nicegui_app.ui.styles import Style
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


def get_bound_model_column(app_state, model_name: str = None):
    column = ui.column().classes(Style.half_screen_column)

    if model_name:
        is_model_selected = lambda v: v == model_name
        column.bind_visibility_from(app_state, "active_model", is_model_selected)
    else:
        is_no_model = lambda v: v == "No Model Selected"
        column.bind_visibility_from(app_state, "active_model", is_no_model)

        with column:
            render_empty_model_state()

    return column


def handle_reset(
    upload_component,
    player_container,
    audio_player,
    profile_select=None,
    model_profile_select=None,
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

    if profile_select:
        profile_select.value = None
        profile_select.update()

    if model_profile_select:
        model_profile_select.value = None
        model_profile_select.update()


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
