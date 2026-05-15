import json
from pathlib import Path
from datetime import datetime
from app.core.config import DATA_DIR

DB_PATH = DATA_DIR / "hot_questions.json"


def _load() -> list[dict]:
    if not DB_PATH.exists():
        return _default_questions()
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(questions: list[dict]):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)


def _default_questions() -> list[dict]:
    return [
        {"id": 1, "question": "PE>10且现金流为正的股票过去3年表现如何？", "click_count": 23000, "is_active": True, "priority": 0, "created_at": "2026-01-01T00:00:00"},
        {"id": 2, "question": "低PE高股息率策略回测分析", "click_count": 18000, "is_active": True, "priority": 0, "created_at": "2026-01-02T00:00:00"},
        {"id": 3, "question": "ROE>15%的白马股组合历史收益", "click_count": 15000, "is_active": True, "priority": 0, "created_at": "2026-01-03T00:00:00"},
        {"id": 4, "question": "沪深300增强型组合能跑赢指数吗？", "click_count": 12000, "is_active": True, "priority": 0, "created_at": "2026-01-04T00:00:00"},
        {"id": 5, "question": "消费板块10年定投收益率多少？", "click_count": 9600, "is_active": True, "priority": 0, "created_at": "2026-01-05T00:00:00"},
    ]


def get_hot_questions(top_n: int = 5) -> list[dict]:
    questions = [q for q in _load() if q.get("is_active", True)]
    questions.sort(key=lambda q: (-q.get("priority", 0), -q.get("click_count", 0)))
    return questions[:top_n]


def add_question(question: str) -> dict:
    questions = _load()
    new_id = max((q["id"] for q in questions), default=0) + 1
    q = {
        "id": new_id,
        "question": question,
        "click_count": 0,
        "is_active": True,
        "priority": 0,
        "created_at": datetime.now().isoformat(),
    }
    questions.append(q)
    _save(questions)
    return q


def update_question(qid: int, question: str = None, is_active: bool = None, priority: int = None) -> dict | None:
    questions = _load()
    for q in questions:
        if q["id"] == qid:
            if question is not None:
                q["question"] = question
            if is_active is not None:
                q["is_active"] = is_active
            if priority is not None:
                q["priority"] = priority
            _save(questions)
            return q
    return None


def delete_question(qid: int) -> bool:
    questions = _load()
    for q in questions:
        if q["id"] == qid:
            q["is_active"] = False
            _save(questions)
            return True
    return False


def click_question(qid: int) -> bool:
    questions = _load()
    for q in questions:
        if q["id"] == qid and q.get("is_active", True):
            q["click_count"] = q.get("click_count", 0) + 1
            _save(questions)
            return True
    return False


def list_all_questions() -> list[dict]:
    questions = _load()
    questions.sort(key=lambda q: (-q.get("priority", 0), -q.get("click_count", 0)))
    return questions
