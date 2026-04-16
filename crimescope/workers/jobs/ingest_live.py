from dataclasses import dataclass
from json import loads
from pathlib import Path


@dataclass
class JobResult:
    records_seen: int
    output_file: str


def run() -> JobResult:
    root_dir = Path(__file__).resolve().parents[2]
    sample = root_dir / "data_samples" / "live_event_package.sample.json"
    payload = loads(sample.read_text())
    return JobResult(records_seen=len(payload["events"]), output_file=str(sample))


if __name__ == "__main__":
    print(run())

