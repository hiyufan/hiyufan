# 演示数据与复验

2026-11-18，基于提交 a03eee1 及本地并发修正。原始结果为 results-before.json，修正后为 results.json；逐条诊断预测、全部并发轮次及耗时分位数均可核对。性能表使用修正后那一次运行的数据。这里的“基线”是同工程的简化实现，不是未经测量的其他产品。

## 结论与边界

- 24条自建口语描述、6类故障、26条种子归档案例：纯规则11/24、规则+案例19/24、再加同义词23/24。Top-1提高50个百分点。开发样本与词典同分布，未做盲测，不能当作实际车间准确率或与其他产品的优劣证明。
- 同义词的消融在实验进程中统一控制规则与检索两路。原评测脚本的use_synonyms=False不会关闭BM25内部扩展，故不能直接视为干净消融。业务默认行为没有因本实验改变。
- 语料由26条种子案例重复并附唯一编号构成；同一查询“夹爪夹不住工件，有嘶嘶声”，各40次，缓存查询预热5次。1万条时，中位数303.735ms→18.858ms，约16.11倍；P95为350.192ms→20.083ms。比较“每次重建+查询”与“复用索引查询”，输出结果核对一致。不是线上响应时间、容量测试或真实万条业务数据；共享主机负载也会使计时波动。
- 每轮10个业务层调用，独立数据库会话、屏障同步，10轮；不是HTTP压测。MariaDB11.8.6默认快照隔离ON、REPEATABLE-READ，原实现每轮1成功+9个1020；本地修正后每轮1成功+9个409业务冲突、1条派单日志。源文件哈希见results.json。
- 新增对应并发回归后，51项后端测试通过。9组浏览器回归为此前导航修复的验证记录；本轮另外验证了PPT自身11页、离线播放、共享DOM、键盘、总览、讲稿链接、派单类别切换、手机控制器、打断转场，无JS异常或网络依赖。

## 复验

需要项目backend依赖、运行中的MySQL/MariaDB，以及一个可创建隔离数据库的测试账号。数据库必须是全新的临时库。不要使用生产连接或生产名称。

```bash
# 自行设置测试账号；密码只从环境读取，不写入此文件。
export DB_NAME=cyf_jxrepair_bench_local
export DB_USER=your_test_user
export DB_PASSWORD=your_test_password
export LLM_API_KEY=
cd backend
python scripts/init_db.py
cd ..
python presentation/research/benchmark.py
```

脚本拒绝不以cyf_jxrepair_bench_开头的数据库名。它不创建/删除数据库，会向所选隔离库新增10条实验工单；每次复验应使用新库。结束后自行删除隔离库。本次实际使用的随机临时数据库均已删除，生产库未改动。pytest使用另一个独立的`<DB_NAME>_test`库。

本地后端变更和回归测试随concurrency-fix.patch保存，可在对应提交上查看或使用`git apply`应用。补丁尚未部署；不要把本地修正结果描述为当前线上已具备的行为。

## 复杂度

T为语料总长度，N为案例数，Q为查询去重词数，H为阈值以上命中数。索引构建期O(T+N)，非空文档常用记法O(T)，空间O(T+N)上界。查询还包含O(L+S·L)的分词和固定同义词表扫描；检索主体O(NQ+H log H)。当前实现逐文档评分、全命中排序，没有倒排索引。缓存减少重复构建工作，不会改变查询的渐近复杂度。

## 文献与实现映射

1. Robertson, S. & Zaragoza, H. (2009). *The Probabilistic Relevance Framework: BM25 and Beyond*. Foundations and Trends in Information Retrieval 3(4),333–389. DOI:10.1561/1500000019。作者所在高校提供的原文：https://www.staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf 。项目采用BM25词频饱和和长度归一，正值IDF变体；重复现象字段加权不能称为严格BM25F。
2. Aamodt, A. & Plaza, E. (1994). *Case-Based Reasoning: Foundational Issues, Methodological Variations, and System Approaches*. AI Communications 7(1),39–59. DOI:10.3233/AIC-1994-7104。作者原文：https://www.iiia.csic.es/~enric/papers/Aamodt_1994_Case.pdf 。项目把检索、建议复用、人工确认/验收和归档映射到CBR循环，不声称完整复现所有方法。
3. MariaDB官方快照隔离说明：https://mariadb.com/docs/server/reference/sql-statements/transactions/set-transaction 。1020冲突会回滚事务；本地修正在尚未进行业务写入的锁阶段回滚重取，最多3次，之后重新执行权限和状态校验。
4. SQLAlchemy关联加载与锁查询说明：https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html#joined-eager-loading 。锁查询避免joined eager loading扩大锁定范围。

规则与案例融合式`1-(1-r)(1-c)`为项目启发式评分。两路并不保证独立，匹配度与置信分未经校准，不能解释为真实故障概率。论文不是项目性能或准确率的外部背书。

## 第8/10页：派单与超期实证

`dispatch-alerts.json`由`dispatch_alerts.py`在全新隔离种子库生成；固定应用时间2026-11-18 12:00，38条工单、无预警初始状态。复验沿用上方隔离库初始化步骤，将最后一条命令改为`python presentation/research/dispatch_alerts.py`。脚本会修改2条测试工单及预警/日志，需全新种子库；结束后删除临时库。

气动与电气场景使用完全相同的维修工、负载和评价数据，仅切换故障类别。四维权重40/30/15/15为手工业务启发式；不是训练出来的模型，未证明最优。气动推荐杨帆0.762；电气推荐何振宇0.756，张国庆0.732。同分按负载、ID稳定排序。贡献条使用接口已舍入的平均评价，和总分的舍入差小于0.001。应用层评分O(R)、排序O(R log R)，不包含数据库聚合成本。

首扫7条、重扫0新增；人工一键处理1条未派单与1条未完工，分别落1条DISPATCH/URGE日志；随后重扫0新增，剩余5条预警。48h是严格超期判定阈值和已人工处理提醒的抑制周期；300秒为扫描间隔，不保证完成时限。只验证单进程顺序调用，未验证多进程并发扫描去重。催办仅写工单日志，没有外部短信通知。这不是实际运营效率、维修时长改善或所有7条已解决的证据。
