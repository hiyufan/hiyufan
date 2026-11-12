"""算法单元测试：BM25 检索、登录锁定。不依赖数据库。"""
import pytest

from app.core.exceptions import BizError
from app.core.login_guard import MAX_FAILURES, LoginGuard
from app.services.ai.text import Bm25Index, tokenize


def test_tokenize_bigrams_and_words():
    assert tokenize("主轴异响ALM401") == ["主轴", "轴异", "异响", "alm401"]
    assert "设备" not in tokenize("设备漏油")  # 停用二元组被过滤


def test_bm25_prefers_relevant_doc():
    idx = Bm25Index(["液压油缸漏油，保压时压力下降", "主轴异响，加工表面有振纹", "皮带跑偏，物料掉落"])
    hits = idx.search("油缸漏油")
    assert hits[0][0] == 0
    assert 0 < hits[0][1] < 1  # 匹配度归一化到 (0, 1)


def test_bm25_term_frequency_saturates():
    """词频饱和：把关键词重复 10 遍，得分不会是重复 1 遍的 10 倍。"""
    once = Bm25Index(["漏油 其他内容填充", "无关文本内容填充"]).search("漏油")[0][1]
    many = Bm25Index(["漏油" * 10 + " 其他内容填充", "无关文本内容填充"]).search("漏油")[0][1]
    assert many > once
    assert many < once * 3


def test_bm25_length_normalization():
    """同样命中一次，短文档比冗长文档更相关。"""
    idx = Bm25Index(["电机过热", "电机过热" + "，现场还有很多与故障无关的描述文字" * 5, "无关"])
    hits = dict(idx.search("电机过热", min_match=0))
    assert hits[0] > hits[1]


def test_login_guard_locks_and_expires():
    now = [0.0]
    guard = LoginGuard(clock=lambda: now[0])
    for i in range(MAX_FAILURES - 1):
        assert guard.fail("u") == MAX_FAILURES - 1 - i
    assert guard.fail("u") == 0
    with pytest.raises(BizError) as exc:
        guard.check("u")
    assert exc.value.code == 429
    now[0] += 11 * 60  # 锁定期过后可以再试
    guard.check("u")


def test_login_guard_window_slides():
    """失败次数只统计 10 分钟窗口内的，零散输错不会被锁。"""
    now = [0.0]
    guard = LoginGuard(clock=lambda: now[0])
    for _ in range(10):
        guard.fail("u")
        now[0] += 3 * 60
    guard.check("u")


def test_synonym_expansion_appends_canonical_terms():
    from app.services.ai.text import expand_synonyms
    assert "跑偏" in expand_synonyms("输送带往一边偏")
    assert expand_synonyms("主轴异响").endswith("主轴异响")  # 已是标准说法时不重复追加
