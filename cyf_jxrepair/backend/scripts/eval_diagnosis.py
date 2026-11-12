"""故障诊断离线评测：对比三种方案在"车间口语描述"上的准确率。

测试集是人工编写的 24 条描述，刻意使用与知识库关键词不同的说法（同义、口语、省略），
标注的是维修人员认可的故障类别。三种方案：
    A 仅规则          关键词规则匹配
    B 规则 + 案例     再加 BM25 相似案例投票（CBR）
    C 规则 + 案例 + 同义词扩展

指标：
    覆盖率   给出了任何判断的比例
    Top-1    第一判断正确的比例（分母为全部样本，没给判断也算错）
    Top-3    正确类别出现在前三的比例

用法（在 backend 目录下，需已初始化数据库）：python scripts/eval_diagnosis.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.database import SessionLocal  # noqa: E402
from app.services.ai.diagnosis import local_diagnose  # noqa: E402

CASES = [
    ("注塑机料筒加热不上来，产品缺料", "电气故障"),
    ("机器人示教器屏幕不亮，按什么都没反应", "电气故障"),
    ("配电柜有烧焦味，老是断电", "电气故障"),
    ("叉车开起来没劲，电量看着是满的", "电气故障"),
    ("货梯门关不上，电梯不走", "电气故障"),
    ("输送线电机摸着很烫，过一会就停", "电气故障"),
    ("冲床滑块下行越来越慢", "液压故障"),
    ("叉车货叉抬不起来，泵在响", "液压故障"),
    ("油缸下面有一滩油，滴油", "液压故障"),
    ("压力机保压保不住，压力往下掉", "液压故障"),
    ("注塑机开合模动作慢，油很烫", "液压故障"),
    ("输送带往一边偏，东西掉下去", "机械故障"),
    ("冷却塔风扇转起来晃得厉害，嗡嗡响", "机械故障"),
    ("主轴转的时候咔咔响", "机械故障"),
    ("机器人第三轴动起来抖", "机械故障"),
    ("模板移动时卡一下卡一下的", "机械故障"),
    ("车间里风动扳手没劲，气不够", "气动故障"),
    ("夹爪夹不住工件，有嘶嘶声", "气动故障"),
    ("分拣挡板不动作了", "气动故障"),
    ("开机报警伺服没准备好，回不了零", "数控系统"),
    ("零件尺寸一会大一会小", "数控系统"),
    ("冷却液出不来，刀具烫手", "润滑冷却"),
    ("空压机排气温度高停机了", "润滑冷却"),
    ("导轨缺油报警", "润滑冷却"),
]

CONFIGS = [
    ("A 仅规则", {"use_cases": False, "use_synonyms": False}),
    ("B 规则 + 案例", {"use_cases": True, "use_synonyms": False}),
    ("C 规则 + 案例 + 同义词", {"use_cases": True, "use_synonyms": True}),
]


def evaluate(db, options: dict) -> tuple[float, float, float, list[str]]:
    covered = top1 = top3 = 0
    misses = []
    for text, expected in CASES:
        predicted = [i.category for i in local_diagnose(db, text, **options)]
        covered += bool(predicted)
        top1 += bool(predicted) and predicted[0] == expected
        top3 += expected in predicted[:3]
        if not predicted or predicted[0] != expected:
            misses.append(f"{text} → {predicted[0] if predicted else '无判断'}（应为 {expected}）")
    n = len(CASES)
    return covered / n, top1 / n, top3 / n, misses


def main() -> None:
    with SessionLocal() as db:
        print(f"测试样本 {len(CASES)} 条\n")
        print(f"{'方案':<22}{'覆盖率':>8}{'Top-1':>8}{'Top-3':>8}")
        results = []
        for name, options in CONFIGS:
            cov, t1, t3, misses = evaluate(db, options)
            results.append((name, misses))
            print(f"{name:<20}{cov:>9.0%}{t1:>9.0%}{t3:>9.0%}")
        print(f"\n{results[-1][0]} 未判对的样本：")
        for m in results[-1][1] or ["（无）"]:
            print("  -", m)


if __name__ == "__main__":
    main()
