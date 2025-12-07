from nicegui import ui


# A class to hold shared application state
class AppState:
    no_model_selected = "No Model Selected"

    def __init__(self):
        # Add here everything that should be shared across the application
        self.active_model = self.no_model_selected

    def set_active_model(self, model_name: str | None) -> None:
        self.active_model = model_name if model_name else self.no_model_selected

        ui.notify(
            f"Active model set to: {self.active_model}", type="info", timeout=1500
        )

    def to_json(self):
        return {
            "active_model": self.active_model,
        }


# Initialize the global state instance
app_state = AppState()


def get_state() -> AppState:
    return app_state
