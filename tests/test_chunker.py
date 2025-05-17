import unittest
from pathlib import Path
from llm_codesearch.chunker import iter_chunks

class IterChunksTest(unittest.TestCase):
    def test_iter_chunks_simple(self):
        root = Path(__file__).parent / "sample_repo"
        (root / "dir").mkdir(parents=True, exist_ok=True)
        (root / "dir" / "a.txt").write_text("hello world")
        chunks = list(iter_chunks(root, max_tokens=100))
        self.assertTrue(chunks)

if __name__ == "__main__":
    unittest.main()
