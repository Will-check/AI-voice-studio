import random
import numpy as np
import torch

from chatterbox.mtl_tts import ChatterboxMultilingualTTS

MAX_CHARS = 300
LANGUAGES = [
    "ar",
    "da",
    "de",
    "el",
    "en",
    "es",
    "fi",
    "fr",
    "he",
    "hi",
    "it",
    "ja",
    "ko",
    "ms",
    "nl",
    "no",
    "pl",
    "pt",
    "ru",
    "sv",
    "sw",
    "tr",
    "zh",
]

exaggeration = {
    "min": 0.25,
    "max": 2.0,
    "default": 0.5,
    "step": 0.05,
    "label": "Exaggeration (Neutral = 0.5, extreme values can be unstable)",
}

cfg = {"min": 0.0, "max": 1.0, "default": 0.5, "step": 0.05, "label": "CFG/Pace"}

temperature = {
    "min": 0.05,
    "max": 2.0,
    "default": 0.8,
    "step": 0.05,
    "label": "Temperature",
}

top_p = {
    "min": 0.1,
    "max": 1.0,
    "default": 1.0,
    "step": 0.05,
    "label": "Top P (Sampling)",
}
min_p = {
    "min": 0.0,
    "max": 0.5,
    "default": 0.05,
    "step": 0.01,
    "label": "Min P (Noise reduction)",
}
repetition_penalty = {
    "min": 1.0,
    "max": 2.0,
    "default": 1.2,
    "step": 0.05,
    "label": "Repetition Penalty",
}
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

MODEL = None


def get_or_load_model():
    global MODEL
    if MODEL is None:
        print("Model not loaded, initializing...")
        try:
            MODEL = ChatterboxMultilingualTTS.from_pretrained(DEVICE)
            if hasattr(MODEL, "to") and str(MODEL.device) != DEVICE:
                MODEL.to(DEVICE)
            print(
                f"Model loaded successfully. Internal device: {getattr(MODEL, 'device', 'N/A')}"
            )
        except Exception as e:
            print(f"Error loading model: {e}")
            raise
    return MODEL


def set_seed(seed: int):
    torch.manual_seed(seed)
    if DEVICE == "cuda":
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    random.seed(seed)
    np.random.seed(seed)


def generate_tts_audio(
    text_input: str,
    language_id: str,
    audio_prompt_path_input: str,
    exaggeration_input: float = 0.5,
    temperature_input: float = 0.8,
    seed_num_input: int = 0,
    cfg_input: float = 0.5,
):
    current_model = get_or_load_model()

    if current_model is None:
        raise RuntimeError("TTS model is not loaded.")

    if seed_num_input != 0:
        set_seed(int(seed_num_input))

    print(f"Generating audio for text: '{text_input[:50]}...'")

    generate_kwargs = {
        "exaggeration": exaggeration_input,
        "temperature": temperature_input,
        "cfg_weight": cfg_input,
        "audio_prompt_path": audio_prompt_path_input,
    }

    raw_wav = current_model.generate(
        text_input[:MAX_CHARS],  # Truncate text to max chars
        language_id=language_id,
        **generate_kwargs,
    )

    wav = raw_wav.squeeze(0).numpy()

    print("Audio generation complete.")
    return (current_model.sr, wav)
