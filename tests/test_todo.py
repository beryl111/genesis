import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from todo import TodoError, TodoStore, main


class TodoStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.path = Path(self.id().replace(".", "_") + ".json")
        if self.path.exists():
            self.path.unlink()
        self.store = TodoStore(self.path)

    def tearDown(self) -> None:
        if self.path.exists():
            self.path.unlink()

    def test_add_and_list(self) -> None:
        item = self.store.add("买牛奶")
        self.assertEqual(item["id"], 1)
        self.assertEqual(item["title"], "买牛奶")
        self.assertFalse(item["done"])

        another = self.store.add("写周报")
        self.assertEqual(another["id"], 2)
        self.assertEqual(
            [todo["title"] for todo in self.store.list()],
            ["买牛奶", "写周报"],
        )
        self.assertEqual(self.store.list("pending"), self.store.list())
        self.assertEqual(self.store.list("done"), [])

    def test_update_title_and_status(self) -> None:
        self.store.add("买牛奶")
        updated = self.store.update(1, title="买面包", done=True)
        self.assertEqual(updated["title"], "买面包")
        self.assertTrue(updated["done"])
        self.assertEqual(self.store.list("done")[0]["id"], 1)
        self.assertEqual(self.store.list("pending"), [])

        reopened = self.store.update(1, done=False)
        self.assertFalse(reopened["done"])
        self.assertEqual(reopened["title"], "买面包")

    def test_delete(self) -> None:
        self.store.add("买牛奶")
        self.store.add("写周报")
        removed = self.store.delete(1)
        self.assertEqual(removed["title"], "买牛奶")
        remaining = self.store.list()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["id"], 2)

    def test_persists_to_json(self) -> None:
        self.store.add("买牛奶")
        reloaded = TodoStore(self.path)
        self.assertEqual(reloaded.list()[0]["title"], "买牛奶")
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(data["next_id"], 2)
        self.assertEqual(data["todos"][0]["title"], "买牛奶")

    def test_cli_add_update_delete(self) -> None:
        path = str(self.path)
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["--file", path, "add", "买牛奶"]), 0)
            self.assertEqual(main(["--file", path, "list"]), 0)
            self.assertEqual(main(["--file", path, "update", "1", "--title", "买面包", "--done"]), 0)
            self.assertEqual(main(["--file", path, "delete", "1"]), 0)
        text = output.getvalue()
        self.assertIn("已新增 #1", text)
        self.assertIn("买牛奶", text)
        self.assertIn("已更新 #1", text)
        self.assertIn("已删除 #1", text)
        self.assertEqual(self.store.list(), [])
        self.assertEqual(main(["--file", path, "add", "   "]), 1)

    def test_rejects_empty_title_and_missing_id(self) -> None:
        with self.assertRaises(TodoError):
            self.store.add("   ")
        self.store.add("买牛奶")
        with self.assertRaises(TodoError):
            self.store.update(1)
        with self.assertRaises(TodoError):
            self.store.update(9, title="不存在")
        with self.assertRaises(TodoError):
            self.store.delete(9)


if __name__ == "__main__":
    unittest.main()
