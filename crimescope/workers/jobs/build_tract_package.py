from dataclasses import dataclass
from json import loads
from pathlib import Path


@dataclass
class PackageBuildResult:
    region_id: str
    output_file: str


def run() -> PackageBuildResult:
    root_dir = Path(__file__).resolve().parents[2]
    sample = root_dir / "data_samples" / "tract_risk_package.sample.json"
    payload = loads(sample.read_text())
    return PackageBuildResult(region_id=payload["regionId"], output_file=str(sample))


if __name__ == "__main__":
    print(run())

