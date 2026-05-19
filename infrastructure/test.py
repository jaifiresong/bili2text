# mypy: disable-error-code="attr-defined"
from tinydb import TinyDB, Query, where

# 1. 创建数据库（数据会保存在 db.json 文件里）
db = TinyDB('db.json', ensure_ascii=False)  # ensure_ascii=False 支持中文

db.drop_tables()

# 2. 插入数据（单条）
db.insert({
    "name": "张三",
    "age": 20,
    "city": "北京"
})

# 3. 插入多条
db.insert_multiple([
    {"name": "李四", "age": 25, "city": "上海", "score": {"chinese": 80, "math": 90}},
    {"name": "王五", "age": 30, "city": "北京"},
    {"name": "赵六", "age": 22, "city": "深圳"}
])

# 4. 查询所有数据
all_data = db.all()
print("所有数据：", all_data)
print(db.count(Query().name == '王五'))
print(db.get(Query().score.chinese == 80))

# # 5. 条件查询
# User = Query()
# result = db.search(User.name)
# print("查询张三：", result)
#
# # 6. 模糊查询（包含某个字）
# result = db.search(User.name.search("李"))
# print("名字含李：", result)
#
# # 7. 年龄大于 22
# result = db.search(User.age > 22)
# print("年龄>22：", result)
#
# # 8. 更新数据（把张三的年龄改成 21）
# db.update({"age": 21}, User.name == "张三")
#
# # 9. 删除数据（删除王五）
# db.remove(User.name == "王五")
#
# # 10. 清空整个表
# # db.truncate()
