def run_tui(session_id=None):
    from backend.tui.app import ILS4GASApp
    app = ILS4GASApp(session_id=session_id)
    app.run()
    sid = app.session_id
    if sid:
        print(f"Session ID: {sid}")
        print(f"To continue: ils4gas --session {sid}")
