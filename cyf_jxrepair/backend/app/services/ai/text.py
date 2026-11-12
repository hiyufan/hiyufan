"""轻量中文检索：不依赖 jieba 等分词库，考场离线环境也能运行。

1. 切词：中文按"字二元组"(bigram) 切分，英文/数字按整词保留。
   例如 "主轴异响ALM401" → ["主轴", "轴异", "异响", "alm401"]
   这是中文信息检索中免分词的常用做法：二元组能覆盖绝大多数双字词，代价只是多出一些无意义片段，
   而无意义片段在大量文档中出现，会被 IDF 自动降权。

2. 排序：Okapi BM25（Robertson & Zaragoza, "The Probabilistic Relevance Framework: BM25 and Beyond", 2009）。
   相比 TF-IDF 余弦，BM25 有两点更适合短文本故障描述：
   - 词频饱和：同一个词出现很多次，得分增长会放缓（由 k1 控制），不会被重复描述"刷分"；
   - 长度归一：长文档里词多、天然更容易命中，按文档长度与平均长度之比打折（由 b 控制）。
"""
import math
import re
from collections import Counter

_CJK_RUN = re.compile(r"[一-鿿]+")
_WORD = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")

# 对故障检索没有区分度的高频二元组
_STOP_BIGRAMS = frozenset({"设备", "出现", "发现", "现象", "有点", "一下", "时候", "进行", "已经", "正常", "问题"})


# 车间口语 → 知识库标准术语。查询扩展（query expansion）：命中口语说法时，把标准术语追加到文本后，
# 规则匹配与 BM25 检索都能用上。只做"追加"不做"替换"，原文信息不丢失。
SYNONYMS: dict[str, tuple[str, ...]] = {
    "跑偏": ("往一边偏", "偏到一边", "走偏", "偏移"),
    "皮带": ("输送带", "传送带"),
    "掉落": ("掉下去", "掉下来", "往下掉"),
    "黑屏": ("屏幕不亮", "屏不亮", "没显示", "不显示"),
    "无法启动": ("开不了机", "启动不了", "起不来", "打不着"),
    "无法起升": ("抬不起来", "升不起来", "举不起来"),
    "温度上不去": ("加热不上来", "热不起来", "升温慢"),
    "速度变慢": ("越来越慢", "变得很慢", "动作慢"),
    "漏油": ("滴油", "冒油", "往外渗油"),
    "漏气": ("嘶嘶声", "跑气"),
    "异响": ("响声大", "有怪声", "咔咔响", "嗡嗡响"),
    "跳闸": ("掉闸", "总是断电", "老是断电"),
    "焦糊": ("烧焦味", "糊味", "焦味"),
}
_SYNONYM_PAIRS = [(variant, canonical) for canonical, variants in SYNONYMS.items() for variant in variants]


def expand_synonyms(text: str) -> str:
    """把口语说法对应的标准术语追加到文本末尾。"""
    extra = {canonical for variant, canonical in _SYNONYM_PAIRS if variant in text and canonical not in text}
    return f"{text} {' '.join(sorted(extra))}" if extra else text


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


class Bm25Index:
    """Okapi BM25 检索。

    score(q, d) = Σ_{t∈q} idf(t) · tf(t,d)·(k1+1) / (tf(t,d) + k1·(1 − b + b·|d|/avgdl))
    idf(t)      = ln(1 + (N − n(t) + 0.5) / (n(t) + 0.5))      （Lucene 采用的恒正形式）

    为了在界面上显示"匹配度"，把得分除以理论上限 Σ idf(t)·(k1+1)
    （每个查询词都在文档中大量出现时才能达到），得到 0~1 之间可比较的值。
    """

    def __init__(self, docs: list[str], k1: float = 1.2, b: float = 0.75):
        self.k1, self.b = k1, b
        self._tfs = [Counter(tokenize(doc)) for doc in docs]
        self._lens = [sum(tf.values()) for tf in self._tfs]
        self.n_docs = len(docs)
        self._avgdl = (sum(self._lens) / self.n_docs) if self.n_docs else 0.0
        df: Counter[str] = Counter()
        for tf in self._tfs:
            df.update(tf.keys())
        self._idf = {t: self._idf_of(n) for t, n in df.items()}
        self._max_idf = self._idf_of(0)  # 从未出现过的词

    def _idf_of(self, n: int) -> float:
        return math.log(1 + (self.n_docs - n + 0.5) / (n + 0.5))

    def _score(self, terms: set[str], idx: int) -> float:
        tf, dl = self._tfs[idx], self._lens[idx]
        norm = self.k1 * (1 - self.b + self.b * dl / self._avgdl) if self._avgdl else self.k1
        return sum(
            self._idf[t] * tf[t] * (self.k1 + 1) / (tf[t] + norm)
            for t in terms if t in tf
        )

    def search(self, query: str, top_k: int = 5, min_match: float = 0.08) -> list[tuple[int, float]]:
        """返回 [(文档下标, 匹配度 0~1)]，按匹配度降序。"""
        terms = set(tokenize(expand_synonyms(query)))
        if not terms or not self.n_docs:
            return []
        # 理论上限：查询里没在知识库出现过的词也计入，所以"描述里有很多知识库没有的词"会拉低匹配度
        upper = sum(self._idf.get(t, self._max_idf) for t in terms) * (self.k1 + 1)
        scored = []
        for idx in range(self.n_docs):
            match = self._score(terms, idx) / upper
            if match >= min_match:
                scored.append((idx, match))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
