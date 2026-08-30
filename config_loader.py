from pathlib import Path
import yaml

CONFIG_FILE = Path(__file__).parent / "config" / "customer_master_detail.yaml"

def load_yaml():
    with CONFIG_FILE.open("r") as f:
        return yaml.safe_load(f)