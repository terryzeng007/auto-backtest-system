import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")
VOLCENGINE_API_KEY = os.getenv("VOLCENGINE_API_KEY", "")
VOLCENGINE_MODEL = os.getenv("VOLCENGINE_MODEL", "glm-5.1")
VOLCENGINE_BASE_URL = os.getenv("VOLCENGINE_BASE_URL", "https://open.volcengineapi.com/api/v3")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"
CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"

for d in [DATA_DIR, RESULTS_DIR]:
    d.mkdir(exist_ok=True)
