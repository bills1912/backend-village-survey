# app/core/utils.py
from bson import ObjectId
from typing import Any


def serialize_doc(doc: dict | None) -> dict | None:
    """Konversi ObjectId dan nested ObjectId ke string."""
    if doc is None:
        return None
    result = {}
    for k, v in doc.items():
        if k == "_id":
            result["id"] = str(v)
        elif isinstance(v, ObjectId):
            result[k] = str(v)
        elif isinstance(v, list):
            result[k] = [
                serialize_doc(i) if isinstance(i, dict) else
                (str(i) if isinstance(i, ObjectId) else i)
                for i in v
            ]
        elif isinstance(v, dict):
            result[k] = serialize_doc(v)
        else:
            result[k] = v
    return result


def serialize_list(docs: list[dict]) -> list[dict]:
    return [serialize_doc(d) for d in docs if d]
