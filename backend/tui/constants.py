COMMAND_DESCRIPTIONS = {
    "/exit": "Exit ILsSage",
    "/quit": "Exit ILsSage",
    "/model": "Switch LLM model",
    "/help": "Show available commands",
    "/clear": "Start a new session",
    "/new": "Start a new session",
}


def get_help_text() -> str:
    return (
        "Commands:\n"
        "  /exit, /quit    Exit ILsSage\n"
        "  /model          Switch LLM model\n"
        "  /clear, /new    Start a new session\n"
        "  /help           Show this help\n"
        "\n"
        "Tips:\n"
        "  Shift+Mouse drag to select and copy text\n"
        "  Esc    Cancel streaming (press twice quickly)"
    )
