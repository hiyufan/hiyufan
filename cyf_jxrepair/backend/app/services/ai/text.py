"""轻量中文文本处理：不依赖 jieba 等分词库，考场离线环境也能运行。

思路：中文按"字二元组"(bigram) 切分，英文/数字按整词保留。
例如 "主轴异响ALM401" → ["主轴", "轴异", "异响", "alm401"]
"""
import math
import re
from collections import Counter

_CJK_RUN = re.compile(r"[一-鿿]+")
_WORD = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")

# 对故障检索没有区分度的高频二元组
_STOP_BIGRAMS = frozenset({"设备", "出现", "发现", "现象", "有点", "一下", "时候", "进行", "已经", "正常", "问题"})


def tokenize(text: str) -> list[str]:
    text = (text or "").lower()
    tokens: list[str] = []
    for run in _CJK_RUN.findall(text):
        if len(run) == 1:
            tokens.append(run)
        else:
            tokens.extend(run[i:i + 2] for i in range(len(run) - 1))
    tokens.extend(_WORD.findall(text))
    return [t for t in tokens if t not in _STOP_BIGRAMS]


def first_sentence(text: str, limit: int = 32) -> str:
    """取第一句并截断，用于摘要。"""
    text = (text or "").strip()
    head = re.split(r"[，,。；;！!\n]", text, maxsplit=1)[0] or text
    return head if len(head) <= limit else head[: limit - 1] + "…"


class TfidfIndex:
    """极简 TF-IDF + 余弦相似度检索。文档量在几千条以内时足够快。"""

    def __init__(self, docs: list[str]):
        self._vectors: list[dict[str, float]] = []
        df: Counter[str] = Counter()
        tfs = []
        for doc in docs:
            tf = Counter(tokenize(doc))
            tfs.append(tf)
            df.update(tf.keys())
        n = max(len(docs), 1)
        self._idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}
        self._vectors = [self._weigh(tf) for tf in tfs]

    def _weigh(self, tf: Counter[str]) -> dict[str, float]:
        vec = {t: c * self._idf.get(t, 1.0) for t, c in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def search(self, query: str, top_k: int = 5, min_score: float = 0.05) -> list[tuple[int, float]]:
        q = self._weigh(Counter(tokenize(query)))
        if not q:
            return []
        scored = []
        for idx, vec in enumerate(self._vectors):
            score = sum(w * vec.get(t, 0.0) for t, w in q.items())
            if score >= min_score:
                scored.append((idx, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
