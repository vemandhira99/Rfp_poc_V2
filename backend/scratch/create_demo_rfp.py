import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scratch.demo_utils import create_demo_rfp


if __name__ == "__main__":
    rfp_id = create_demo_rfp(embed=True)
    print({"demo_rfp_id": rfp_id})
