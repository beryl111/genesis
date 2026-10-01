# 待办事项

一个用 Python 标准库实现的命令行待办应用，支持新增、查看、修改和删除。数据保存在 `todo.json`。

## 运行

```bash
python3 todo.py add "买牛奶"
python3 todo.py list
python3 todo.py update 1 --title "买面包" --done
python3 todo.py delete 1
```

不带子命令时进入交互菜单：

```bash
python3 todo.py
```

也可以用 `--file` 指定其他数据文件，默认是项目目录下的 `todo.json`。

## 数据格式

```json
{
  "next_id": 2,
  "todos": [
    {
      "id": 1,
      "title": "买牛奶",
      "done": false,
      "created_at": "2026-10-01T10:00:00",
      "updated_at": "2026-10-01T10:00:00"
    }
  ]
}
```

## 测试

```bash
python3 -m unittest tests.test_todo
```
