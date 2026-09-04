# Seed knowledge

这些 JSONL 文件全部为项目自编的最小知识卡、解题模式、错误模式和示例，不包含教材原文。生产环境可由 `python -m signaltutor.rag.ingest` 校验并导入数据库。

## 管理员知识库

运行项目后打开 `/admin`，通过“真题知识库”可以手工录入资料，或者导入文字版 PDF、Markdown、TXT、JSON 和 JSONL。生产环境的内容默认保存在 `KNOWLEDGE_STORE_PATH`，Railway 部署建议设为 `/app/.var/knowledge.json` 并把 `/app/.var` 挂载到 Volume。

结构化 JSON 可以是数组，也可以是带 `entries` 数组的对象：

```json
[
  {
    "title": "西电 2025 年信号与系统真题第 3 题",
    "content": "题目全文与经过校对的参考解答",
    "kind": "past_exam",
    "school": "西安电子科技大学",
    "year": 2025,
    "chapter": "z_transform",
    "topics": ["逆 Z 变换", "收敛域"],
    "difficulty": 4,
    "source_page": 3,
    "source_url": "https://example.com/licensed-source",
    "published": true
  }
]
```

`kind` 可用值为 `past_exam`、`textbook`、`formula`、`syllabus`、`solution` 和 `other`。只应导入自己编写、已获授权或允许使用的资料；教材内容建议整理成知识摘要，并保留名称、页码和合法来源链接。
