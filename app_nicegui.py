from nicegui import ui
from nicegui import app
from nicegui_app.ui.tabs.single_generation_tab import single_generation_tab
from nicegui_app.ui.tabs.audiobook_creation_tab import audiobook_creation_tab
from nicegui_app.logic.app_state import AppState, get_state
from nicegui_app.ui.styles import Style


app.add_static_files("/voice_library", "voice_library")

app_state = get_state()

# CSS to modify native browser features
ui.add_head_html(
    """
    <style>
        /* Disable the resize handle for all textarea elements, solving the user's request */
        textarea {
            resize: none !important;
        }
        
        /* Hide arrows (spinners) for Chrome, Safari, Edge, Opera on number inputs */
        input[type=number]::-webkit-inner-spin-button, 
        input[type=number]::-webkit-outer-spin-button { 
            -webkit-appearance: none;
            margin: 0;
        }

        /* Hide arrows (spinners) for Firefox on number inputs */
        input[type=number] {
            -moz-appearance: textfield;
        }
        /* Always show scrollbar to prevent tab content shifting on change */
        body { 
            overflow-y: scroll; 
        }
    </style>
"""
)

with ui.column().classes("w-full gap-5 px-5"):

    # 1. Header Section
    with ui.row().classes("justify-center w-full py-10 bg-gray-800 shadow-lg"):
        with ui.column().classes("items-center gap-0"):
            title_html = """
            <span class="text-6xl font-extrabold" 
                style="background-image: linear-gradient(to right, #00BFFF, #8A2BE2); 
                        -webkit-background-clip: text; 
                        -webkit-text-fill-color: transparent;">
                    AI Voice Studio
            </span>
            """
            ui.html(title_html, sanitize=False).classes("pb-2")

            # Subtitle
            ui.label("Transforming Text into Expressive Audio").classes(
                "text-lg text-gray-300 font-light"
            )

    # 2. Navigation Tabs and Right-aligned Dropdown
    with ui.row().classes(Style.menu_line):
        # Tabs (Left-aligned)
        with (
            ui.tabs()
            .classes("h-12")
            .props(
                "active-color=indigo indicator-color=indigo align=left inline-label"
            ) as tabs
        ):

            tab_gen = ui.tab("Single Generation", icon="mic")
            tab_audio = ui.tab("Audiobook Creation", icon="menu_book")

        # Dropdown Box (Right-aligned)
        default_model = "Chatterbox"
        no_model_selected_label = ""
        model_options = [no_model_selected_label, "Chatterbox"]
        app_state.set_active_model(default_model)

        def handle_model_change(e):
            model_name = None if e.value == no_model_selected_label else e.value
            app_state.set_active_model(model_name)

        ui.select(
            options=model_options,
            value=default_model,
            label="Select Model",
            on_change=handle_model_change,
        ).classes("w-48 h-12 ml-6 ml-auto").props("dense outlined color=indigo")

    # 3. Content Panels
    with ui.tab_panels(tabs, value=tab_audio).classes("w-full"):
        single_generation_tab(tab_gen)
        audiobook_creation_tab(tab_audio)

ui.run(title="Text To Speech Interface", host="0.0.0.0", port=7861)
