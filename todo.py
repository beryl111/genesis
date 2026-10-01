#!/usr/bin/env python3
"""简单待办事项应用：增、查、改、删，数据保存在 todo.json。"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent / "todo.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class TodoError(Exception):
    """用户可修正的操作错误。"""


class TodoStore:
    """待办事项的 JSON 文件存储。"""

    def __init__(self, path: Path | str = DEFAULT_PATH) -> None:
        self.path = Path(path)

    def load(self) -> dict:
        if not self.path.exists():
            return {"next_id": 1, "todos": []}
        try:
            raw = self.path.read_text(encoding="utf-8")
            data = json.loads(raw) if raw.strip() else {"next_id": 1, "todos": []}
        except json.JSONDecodeError as exc:
            raise TodoError(f"无法读取 {self.path}：文件不是合法的 JSON") from exc
        if not isinstance(data, dict) or not isinstance(data.get("todos"), list):
            raise TodoError(f"无法读取 {self.path}：缺少 todos 列表")
        data.setdefault("next_id", self._next_id(data["todos"]))
        return data

    def save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(self.path)

    def add(self, title: str) -> dict:
        title = _require_title(title)
        data = self.load()
        now = _now()
        item = {
            "id": int(data["next_id"]),
            "title": title,
            "done": False,
            "created_at": now,
            "updated_at": now,
        }
        data["next_id"] = item["id"] + 1
        data["todos"].append(item)
        self.save(data)
        return item

    def list(self, status: str = "all") -> list[dict]:
        todos = list(self.load()["todos"])
        if status == "done":
            return [item for item in todos if item.get("done")]
        if status == "pending":
            return [item for item in todos if not item.get("done")]
        if status != "all":
            raise TodoError(f"未知的筛选条件：{status}")
        return todos

    def update(
        self,
        todo_id: int,
        title: str | None = None,
        done: bool | None = None,
    ) -> dict:
        if title is None and done is None:
            raise TodoError("请至少修改标题或完成状态中的一项")
        data = self.load()
        item = _find(data["todos"], todo_id)
        if title is not None:
            item["title"] = _require_title(title)
        if done is not None:
            item["done"] = bool(done)
        item["updated_at"] = _now()
        self.save(data)
        return item

    def delete(self, todo_id: int) -> dict:
        data = self.load()
        item = _find(data["todos"], todo_id)
        data["todos"] = [todo for todo in data["todos"] if todo["id"] != todo_id]
        self.save(data)
        return item

    @staticmethod
    def _next_id(todos: list[dict]) -> int:
        ids = [int(item["id"]) for item in todos if "id" in item]
        return max(ids, default=0) + 1


def _require_title(title: str) -> str:
    cleaned = title.strip()
    if not cleaned:
        raise TodoError("待办内容不能为空")
    return cleaned


def _find(todos: list[dict], todo_id: int) -> dict:
    for item in todos:
        if item.get("id") == todo_id:
            return item
    raise TodoError(f"找不到编号为 {todo_id} 的待办")


def _print_todos(todos: list[dict]) -> None:
    if not todos:
        print("暂无待办事项。")
        return
    print(f"{'编号':<6}{'状态':<8}{'内容'}")
    print("-" * 40)
    for item in todos:
        status = "已完成" if item.get("done") else "未完成"
        print(f"{item['id']:<6}{status:<8}{item['title']}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="待办事项：增删改查，数据保存在 todo.json",
    )
    parser.add_argument(
        "--file",
        default=str(DEFAULT_PATH),
        help="数据文件路径，默认是当前目录下的 todo.json",
    )
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add", help="新增一条待办")
    add_parser.add_argument("title", help="待办内容")

    list_parser = subparsers.add_parser("list", help="查看待办")
    list_parser.add_argument(
        "--status",
        choices=("all", "pending", "done"),
        default="all",
        help="筛选：all 全部，pending 未完成，done 已完成",
    )

    update_parser = subparsers.add_parser("update", help="修改一条待办")
    update_parser.add_argument("id", type=int, help="待办编号")
    update_parser.add_argument("--title", help="新的待办内容")
    status_group = update_parser.add_mutually_exclusive_group()
    status_group.add_argument("--done", action="store_true", help="标记为已完成")
    status_group.add_argument("--undone", action="store_true", help="标记为未完成")

    delete_parser = subparsers.add_parser("delete", help="删除一条待办")
    delete_parser.add_argument("id", type=int, help="待办编号")

    return parser


def _run_command(store: TodoStore, args: argparse.Namespace) -> int:
    if args.command == "add":
        item = store.add(args.title)
        print(f"已新增 #{item['id']}：{item['title']}")
        return 0
    if args.command == "list":
        _print_todos(store.list(args.status))
        return 0
    if args.command == "update":
        done = True if args.done else False if args.undone else None
        item = store.update(args.id, title=args.title, done=done)
        status = "已完成" if item["done"] else "未完成"
        print(f"已更新 #{item['id']}：{item['title']}（{status}）")
        return 0
    if args.command == "delete":
        item = store.delete(args.id)
        print(f"已删除 #{item['id']}：{item['title']}")
        return 0
    return _interactive(store)


def _prompt(message: str) -> str:
    try:
        return input(message).strip()
    except EOFError:
        print()
        return ""


def _interactive(store: TodoStore) -> int:
    actions = {
        "1": "查看全部待办",
        "2": "新增待办",
        "3": "修改待办",
        "4": "删除待办",
        "0": "退出",
    }
    print("待办事项")
    while True:
        print()
        for key, label in actions.items():
            print(f"{key}. {label}")
        choice = _prompt("请选择：")
        if choice in {"", "0"}:
            print("再见。")
            return 0
        try:
            if choice == "1":
                _print_todos(store.list())
            elif choice == "2":
                title = _prompt("待办内容：")
                item = store.add(title)
                print(f"已新增 #{item['id']}：{item['title']}")
            elif choice == "3":
                todo_id = int(_prompt("待办编号："))
                title = _prompt("新内容（直接回车表示不改）：")
                status = _prompt("完成状态：1 已完成，2 未完成，直接回车表示不改：")
                done = {"1": True, "2": False}.get(status)
                if status and done is None:
                    raise TodoError("完成状态请输入 1、2，或直接回车")
                item = store.update(todo_id, title=title or None, done=done)
                label = "已完成" if item["done"] else "未完成"
                print(f"已更新 #{item['id']}：{item['title']}（{label}）")
            elif choice == "4":
                todo_id = int(_prompt("要删除的编号："))
                item = store.delete(todo_id)
                print(f"已删除 #{item['id']}：{item['title']}")
            else:
                print("请输入菜单中的数字。")
        except TodoError as exc:
            print(f"操作失败：{exc}")
        except ValueError:
            print("操作失败：编号必须是数字。")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    store = TodoStore(args.file)
    try:
        return _run_command(store, args)
    except TodoError as exc:
        print(f"操作失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
