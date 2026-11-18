/* 一个时间轴、一张真实 DOM 工单。翻页只改变同一舞台的布局，不替换共享元素。 */
(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const paper = [239, 236, 228], ink = [24, 28, 25], lime = [223, 255, 102];
  const clamp = (v, lo = 0, hi = 1) => Math.min(hi, Math.max(lo, v));
  const mix = (a, b, t) => a + (b - a) * t;
  const rgb = (a, b, t) => `rgb(${a.map((v, i) => Math.round(mix(v, b[i], t))).join(',')})`;
  const states = [
  {
    "title": "让故障，有下文。",
    "x": 1140,
    "y": 548,
    "w": 410,
    "h": 250,
    "r": 0,
    "dark": 0,
    "photo": [
      770,
      -20,
      830,
      780,
      1
    ],
    "accent": [
      60,
      118,
      308,
      17
    ],
    "dot": [
      1515,
      62
    ],
    "word": [
      235,
      727,
      1,
      1
    ],
    "code": "CYF20261118001",
    "subject": "气压不足",
    "detail": "夹爪气缸动作无力",
    "status": "待派单",
    "color": [
      239,
      236,
      228
    ]
  },
  {
    "title": "一张工单，走完六道关。",
    "x": 70,
    "y": 632,
    "w": 500,
    "h": 150,
    "r": 0,
    "dark": 0,
    "photo": [
      1210,
      -50,
      520,
      700,
      0
    ],
    "accent": [
      60,
      350,
      1480,
      4
    ],
    "dot": [
      71,
      390
    ],
    "word": [
      300,
      740,
      0.9,
      0
    ],
    "code": "CYF20261118001",
    "subject": "提交，只是开始。",
    "detail": "",
    "status": "驳回有意见，重提有去向",
    "color": [
      239,
      236,
      228
    ],
    "compact": true
  },
  {
    "title": "工单是中心，数据各归其位。",
    "x": 930,
    "y": 390,
    "w": 390,
    "h": 200,
    "r": 0,
    "dark": 0,
    "photo": [
      1360,
      -120,
      470,
      800,
      0
    ],
    "accent": [
      630,
      170,
      5,
      590
    ],
    "dot": [
      1050,
      399
    ],
    "word": [
      1100,
      710,
      0.6,
      0
    ],
    "code": "repair_order",
    "subject": "报修工单",
    "detail": "",
    "status": "device_id · reporter_id",
    "color": [
      223,
      255,
      102
    ],
    "compact": true
  },
  {
    "title": "十次抢单，只落一笔。",
    "x": 70,
    "y": 615,
    "w": 520,
    "h": 150,
    "r": 0,
    "dark": 1,
    "photo": [
      1260,
      -100,
      600,
      800,
      0.08
    ],
    "accent": [
      660,
      164,
      4,
      610
    ],
    "dot": [
      664,
      754
    ],
    "word": [
      490,
      720,
      0.9,
      0
    ],
    "code": "SELECT … FOR UPDATE",
    "subject": "先锁，再校验，再提交",
    "detail": "",
    "status": "状态与日志，原子写入",
    "color": [
      223,
      255,
      102
    ],
    "compact": true
  },
  {
    "title": "建议有出处，经验能回流。",
    "x": 70,
    "y": 474,
    "w": 530,
    "h": 230,
    "r": 0,
    "dark": 0,
    "photo": [
      1250,
      -100,
      520,
      850,
      0
    ],
    "accent": [
      60,
      383,
      530,
      6
    ],
    "dot": [
      640,
      265
    ],
    "word": [
      450,
      710,
      0.7,
      0
    ],
    "code": "RULES + CASE-BASED REASONING",
    "subject": "初判：气动故障",
    "detail": "规则关键词 + 相似案例",
    "status": "维修工确认实际类别",
    "color": [
      239,
      236,
      228
    ],
    "compact": false
  },
  {
    "title": "多走一步，多判对十二条。",
    "x": 70,
    "y": 619,
    "w": 525,
    "h": 150,
    "r": 0,
    "dark": 0,
    "photo": [
      1250,
      -100,
      520,
      850,
      0
    ],
    "accent": [
      60,
      372,
      530,
      6
    ],
    "dot": [
      640,
      265
    ],
    "word": [
      450,
      710,
      0.7,
      0
    ],
    "code": "QUERY EXPANSION",
    "subject": "口语 → 标准术语",
    "detail": "",
    "status": "“嘶嘶声” → “漏气”",
    "color": [
      223,
      255,
      102
    ],
    "compact": true
  },
  {
    "title": "复用索引，省下重复功。",
    "x": 70,
    "y": 616,
    "w": 525,
    "h": 150,
    "r": 0,
    "dark": 1,
    "photo": [
      1260,
      -100,
      600,
      800,
      0.08
    ],
    "accent": [
      660,
      164,
      4,
      610
    ],
    "dot": [
      664,
      754
    ],
    "word": [
      490,
      720,
      0.9,
      0
    ],
    "code": "CACHE + VERSION CHECK",
    "subject": "归档变化时，重建索引",
    "detail": "",
    "status": "日常查询，复用同一份索引",
    "color": [
      223,
      255,
      102
    ],
    "compact": true
  },
  {
    "title": "换页面，不换现场。",
    "x": 1020,
    "y": 585,
    "w": 470,
    "h": 152,
    "r": 0,
    "dark": 1,
    "photo": [
      1220,
      -80,
      680,
      850,
      0.06
    ],
    "accent": [
      60,
      359,
      435,
      7
    ],
    "dot": [
      613,
      181
    ],
    "word": [
      64,
      660,
      0.7,
      0
    ],
    "code": "CYF20261118001",
    "subject": "切页不丢登录态",
    "detail": "",
    "status": "页面退出，旧请求取消",
    "color": [
      223,
      255,
      102
    ],
    "compact": true
  },
  {
    "title": "修掉边界，数字才站得住。",
    "x": 70,
    "y": 479,
    "w": 540,
    "h": 235,
    "r": -1,
    "dark": 0,
    "photo": [
      1190,
      -80,
      620,
      850,
      0
    ],
    "accent": [
      60,
      382,
      530,
      8
    ],
    "dot": [
      711,
      151
    ],
    "word": [
      430,
      730,
      0.8,
      0
    ],
    "code": "SOURCE → REPRO → VERIFY",
    "subject": "6 项修复",
    "detail": "权限 · 业务 · 输入 · 交互",
    "status": "并发实验补上此前测试盲区",
    "color": [
      239,
      236,
      228
    ]
  },
  {
    "title": "闭环，用运行结果回答。",
    "x": 850,
    "y": 499,
    "w": 680,
    "h": 224,
    "r": 0,
    "dark": 1,
    "photo": [
      1270,
      -90,
      600,
      850,
      0.06
    ],
    "accent": [
      60,
      333,
      650,
      6
    ],
    "dot": [
      1519,
      167
    ],
    "word": [
      250,
      720,
      0.8,
      0
    ],
    "code": "CYF20261118001",
    "subject": "气动故障已处理",
    "detail": "",
    "status": "已验收 · 5 / 5",
    "color": [
      239,
      236,
      228
    ],
    "compact": true,
    "archived": true
  },
  {
    "title": "修好设备，也留下答案。",
    "x": 865,
    "y": 550,
    "w": 665,
    "h": 225,
    "r": 0,
    "dark": 0,
    "photo": [
      900,
      -20,
      700,
      780,
      1
    ],
    "accent": [
      60,
      116,
      308,
      17
    ],
    "dot": [
      1531,
      44
    ],
    "word": [
      270,
      732,
      1,
      1
    ],
    "code": "CYF20261118001",
    "subject": "经验，进入知识库。",
    "detail": "",
    "status": "归档不是终点",
    "color": [
      223,
      255,
      102
    ],
    "compact": true,
    "archived": true
  }
];
  const LAST = states.length - 1;
  const notes = [
  {
    "focus": "项目定位。用一张工单串起整场演示，不在封面堆目录。",
    "story": "题设是一家约300名员工、4个厂区的制造企业。要解决纸单易遗漏、进度看不见、经验留不住。CYF是当前工程标识，姓名、学号和班级未擅自填写。",
    "evidence": [
      "项目名称、工程目录、数据库名和工单前缀均为 CYF / cyf_jxrepair。",
      "系统已上线；摄影为生成的封面视觉，不是企业真实车间照片。"
    ],
    "sources": [
      "README.md",
      "用户附件：A卷项目背景与统一命名要求"
    ]
  },
  {
    "focus": "需求与提示词设计 10分；业务闭环 15分。",
    "story": "基础功能包括登录、用户管理、设备管理、报修与图片、列表查询、工单详情、派单与驳回、接单完工、验收评价、统计和角色隔离。拓展功能单列为诊断、知识检索、摘要、超期预警。此页同时讲清驳回重提和验收不通过的返修分支。",
    "evidence": [
      "页面：report → dispatch → workbench → order-detail。",
      "接口：POST /api/orders、/{id}/dispatch、/take、/complete、/evaluate；分支 /reject、/resubmit、/accept-fail。",
      "已有4类提示词模板：前端、数据库、后端、BUG排查；都包含技术栈、功能、输出、注释要求。"
    ],
    "sources": [
      "docs/需求分析与业务流程.md",
      "docs/提示词模板.md",
      "backend/app/services/workflow.py"
    ],
    "caveat": "TraeCN真实执行截图仍需本人补齐。本演示不把现有模板当作已执行的证明。"
  },
  {
    "focus": "数据库设计 15分。",
    "story": "5张核心表：用户、设备、工单、日志、评价；3张支撑表：部门、故障规则、预警。工单用外键关联设备和人员，既避免冗余，也让日志与评价围绕同一个工单ID聚合。",
    "evidence": [
      "工单编号唯一；状态枚举；默认时间戳；状态与时间组合索引。",
      "评价 order_id 唯一且分数限制1—5；日志保留操作人、时间和内容。",
      "13名用户、16台设备、38张工单是SQL种子数据，非线上当前总量。",
      "SQL面向MySQL 8.0；现在线上MariaDB 11.8已验证运行。",
      "idx_order_status_created(status, created_at)用于状态与时间查询；实际执行计划取决于条件和选择率，不承诺所有请求都走索引。"
    ],
    "sources": [
      "sql/01_schema.sql",
      "sql/02_seed.sql",
      "docs/数据库设计文档.md"
    ]
  },
  {
    "focus": "后端20分；业务闭环15分。展示状态机、锁和事务，而非接口数量。",
    "story": "同一轮10个独立数据库会话在屏障后并发派同一工单。原代码在MariaDB 11.8快照隔离下，每轮1次成功、9次1020数据库异常。收窄锁查询并对锁阶段快照冲突回滚重取后复验10轮，每轮1次成功、9次409业务冲突、仅1条DISPATCH日志。",
    "evidence": [
      "业务层并发调用，未经过HTTP与反向代理，不是系统吞吐或容量测试。",
      "锁查询lazyload(\"*\")避免关联JOIN；1020时在尚未写入业务数据的锁阶段回滚重取（最多3次），随后状态机校验、状态变更、日志写入在一个事务内完成。",
      "7条流转规则统一决定可执行actions；角色、归属、状态与终态校验由后端执行。",
      "4角色数据范围：员工本人、部门管理员本部门、维修工被指派、设备科全厂。",
      "完整后端包含44个OpenAPI操作；JWT、上传校验、统一响应等考试要求保留实现，主画面不逐条罗列。"
    ],
    "sources": [
      "backend/app/services/order_service.py:get_scoped / _transit",
      "backend/app/services/workflow.py",
      "research/results-before.json",
      "research/results.json",
      "https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html#joined-eager-loading"
    ],
    "caveat": "修正与本页实验是当前本地工作区结果，尚未部署到线上。现有部署仍为a03eee1。10轮实验只能证明该受控竞争场景，不能证明所有并发路径安全；新建报修防重复等路径尚未覆盖。"
  },
  {
    "focus": "AI拓展10分，重点说明可解释的本地实现与文献映射。",
    "story": "Aamodt与Plaza(1994)的CBR循环映射为：BM25检索(retrieve)、参考历史处理并投票(reuse)、维修工确认与验收(revise，人工环节)、归档案例保留(retain)。本项目实现轻量应用，不是完整复现该论文全部方法。BM25参考Robertson与Zaragoza(2009)，采用词频饱和、长度归一；中文文本用字二元组。",
    "evidence": [
      "BM25参数k1=1.2、b=0.75。IDF采用ln(1+(N-df+0.5)/(df+0.5))正值形式。",
      "Top-5案例按相似度加权类别投票，低于0.12匹配度不参与；规则得分r=s/(s+4)。",
      "融合为1-(1-r)(1-c)，是项目排序启发式。两路证据相关，未校准为真实故障概率。",
      "返回命中关键词与案例编号；故障描述重复加权不是严格BM25F实现。",
      "同时有结构化摘要、48小时超期预警；派单推荐为技能40%+负载30%+同类经验15%+满意度15%的人工加权。",
      "默认离线，无需外部模型；大模型仅可选增强，当前线上未配置。"
    ],
    "sources": [
      "backend/app/services/ai/text.py",
      "backend/app/services/ai/diagnosis.py",
      "backend/app/services/ai/knowledge.py",
      "https://www.staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf",
      "https://www.iiia.csic.es/~enric/papers/Aamodt_1994_Case.pdf"
    ],
    "caveat": "案例库增长不等于准确率必然提高。文献提供方法依据，不为本项目的性能或诊断结果背书。"
  },
  {
    "focus": "AI拓展质量：用可复现消融展示各部分作用。",
    "story": "同一份SQL种子库（26条归档案例）、同一组24条人工编写口语描述、6种故障类别。纯规则Top-1 11/24=45.8%；加案例19/24=79.2%；再加同义词23/24=95.8%。提高12条，即50个百分点，而不是提高50%。",
    "evidence": [
      "实验逐条预测、标签和失败样本见research/results.json。分母包含无判断样本。",
      "原评测的use_synonyms=False没有关闭BM25内部的同义词扩展。本次仅在独立实验中patch检索层扩展开关，统一控制两路证据，不改变生产默认行为。",
      "语料、标签与词典同属开发过程，未做独立盲测，存在词汇和案例分布重叠。",
      "样本由项目自建，没有外部专家标注验证证据，不能称为工业公开基准。"
    ],
    "sources": [
      "backend/scripts/eval_diagnosis.py:CASES",
      "research/benchmark.py",
      "research/results.json",
      "sql/02_seed.sql"
    ],
    "caveat": "95.8%仅为24条开发样本自测Top-1，不能外推为车间真实准确率，也不能声称优于商业产品。"
  },
  {
    "focus": "工程性能、算法复杂度与边界。",
    "story": "基线为每次重新构建BM25再检索；优化为复用已建索引再检索。两者同语料、同查询、同代码并核对输出一致。语料由26条种子案例重复并附唯一编号构成1千、5千、1万条，非真实业务量。各40次，报告中位数；预热5次。",
    "evidence": [
      "硬件：ARM64、4个可见逻辑CPU；Python3.11.15；数值取research/results.json。",
      "构建期O(T)（包含空文档开销时为O(T+N)）；持久索引空间O(T+N)上界。",
      "查询为O(L + S·L + NQ + H log H)，忽略固定词典和短查询预处理后主项O(NQ + H log H)；逐文档扫描并对全部命中排序。",
      "N为文档数，Q为去重后的查询词数，H为阈值以上命中数。缓存减少重复分词与统计，不改变检索渐近复杂度。",
      "线上知识服务每次仍查询归档版本，版本变化时双重检查加锁重建。本表只测纯Python算法，不含DB检查、序列化和网络。"
    ],
    "sources": [
      "backend/app/services/ai/text.py:Bm25Index",
      "backend/app/services/ai/knowledge.py:_ensure",
      "research/benchmark.py",
      "research/results.json"
    ],
    "caveat": "没有倒排索引，也未证明百万级可用。后续可引入倒排候选与Top-K堆，但PPT不将其计为已实现。"
  },
  {
    "focus": "前端页面开发 15分。",
    "story": "11指登录页加10个应用视图，不计跳转用index.html。原生HTML/CSS/JS，ECharts与字体本地化。统计看板包含月度工单量、状态分布、平均处理时长和设备故障排行4类图表。可点击截图上方的两个选项切换真实截图。",
    "evidence": [
      "报修照片选择预览、列表分页筛选检索、派单/评价弹窗、成功失败提示、会话保持与退出。",
      "此前普通链接每次创建新document；现在模板复用、共享导航、同一文档切换，实测document请求为0。",
      "History API保留前进后退与筛选；离开视图取消请求与debounce，释放图表和照片URL。",
      "初始化期间暂缓交互，避免输入被初始状态覆盖。"
    ],
    "sources": [
      "frontend/js/core/router.js",
      "frontend/js/core/http.js",
      "frontend/js/pages/dashboard.js",
      "frontend/tests/navigation.test.mjs",
      "提交 1ffecd2 / a03eee1"
    ],
    "caveat": "嵌入的是实际运行截图，不是幻灯片内连接生产数据库的后台。浏览器回归使用Chromium，未据此声称已测Edge。"
  },
  {
    "focus": "缺陷甄别与人工优化 15分。展示6项真实修复，避免只讲最终结果。",
    "story": "这些问题可通过Git对照和运行验证追溯，涉及空值、权限与数据范围、业务语义、输入边界、测试数据安全、页面生命周期。不要把它们未经举证地说成六组完整的考试过程材料。",
    "evidence": [
      "新增并发缺陷：MariaDB快照隔离竞争时产生1020；本地改为只锁工单并在锁阶段回滚重取后，10轮均得到1成功+9冲突+1日志。",
      "部门预警：加工单数据范围过滤。共享知识：独立只读案例接口。",
      "空白文本trim后校验，知识查询限制500字，日志内容控制字段长度。",
      "测试：独立<DB_NAME>_test数据库与临时uploads，防止清空业务库。",
      "导航：持久页框架、可重复mount、取消请求、释放图表、初始化保护。"
    ],
    "sources": [
      "提交 0924751",
      "提交 1ffecd2",
      "提交 a03eee1",
      "backend/tests/test_api_flow.py",
      "frontend/tests/navigation.test.mjs",
      "research/results-before.json",
      "research/results.json",
      "backend/app/services/order_service.py:本地未发布修正"
    ],
    "caveat": "考试要求的“AI原始片段→分析→人工修正→验证”四步记录、10条排查日志及注释标记，仍应按本人实际过程整理；这里没有编造AI原始记录。"
  },
  {
    "focus": "系统联调与业务闭环 15分。",
    "story": "演示工单CYF20261118001已从提交走到归档，中间实际经历驳回和重新提交，照片保留，最后验收5分。右侧为该工单真实截图。51是本次后端pytest通过数（包含新增并发回归）；9是浏览器子场景数，node输出的10还包含外层父测试。",
    "evidence": [
      "实际日志：SUBMIT、REJECT、RESUBMIT、DISPATCH、TAKE、COMPLETE、ACCEPT、ARCHIVE。",
      "9组浏览器场景覆盖全导航/图表、历史、慢请求、重试、取消旧任务、初始化保护和三类其他角色。",
      "宝塔Nginx反代到127.0.0.1:8026，服务开机启动；HTTPS证书自动续期。",
      "数据库和上传目录持久化；重启后工单与照片保留。"
    ],
    "sources": [
      "backend/tests/",
      "frontend/tests/navigation.test.mjs",
      "真实线上工单40",
      "assets/order.png",
      "本次会话的测试与部署验证记录"
    ]
  },
  {
    "focus": "交付与反思。回扣归档进入知识库，不做无内容的谢谢页。",
    "story": "系统已经可访问；从报修记录开始，最后留下可复用的维修经验。当前部署MariaDB 11.8，项目SQL目标MySQL 8.0；考试环境与报告材料应按要求单独核对。",
    "evidence": [
      "点击域名可打开线上系统；账号密码不嵌入本文件。",
      "后续可迭代：多进程下共享限流/缓存与定时任务调度、真实现场图片校验和知识质量评估。",
      "企业场景工程措施已实现：角色与行级数据权限、状态机、事务与日志、本地回退；高可用、跨进程缓存/限流、分布式任务未完成验证，避免泛称企业级。"
    ],
    "sources": [
      "README.md",
      "用户附件两份DOCX",
      "https://jxrepair.oiya.net"
    ],
    "caveat": "此HTML用于项目演示，不能代替考试报告、源码包、TraeCN执行截图和本人对代码的解释。个人信息与过程截图需据实补齐。"
  }
];

  const stage=$('#stage'), scenes=[...document.querySelectorAll('.scene')], ticket=$('#ticket');
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  let current=clamp((Number(location.hash.slice(1))||1)-1,0,LAST), target=Math.round(current), raf=0, changed=-1;
  const liveState={current,target,moving:false};
  window.deck={go, next:()=>go(target+1), previous:()=>go(target-1), state:liveState, slides:states.map(s=>s.title)};
  function resize(){
    const scale=Math.min(innerWidth/1600,innerHeight/900);
    stage.style.transform=`scale(${scale})`;
    stage.style.left=`${(innerWidth-1600*scale)/2}px`;
    stage.style.top=`${(innerHeight-900*scale)/2}px`;
    // 手机上把控制器移出缩放舞台，保留可点击的实际尺寸。
    const controls=$('#controls');
    if(innerWidth<900&&controls.parentElement!==document.body)document.body.append(controls);
    else if(innerWidth>=900&&controls.parentElement!==stage)stage.append(controls);
  }
  addEventListener('resize',resize);resize();

  function render(value){
    const lo=Math.min(LAST-1,Math.floor(value)), hi=Math.min(LAST,lo+1), t=value-lo;
    const a=states[lo], b=states[hi], near=Math.round(value), s=states[near];
    const dark=mix(a.dark,b.dark,t), color=rgb(ink,paper,dark);
    stage.style.setProperty('--stage-ink',color);
    $('#paper').style.background=rgb(paper,ink,dark);
    stage.classList.toggle('is-dark',dark>.5);
    for(const [index,scene] of scenes.entries()){
      const distance=Math.abs(index-value), visible=distance<.95;
      scene.style.visibility=visible?'visible':'hidden';
      scene.style.opacity=clamp(1-distance*1.48);
      scene.style.transform=`translate3d(${(index-value)*115}px,${(index-value)*20}px,0) scale(${1-Math.min(distance,1)*.035})`;
      scene.setAttribute('aria-hidden',index===near?'false':'true');
      scene.inert=index!==near;
      scene.classList.toggle('is-current',index===near);
    }
    const x=mix(a.x,b.x,t),y=mix(a.y,b.y,t),w=mix(a.w,b.w,t),h=mix(a.h,b.h,t);
    ticket.style.transform=`translate3d(${x}px,${y}px,0) rotate(${mix(a.r,b.r,t)}deg)`;
    ticket.style.width=`${w}px`;ticket.style.height=`${h}px`;
    ticket.style.background=rgb(a.color,b.color,t);
    const ph=a.photo.map((v,i)=>mix(v,b.photo[i],t));
    $('#photo').style.transform=`translate3d(${ph[0]}px,${ph[1]}px,0)`;
    $('#photo').style.width=`${ph[2]}px`;$('#photo').style.height=`${ph[3]}px`;$('#photo').style.opacity=ph[4];
    const ac=a.accent.map((v,i)=>mix(v,b.accent[i],t));
    $('#accent').style.transform=`translate3d(${ac[0]}px,${ac[1]}px,0)`;
    $('#accent').style.width=`${ac[2]}px`;$('#accent').style.height=`${ac[3]}px`;
    const dt=a.dot.map((v,i)=>mix(v,b.dot[i],t));
    $('#signalDot').style.transform=`translate3d(${dt[0]}px,${dt[1]}px,0)`;
    const line=`M 60 125 C ${mix(550,900,clamp(value/LAST))} 125, ${x-120} ${y+h/2}, ${x} ${y+h/2} S ${x+w+80} ${y+h/2}, 1540 790`;
    $('#threadLine').setAttribute('d',line);$('#threadBack').setAttribute('d',line);
    $('#threadLine').style.strokeDashoffset=-value*70;
    const word=a.word.map((v,i)=>mix(v,b.word[i],t));
    $('#ghostWord').style.transform=`translate3d(${word[0]-235}px,${word[1]-706}px,0) scale(${word[2]})`;
    $('#ghostWord').style.opacity=word[3];
    $('#progressFill').style.width=`${value/LAST*900}px`;
    if(changed!==near){
      changed=near;
      $('.ticket-code').textContent=s.code;$('.ticket-title').textContent=s.subject;$('.ticket-detail').textContent=s.detail;$('#ticketStatus').textContent=s.status;
      ticket.classList.toggle('compact',!!s.compact);ticket.classList.toggle('archived',!!s.archived);
      $('#ghostWord').textContent=near===LAST?'REUSE':'REPAIR';
      $('#pageNumber').textContent=String(near+1).padStart(2,'0');
      $('#announcer').textContent=`第${near+1}页，共${states.length}页。${s.title}`;
      document.title=`${String(near+1).padStart(2,'0')} · ${s.title} · CYF捷修云`;
      $('#prevBtn').disabled=near===0;$('#nextBtn').disabled=near===LAST;
      updateNotes(near);
      document.querySelectorAll('#overviewGrid button').forEach((el,i)=>el.classList.toggle('current',i===near));
    }
    liveState.current=value;liveState.target=target;
  }
  function go(index,{immediate=false,fromHistory=false}={}){
    const next=clamp(Math.round(index),0,LAST);cancelAnimationFrame(raf);target=next;liveState.target=target;
    if(!fromHistory){try{history.replaceState(null,'',`#${next+1}`);}catch{location.hash=String(next+1);}}
    const start=current,delta=target-current;
    if(immediate||reduced.matches||Math.abs(delta)<.001){current=target;render(current);liveState.moving=false;return;}
    const duration=1050+Math.min(2,Math.abs(delta))*110;
    let began;
    liveState.moving=true;
    function frame(now){
      began??=now;const p=clamp((now-began)/duration);
      const eased=p<.5?16*p**5:1-(-2*p+2)**5/2;
      current=start+delta*eased;render(current);
      if(p<1)raf=requestAnimationFrame(frame);else{current=target;render(current);liveState.moving=false;}
    }
    raf=requestAnimationFrame(frame);
  }
  function updateNotes(index){
    const note=notes[index];$('#notesTitle').textContent=`${String(index+1).padStart(2,'0')} · ${states[index].title}`;
    const body=$('#notesBody');body.replaceChildren();
    const section=(title,items)=>{const h=document.createElement('h3');h.textContent=title;body.append(h);for(const text of items){const p=document.createElement('p');if(/^https:\/\//.test(text)){const a=document.createElement('a');a.href=text;a.target='_blank';a.rel='noopener';a.textContent=text;p.append(a);}else p.textContent=text;body.append(p);}};
    section('评分重点',[note.focus]);section('讲述',[note.story]);section('可以展示的证据',note.evidence);section('来源',note.sources);
    if(note.caveat)section('如实说明',[note.caveat]);
  }
  function toggleDialog(dialog){if(dialog.open)dialog.close();else dialog.showModal();}
  states.forEach((s,index)=>{const button=document.createElement('button'),number=document.createElement('b'),title=document.createElement('span');number.textContent=String(index+1).padStart(2,'0');title.textContent=s.title;button.append(number,title);button.addEventListener('click',()=>{$('#overview').close();go(index);});$('#overviewGrid').append(button);});
  $('#nextBtn').addEventListener('click',()=>go(target+1));$('#prevBtn').addEventListener('click',()=>go(target-1));
  $('#overviewBtn').addEventListener('click',()=>toggleDialog($('#overview')));$('#notesBtn').addEventListener('click',()=>toggleDialog($('#notes')));
  $('#brand').addEventListener('click',(event)=>{event.preventDefault();go(0);});
  document.querySelectorAll('.close-dialog').forEach(button=>button.addEventListener('click',()=>button.closest('dialog').close()));
  document.querySelectorAll('dialog').forEach(dialog=>dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}}));
  async function fullscreen(){try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch{}}
  $('#fullBtn').addEventListener('click',fullscreen);
  addEventListener('keydown',(event)=>{
    if(event.altKey||event.ctrlKey||event.metaKey||event.target.matches('input,textarea,[contenteditable]'))return;
    if(document.querySelector('dialog[open]'))return;
    if(event.key===' '&&event.target.closest('button,a'))return;
    if(['ArrowRight','ArrowDown','PageDown',' '].includes(event.key)){event.preventDefault();go(target+1);}
    else if(['ArrowLeft','ArrowUp','PageUp'].includes(event.key)){event.preventDefault();go(target-1);}
    else if(event.key==='Home'){event.preventDefault();go(0);}
    else if(event.key==='End'){event.preventDefault();go(LAST);}
    else if(event.key.toLowerCase()==='m')toggleDialog($('#overview'));
    else if(event.key.toLowerCase()==='n')toggleDialog($('#notes'));
    else if(event.key.toLowerCase()==='f')fullscreen();
  });
  let touchStart;
  $('#viewport').addEventListener('touchstart',e=>{if(!e.target.closest('button,a,.screen-window'))touchStart={x:e.changedTouches[0].clientX,y:e.changedTouches[0].clientY};},{passive:true});
  $('#viewport').addEventListener('touchend',e=>{if(!touchStart)return;const dx=e.changedTouches[0].clientX-touchStart.x,dy=e.changedTouches[0].clientY-touchStart.y;if(Math.abs(dx)>50&&Math.abs(dx)>Math.abs(dy)*1.4)go(target+(dx<0?1:-1));touchStart=null;},{passive:true});
  let wheelAt=0;
  $('#viewport').addEventListener('wheel',event=>{if(event.target.closest('.screen-window')||document.querySelector('dialog[open]')||Math.abs(event.deltaY)<22)return;event.preventDefault();if(performance.now()-wheelAt<1400)return;wheelAt=performance.now();go(target+(event.deltaY>0?1:-1));},{passive:false});
  function screenshotView(which){const isDashboard=which==='dashboard';$('#productScreen').src=isDashboard?'assets/dashboard.png':'assets/report.png';$('#productScreen').alt=isDashboard?'捷修云统计看板真实运行截图':'捷修云报修与本地初判真实运行截图';$('#dashboardTab').setAttribute('aria-pressed',String(isDashboard));$('#reportTab').setAttribute('aria-pressed',String(!isDashboard));$('.screen-window').scrollTop=0;}
  $('#dashboardTab').addEventListener('click',()=>screenshotView('dashboard'));$('#reportTab').addEventListener('click',()=>screenshotView('report'));
  addEventListener('hashchange',()=>go((Number(location.hash.slice(1))||1)-1,{fromHistory:true}));
  reduced.addEventListener('change',()=>{if(reduced.matches)go(target,{immediate:true});});
  render(current);
})();
