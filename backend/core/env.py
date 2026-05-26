import json
import os
from pathlib import Path
from typing import Dict


_DEFAULTS: Dict[str, str] = {
    "ILSSAGE_WEB_HOST": "0.0.0.0",
    "ILSSAGE_WEB_PORT": "8789",
    "ILSSAGE_MCP_TRANSPORT": "stdio",
    "ILSSAGE_MCP_HOST": "localhost",
    "ILSSAGE_MCP_PORT": "50001",
    "ILSSAGE_TRAIN_EB_PATH": "",
    "ILSSAGE_QM_FEATURE_PATH": "",
    "ILSSAGE_MOLECULE_GEN_SCRIPT": "",
    "ILSSAGE_EB_PREDICT_SCRIPT": "/personal/test/dwl/ilssage-models/Model/Property_pred/Eb_predict.py",
}


class EnvManager:
    _initialized = False

    @classmethod
    def init(cls) -> None:
        if cls._initialized:
            return

        env_file = Path("~/.ilssage/env.json").expanduser()
        existing: Dict[str, str] = {}
        if env_file.exists():
            try:
                existing = json.loads(env_file.read_text())
            except (json.JSONDecodeError, IOError):
                pass

        merged = dict(_DEFAULTS)
        merged.update(existing)

        changed = False
        for k, v in merged.items():
            if k not in existing:
                changed = True
            # Only set os.environ if not already explicitly set externally
            if k not in os.environ:
                os.environ[k] = v

        if changed or not env_file.exists():
            env_file.parent.mkdir(parents=True, exist_ok=True)
            env_file.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n")

        cls._initialized = True
