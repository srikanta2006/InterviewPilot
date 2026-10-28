import os
import shutil
import tempfile
import pytest

# Ensure all tests use fast, deterministic, offline mock embeddings
os.environ["USE_MOCK_EMBEDDINGS"] = "1"

# Isolate ChromaDB storage to a temporary directory during automated tests
TEST_CHROMA_DIR = tempfile.mkdtemp(prefix="chroma_test_run_")
os.environ["CHROMA_PERSIST_DIRECTORY"] = TEST_CHROMA_DIR


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_chroma():
    yield
    shutil.rmtree(TEST_CHROMA_DIR, ignore_errors=True)

