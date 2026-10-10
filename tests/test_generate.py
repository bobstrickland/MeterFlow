import hashlib
from pathlib import Path
from meterflow.generate import generateReadings


def test_same_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    file_path:Path = Path("output.csv")

    file_hash_1:str
    file_hash_2:str 
    generateReadings()

    with open(file_path, "rb") as f:
        file_hash_1 = hashlib.file_digest(f, "sha256").hexdigest()

    file_path.unlink()

    generateReadings()
    with open(file_path, "rb") as f:
        file_hash_2 = hashlib.file_digest(f, "sha256").hexdigest()
    assert file_hash_1==file_hash_2
