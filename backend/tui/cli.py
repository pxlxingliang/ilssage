def run_tui(session_id=None):
    from backend.tui.app import IlsSageApp
    app = IlsSageApp(session_id=session_id)
    app.run()
    sid = app.session_id
    if sid:
        print(f"Session ID: {sid}")
        print(f"To continue: ilssage --session {sid}")
