"""Build the editable course report from checked-out source and captured evidence."""
from pathlib import Path
import argparse,json,re,subprocess,textwrap
from collections import Counter
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH,WD_TAB_ALIGNMENT,WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--output-dir',default='/yufan/output/jxrepair-report');parser.add_argument('--student-info',required=True);args=parser.parse_args()
OUT=Path(args.output_dir).resolve()
PROFILE=json.loads(Path(args.student_info).read_text())
def personal(text):
 for key,value in {'【姓名】':PROFILE['name'],'【学号】':PROFILE['student_id'],'【专业班级】':PROFILE['class_name']}.items():text=text.replace(key,value)
 return text
A=OUT/'assets'
E=json.loads((OUT/'evidence.json').read_text())
SPEC=json.loads((OUT/'openapi.json').read_text())
META=json.loads((OUT/'database-metadata.json').read_text())
BENCH=json.loads((ROOT/'presentation/research/results.json').read_text())
BLOCKS=[]
def p(text):BLOCKS.append({'kind':'p','text':text})
def h(text,level=2):BLOCKS.append({'kind':'h','text':text,'level':level})
def table(headers,rows,widths=None):BLOCKS.append({'kind':'table','headers':headers,'rows':[[str(x) for x in r] for r in rows],'widths':widths})
def code(text,label=''):BLOCKS.append({'kind':'code','text':textwrap.dedent(text).strip(),'label':label})
def fig(name,caption,max_h=12):BLOCKS.append({'kind':'image','name':name,'caption':caption,'max_h':max_h})
def src(path):return (ROOT/path).read_text()
def git(ref,path):return subprocess.check_output(['git','show',f'{ref}:cyf_jxrepair/{path}'],cwd=ROOT,text=True)
def function(text,name,max_lines=35):
 m=re.search(r'^(?:async )?def '+re.escape(name)+r'\(.*?(?=^def |^async def |\Z)',text,re.M|re.S)
 return '\n'.join(m.group().splitlines()[:max_lines]) if m else ''
def plainmd(text):
 text=re.sub(r'`([^`]+)`',r'\1',text)
 return text.replace('**','').replace('<br>','；')

def md_content(text,min_level=3):
 lines=text.splitlines();i=0
 while i<len(lines):
  s=lines[i].strip()
  if s.startswith('```'):
   lang=s[3:];content=[];i+=1
   while i<len(lines) and not lines[i].startswith('```'):content.append(lines[i]);i+=1
   if lang!='mermaid':code('\n'.join(content))
  elif s.startswith('|') and i+1<len(lines) and re.match(r'\|[\s|:-]+\|',lines[i+1]):
   heads=[plainmd(x.strip()) for x in s.strip('|').split('|')];rows=[];i+=2
   while i<len(lines) and lines[i].strip().startswith('|'):
    rows.append([plainmd(x.strip()) for x in lines[i].strip().strip('|').split('|')]);i+=1
   table(heads,rows);continue
  elif s.startswith('#'):
   n=len(s)-len(s.lstrip('#'));h(plainmd(s.lstrip('#').strip()),min(3,max(2,n)))
  elif s and s!='---':p(plainmd(s.lstrip('> ')))
  i+=1

# I. Requirements and prompts.
h('一、需求拆解与结构化提示词设计',1)
h('1.1 项目背景、目标与事实范围')
p('本项目面向闽榕智造科技有限公司的设备报修场景。题设企业拥有300余名员工、4个厂区，原有纸单和电话沟通方式容易造成信息遗漏、进度不透明和维修经验流失。系统将“谁报修、谁处理、处理到哪一步、最终如何解决”组织成一张可追溯的工单，形成从提交到归档的闭环。企业人数来自题设背景，并非本系统已验证的并发用户数。')
p('系统名称为“CYF捷修云报修工单管理系统”，CYF与【姓名】的姓名缩写一致；工程目录、数据库名称和编号前缀分别为cyf_jxrepair、cyf_jxrepair和CYF。工单采用“CYF+8位日期+3位当日流水”格式，例如CYF20261118001。')
p('本报告依据当前工程源码、Git历史和2026年11月18日的运行复核编写。主体为a03eee1版本及本地MariaDB并发修正；后者尚未部署到线上。界面截图均从独立测试实例采集，测试数据不等于实际企业业务数据。报告中的提示词概念图明确标注AI生成，不作为TraeCN实际执行证明。')
h('1.2 功能需求清单与验收条件')
requirements=[
('基础','登录与角色识别','四类账号登录、保持会话、退出登录','登录后进入对应首页，未登录请求受保护接口返回401'),
('基础','提交报修','选择设备、故障描述、紧急程度与图片','生成唯一编号，图片上传到本地目录'),
('基础','列表查询','分页、状态筛选、关键词与紧急程度筛选','页面条件传给接口，结果按角色限定'),
('基础','工单详情','设备、人员、照片、状态和流转日志','同一工单ID可追溯操作历史'),
('基础','派单与驳回','设备科指派维修工或填写驳回意见','仅待派单可操作，意见留存'),
('基础','修改与重提','报修人修改被驳回工单并保留照片','同一编号重新进入待派单'),
('基础','接单与完工','维修工接单、确认故障类别和处理结果','仅本人负责的工单可流转'),
('基础','验收与评价','报修人打分、评价或退回维修','通过即归档；不通过回维修中'),
('基础','统计看板','月度工单量、状态、平均时长、故障排行','数据由数据库聚合，支持部门范围'),
('基础','用户与角色权限','设备科管理全厂，部门管理员限定部门','页面、接口与行级数据共同控制'),
('基础','设备台账','新增、编辑、筛选和删除约束','有报修记录的设备禁止删除'),
('拓展','故障智能诊断','规则、案例推理和同义词扩展','给出类别、建议和依据，供人工确认'),
('拓展','维修知识库','归档工单自动成为可检索案例','返回现象与处理结果，不开放完整工单权限'),
('拓展','智能摘要','故障、风险、处理建议结构化提取','派单、详情、统计页可查看'),
('拓展','超期预警','48小时未派单或未完工提示与处理','周期扫描；可自动派单或记录催办'),
('拓展','维修工推荐','技能、负载、经验与满意度加权','推荐给出理由，设备科仍可人工选择')]
table(['属性','需求','实现内容','验收条件'],requirements,[1.2,2.4,5.4,7.2])
h('1.3 业务全流程与页面、接口映射')
fig('flow.png','图1-1 报修闭环与驳回重提分支。归档由验收事务自动完成，不设置独立归档按钮。',16)
table(['环节','页面','接口与状态结果'],[
('提交','report.html','POST /api/orders → PENDING'),('派单','dispatch.html / order-detail.html','POST /api/orders/{id}/dispatch → ASSIGNED'),('接单','workbench.html / order-detail.html','POST /api/orders/{id}/take → REPAIRING'),('完工','workbench.html / order-detail.html','POST /api/orders/{id}/complete → TO_ACCEPT'),('验收归档','order-detail.html','POST /api/orders/{id}/evaluate → ARCHIVED'),('驳回与重提','order-detail.html / report.html?resubmit={id}','/reject → REJECTED；/resubmit → PENDING'),('验收不通过','order-detail.html','/accept-fail → REPAIRING')],[2,5,9.2])
p('题设中“派单”与“接单”是两个不同动作，因此增加ASSIGNED（待接单）状态。终态ARCHIVED禁止再次变更；前端按钮来自后端actions字段，不另外维护一套状态流转规则。')
h('1.4 技术架构与模块分工')
table(['层次','主要模块','职责'],[
('前端','HTML、CSS、ES Modules、ECharts','表单、列表、弹窗、图表；共享页框架与页面生命周期'),('接口层','backend/app/routers','参数校验、鉴权依赖、统一响应；不直接拼接SQL'),('业务层','services/workflow.py、order_service.py等','状态机、数据范围、事务、统计与预警'),('数据层','SQLAlchemy ORM / PyMySQL / InnoDB','关系约束、持久化、行锁和数据库聚合'),('离线智能层','services/ai','BM25、案例推理、摘要、可选模型适配'),('交付运行','一键脚本 / 宝塔Nginx / systemd','本地启动和域名反代部署；配置与持久化分离')],[2,5.3,8.9])
h('1.5 四类结构化提示词模板全文')
p('以下为工程docs/提示词模板.md中保存的四类可复用模板。模板包含技术栈约束、功能描述、输出格式、代码注释规范；花括号内容须在实际使用时替换。模板存在不等于已经在TraeCN中执行。')
for idx,m in enumerate(re.finditer(r'## (\d)\. ([^\n]+)\n\n```text\n(.*?)\n```',src('docs/提示词模板.md'),re.S),1):
 h('1.5.'+str(idx)+' '+m.group(2),3);code(m.group(3))
h('1.6 提示词执行材料与示意图')
fig('prompt-workflow-ai-illustration.png','图1-2 AI生成的提示词工作流概念图。界面和代码均为示意，不是TraeCN实际执行截图，也不作为项目源码。',12)
table(['材料','当前状态','真实记录应包含的内容'],[
('数据库提示词','模板已提供；实际执行截图待补','输入约束、AI输出SQL、后续修正位置'),('后端提示词','模板已提供；实际执行截图待补','目标接口、AI输出、越权与状态检查'),('前端提示词','模板已提供；实际执行截图待补','目标页面、组件输出、界面联调'),('BUG排查提示词','模板已提供；实际执行截图待补','错误信息、复现步骤、建议与运行回归')],[3,5,8.2])
p('目前工程没有可核验的TraeCN对话截图。应在本人实际使用TraeCN执行这四类任务后保存原始截图并替换上述记录位置；本报告不把概念图、Git提交或其他编程助手记录改称为TraeCN执行证据。')

# II. Database.
h('二、数据库设计',1)
h('2.1 数据表清单与设计原则')
p('数据库使用InnoDB与utf8mb4，核心表5张、支撑表3张。报修工单只保存设备和人员外键，不重复存储设备名称、人员姓名；照片保存在服务器文件目录，数据库仅保存相对路径。名称变化会反映到关联查询结果中，因此当前设计不提供人员名称的历史快照。')
table(['表名','类型','用途'],[(x,y,z) for x,y,z in [
('sys_user','核心','账号、角色、部门和维修技能'),('device','核心','设备台账与在用状态'),('repair_order','核心','报修、派单、维修、验收全过程'),('order_log','核心','每次操作的人员、内容、时间和前后状态'),('repair_evaluation','核心','一单一评，1—5星满意度'),('sys_dept','支撑','部门与厂区'),('fault_knowledge','支撑','故障关键词、原因与建议'),('order_alert','支撑','超期预警及处理记录')]], [4.2,1.5,10.5])
h('2.2 表关系与关键约束')
fig('er.png','图2-1 八张业务表的主要关系。规则知识表独立于工单外键链；用户关联含多种业务身份。',15)
p('sys_dept与sys_user、device均为一对多；device与repair_order为一对多；工单与日志、预警为一对多，与评价为一对零或一。reporter_id、dispatcher_id、repairer_id分别表示报修人、派单人、维修工，不能混为一个操作人字段。')
p('工单编号、账号、设备编号设置唯一约束；评价order_id唯一且score限制为1—5；状态与时间设置组合索引，人员、设备及故障类别设置检索索引。索引是否被使用仍取决于查询条件与选择率，不能仅凭建有索引就宣称所有接口固定提升若干倍。')
h('2.3 字段说明（依据运行数据库结构）')
cn={'sys_user':'用户表','device':'设备台账表','repair_order':'报修工单表','order_log':'工单流转日志表','repair_evaluation':'维修评价表','sys_dept':'部门表','fault_knowledge':'故障规则表','order_alert':'超期预警表'}
for idx,name in enumerate(['sys_user','device','repair_order','order_log','repair_evaluation','sys_dept','fault_knowledge','order_alert'],1):
 h(f'2.3.{idx} {name} {cn[name]}',3)
 rows=[]
 for c in META['columns']:
  if c['TABLE_NAME']!=name:continue
  typ=c['COLUMN_TYPE'];typ='ENUM' if typ.startswith('enum(') else typ
  constraint=('主键' if c['COLUMN_KEY']=='PRI' else '唯一' if c['COLUMN_KEY']=='UNI' else '索引/关联' if c['COLUMN_KEY']=='MUL' else '')
  constraint+=('；非空' if c['IS_NULLABLE']=='NO' else '；可空')
  if c['COLUMN_DEFAULT'] not in (None,'NULL'):constraint+='；默认'+str(c['COLUMN_DEFAULT'])
  rows.append([c['COLUMN_NAME'],typ,constraint.strip('；'),c['COLUMN_COMMENT'] or '—'])
 table(['字段','类型','约束/默认值','说明'],rows,[3.8,3.0,3.7,5.7])
p('补充：created_at默认CURRENT_TIMESTAMP；需要记录修改时间的updated_at由数据库自动刷新。photo_paths为JSON格式路径数组，API限制最多3张。order_log.content限制500字，因此日志使用摘要，而完整故障描述和维修结果仍保留在工单字段。')
h('2.4 可追溯的SQL迭代优化')
p('初始版本已经包含主外键、唯一约束和评价分数CHECK，不能将这些现成约束伪写为后续新增。Git提交780dc87的真实SQL变化是在repair_order加入fault_category与分类索引，使维修工确认的故障类别可作为案例标签。')
code('''-- 修正前：提交780dc87的父版本，片段
repair_result VARCHAR(500) NULL COMMENT '处理结果',
created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
-- 索引中没有 idx_order_category''','SQL优化前（Git可追溯片段）')
code('''-- 修正后：sql/01_schema.sql，片段
repair_result VARCHAR(500) NULL COMMENT '处理结果',
fault_category VARCHAR(20) NULL
    COMMENT '故障类别（维修工完工时确认，作为故障诊断的历史案例标签）',
created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
KEY idx_order_category (fault_category),''','SQL优化后（片段；非独立执行脚本）')
p('设计取舍：类别由维修工在完工时确认，避免直接把机器初判当作真实标签；归档后案例才能被共享检索。完整建表脚本位于sql/01_schema.sql，须按依赖顺序执行。初始化脚本支持环境变量指定独立库名，测试时不对业务库执行强制重建。Git差异能够证明版本变动，不能替代未提供的TraeCN原始建表输出或本人审核过程截图。')
h('2.5 种子数据与SQL执行复核')
table(['数据','数量','覆盖说明'],[
('部门',5,'生产一部、生产二部、注塑车间、仓储物流部、设备科'),('用户',13,'设备科2、部门管理员2、员工5、维修工4'),('设备',16,'4个厂区，含已报废设备'),('工单',38,'归档26、待验收3、维修中2、待接单2、待派单3、驳回2'),('流转日志',187,'包含操作人、时间、内容与前后状态'),('维修评价',26,'与归档工单对应'),('故障规则',19,'覆盖6类故障')],[3,1.5,11.7])
p('上述为sql/02_seed.sql的原始种子口径。本次复核读取独立库中原始ID范围，数量与脚本一致；闭环演示另外新增1台测试设备与1张工单，不把它们混入种子数量。完整51项后端测试包含建库、初始化和接口集成验证。')
p('SQL设计目标为题目要求的MySQL8.0；当前部署与本次复核使用MariaDB11.8.6。MariaDB能够运行此工程不等于所有MySQL功能完全等价，特别是快照隔离下的并发异常需要单独处理。最终考场仍应使用指定MySQL8.0环境验证。')

# III. Backend.
h('三、后端接口开发与调试',1)
h('3.1 分层实现、鉴权与统一响应')
p('接口通过FastAPI定义参数模型和角色依赖；services实现业务与数据范围；models映射关系表。JWT标识当前用户，密码保存为PBKDF2-SHA256加盐哈希。状态机还检查归属与当前状态，不能仅凭角色判断可否操作。业务异常、参数异常和数据库约束异常通过全局处理器转换为统一JSON。')
code('''{"code": 200, "message": "操作成功", "data": {...}}
{"code": 403, "message": "无权执行该操作", "data": null}''','通用响应结构')
table(['状态码','含义','项目中的处理'],[
(200,'成功','data为对象、列表、分页对象或null'),(401,'未登录或会话无效','携带会话的请求引导重新登录；登录密码错误由登录页显示'),(403,'角色不允许','员工不可派单、维修工不可验收'),(404,'不存在或不在可见范围','不向员工泄露其他人工单是否存在'),(409,'业务状态冲突','重复派单、归档后变更、设备已有处理中报修等'),(422,'参数校验失败','空白、过短/过长、非法枚举或评分'),(500,'非预期服务器错误','日志保留细节，响应不暴露SQL与内部结构')],[1.7,4,10.5])
h('3.2 接口清单总表（由当前OpenAPI核对）')
p('当前OpenAPI包含44个HTTP操作，含基础选项和健康检查。旧版docs/接口清单.md仍写43，本报告直接读取运行实例的OpenAPI，补入共享维修案例详情接口。除登录、部门列表、基础选项与健康检查等公开接口外，其余请求携带Authorization: Bearer <token>。下表返回列为data的精简结构示例，不是所有字段的完整实测响应；成功外层结构统一见3.1。')
def resolve(s):
 if '$ref' in s:return SPEC['components']['schemas'][s['$ref'].split('/')[-1]]
 return s

def ex(s,depth=0):
 s=resolve(s)
 if 'anyOf' in s:s=resolve(next((x for x in s['anyOf'] if x.get('type')!='null'),{'type':'null'}))
 if 'enum' in s:return s['enum'][0]
 t=s.get('type')
 if t=='array':return [] if depth>=2 else [ex(s.get('items',{}),depth+1)]
 if t=='object' or 'properties' in s:
  if depth>=2:return {}
  props=s.get('properties',{})
  if not props:return {}
  return {k:ex(v,depth+1) for k,v in list(props.items())[:2]}
 if t in ('integer','number'):return 1
 if t=='boolean':return True
 if t=='null':return None
 return '示例'
apirows=[]
for path,ops in SPEC['paths'].items():
 for method,op in ops.items():
  if method not in ['get','post','put','patch','delete']:continue
  params=[f"{v['name']}{'*' if v.get('required') else ''}({v['in']})" for v in op.get('parameters',[])]
  for mime,body in op.get('requestBody',{}).get('content',{}).items():
   model=resolve(body.get('schema',{}));required=model.get('required',[])
   params.append(('表单：' if 'multipart' in mime else 'JSON：')+'、'.join(k+('*' if k in required else '') for k in model.get('properties',{})))
  response=resolve(op.get('responses',{}).get('200',{}).get('content',{}).get('application/json',{}).get('schema',{}))
  data=response.get('properties',{}).get('data',{})
  sample_value=ex(data)
  if path=='/api/health':sample_value={'app':'CYF捷修云报修工单管理系统'}
  if path=='/api/ai/engine':sample_value={'llm_enabled':False,'llm_model':None}
  sample=json.dumps(sample_value,ensure_ascii=False,separators=(',',':'))
  if len(sample)>95:sample=sample[:92]+'…'
  apirows.append([len(apirows)+1,method.upper()+' '+path,op.get('summary',''),'; '.join(params) or '—',sample])
table(['#','方法与地址','用途','请求参数（*必填）','data结构示例'],apirows,[.9,4.3,3.0,4.4,3.6])
h('3.3 核心接口：提交报修、状态流转与权限')
code('''# routers/orders.py：先去空白，再检查长度
FaultDesc = Annotated[
    str, StringConstraints(strip_whitespace=True,
                           min_length=5, max_length=500),
    Form(description="故障描述，去除首尾空白后5~500个字"),
]''','报修参数人工复核后的边界处理')
code(function(src('backend/app/services/order_service.py'),'_transit',18),'统一流转模板（当前源码）')
p('派单前校验维修工在岗且角色正确；_transit先通过加锁查询取到可见工单，再由ensure_can检查终态、角色、归属和当前状态，之后同时写工单与日志并提交事务。完整工单接口由scope_filter限定可见行；共享知识接口只公开归档后的现象与处理结果，不扩大员工的工单访问权限。')
code('''# services/workflow.py：校验顺序
rule = TRANSITIONS[action]
if order.status in TERMINAL_STATUSES: raise Conflict(...)
if user.role not in rule.roles: raise Forbidden(...)
if not _owner_ok(rule, order, user): raise Forbidden(...)
if order.status not in rule.sources: raise Conflict(...)''','状态机检查要点（省略错误文本；完整实现见源码）')
p('图片校验同时覆盖扩展名、文件头、单张大小和总张数，允许jpg/png、每张不超过5MB、最多3张；落盘文件使用UUID命名。数据库只存相对路径。当前校验不等于完整图像解码、病毒查杀或内容识别，不能夸大为已完成全部文件安全能力。')
h('3.4 接口请求与真实返回摘录')
p('以独立测试实例为准，提交工单ID为39、编号为'+E['orderNo']+'。下面保留关键字段，令牌不写入报告。')
for title,request,response in [
('提交报修','POST /api/orders (multipart)\ndevice_id=17\nfault_desc=夹爪气缸动作无力，有嘶嘶声，夹不住工件。\nurgency=NORMAL\nphotos=<生成机械臂素材，用于上传验证>',{'code':200,'message':f"报修已提交，工单号 {E['orderNo']}",'data':{k:E['workflow'][0]['data'].get(k) for k in ['id','order_no','status','photo_urls']}}),
('验收归档','POST /api/orders/39/evaluate\n{"score":5,"comment":"压力恢复，连续试机后未复现，验收通过。"}',{'code':200,'data':{k:E['finalOrder'].get(k) for k in ['id','status','status_label','actions','evaluation']}}),
('员工无权派单','POST /api/orders/31/dispatch\n{"repairer_id":12}',E.get('examples',{}).get('forbidden',{}).get('body',{'code':403,'data':None}))]:
 h(title,3);code(request);code(json.dumps(response,ensure_ascii=False,indent=2))
h('3.5 FastAPI /docs 调试截图')
fig('25-swagger.png','图3-1 本地化Swagger UI接口文档。与本次运行实例的OpenAPI一致。',10)
fig('26-swagger-response.png','图3-2 在/docs中授权后执行GET /api/orders，返回HTTP200。访问令牌已脱敏。',15)
h('3.6 并发兼容性修正与结果')
p('MariaDB11.8默认启用innodb_snapshot_isolation，在REPEATABLE-READ下，事务先读取用户信息建立快照，再等待另一事务修改同一工单时，锁查询可能触发1020“Record has changed since last read”。因此仅使用FOR UPDATE还不足以保证所有失败均转换为业务冲突。[3]')
p('本地修正将锁查询的关联加载改为lazyload("*")，并在尚未写入业务数据的锁阶段捕获1020、回滚旧快照、重新取锁，最多尝试3次；然后重新执行权限与状态判断。其他数据库异常不被吞掉。每轮10个独立会话，连续10轮：修正前均为1成功、9个1020；修正后均为1成功、9个409冲突、1条派单日志。该实验是业务层受控竞争，不是HTTP吞吐测试，也未覆盖全部并发路径。')

# IV. Frontend.
h('四、前端页面开发与调试',1)
h('4.1 页面清单与实际联通')
page_rows=[('login.html','四类角色','登录、角色首页、退出提示'),('report.html','员工/部门管理员','设备、故障描述、照片预览、初判、重提'),('orders.html','全部登录角色','按数据范围列表、分页、筛选、检索'),('order-detail.html','按工单归属','维修单、日志、图片、操作、评价'),('dispatch.html','设备科管理员','待派单、推荐维修工、驳回'),('workbench.html','维修工','本人待接、维修中、完工、归档'),('dashboard.html','设备科/部门管理员','4类图表、指标、预警和摘要'),('devices.html','设备科管理员','台账、筛选、新增、编辑和删除约束'),('users.html','设备科/部门管理员','用户管理及部门范围'),('knowledge.html','全部登录角色','历史故障检索'),('knowledge-detail.html','全部登录角色','归档知识只读详情')]
table(['页面','使用范围','交互/接口联通'],page_rows,[4.5,4,7.7])
p('共11个实际页面，不计仅跳转用的index.html。原生ES Modules组织页面逻辑，ECharts、字体和Swagger资源本地化。fetch统一经过http.js，成功和错误消息采用统一反馈；API失败时给出重试信息，不以静态假数据替代真实结果。')
h('4.2 主要页面运行截图')
for name,caption in [('01-login.png','图4-1 登录页与角色入口（独立演示环境）。'),('12-report-filled.png','图4-2 报修表单、图片预览、故障初判与案例。上传图片是生成素材，仅用于验证上传和展示。'),('05-orders.png','图4-3 工单列表、状态页签、检索与分页。'),('07-dispatch.png','图4-4 设备科派单页。'),('10-repairer.png','图4-5 维修工工作台，仅显示本人负责工单。'),('04-devices.png','图4-6 设备台账。'),('06-users.png','图4-7 用户管理。'),('08-knowledge.png','图4-8 维修知识库检索。'),('27-knowledge-detail.png','图4-9 归档案例只读详情，不包含完整工单操作权限。')]:fig(name,caption,10)
h('4.3 三处界面优化前后对照')
p('“优化前”画面由Git初始版本e1928e8的前端重新运行取得；“优化后”为当前前端。两者连接同一独立测试实例，用于比较界面和交互表达，不代表在考场当时截取的历史截图。')
for title,before,after,caption in [
('4.3.1 报修：从单列输入到现象与依据并排','before-report.png','12-report-filled.png','故障描述与初判、相似案例并排；照片可预览、删除，错误就近提示。'),
('4.3.2 看板：从通用卡片到制造场景分区','before-dashboard.png','02-dashboard.png','使用清晰分隔线、警示带和状态文字；月度、状态、时长、排行分区呈现。'),
('4.3.3 详情：从普通卡片到纸质维修单','before-order.png','24-archived.png','设备、报修、维修和验收分段，工单号、状态印章及流转日志更易定位。')]:
 h(title,3);fig(before,'优化前：e1928e8前端重运行截图。',7.5);fig(after,'优化后：'+caption,9)
h('4.4 导航、生命周期与初始化保护')
p('旧版普通链接跳转会重新创建document，重复初始化页框架、图表与页面资源。当前保留独立HTML入口，由router.js接管站内页面切换，只替换内容区并缓存已加载模板；History API维持前进后退和筛选条件。页面mount接收AbortSignal，离开页面取消请求、清除防抖任务、释放图表和图片Object URL。')
code('''# 逻辑对照（概括）
旧版：点击链接 → 新document → 页框架与页面脚本重新执行
当前：点击导航 → 读取/复用模板 → 取消旧视图 → mount新视图
      → 更新地址与标题 → 初始化完成后解除inert/aria-busy''')
p('a03eee1补充初始化保护：设备列表等异步数据未就绪时暂缓表单交互，防止用户先输入后被初始化结果覆盖。浏览器回归验证9个子场景，包含四类角色导航、模板只请求一次、图表释放、前进后退、慢请求、失败重试和初始化保护。子场景内站内导航document请求为0；node输出的10还包含外层父测试。')
p('源码中已有“人工修改-CYF”的并发说明；历史UI修改的提交差异可以追溯，但当前前端并未统一补齐附件指定的“人工优化-姓名缩写”注释。报告不以Git记录冒充这些注释已存在，提交前应由本人核对并按实际修改补齐。浏览器本轮为Chromium156，未据此声称已在Microsoft Edge实际测试。')

# V. Defects.
h('五、AI代码缺陷甄别与人工优化记录',1)
h('5.1 记录口径与缺陷分类')
p('以下整理AI辅助工程中8组可追溯的代码问题。修正前片段来自Git真实版本或本次并发实验前版本，修正后片段对应现有源码；省略处用“...”表示，不是可直接执行的独立程序。分类覆盖参数边界、业务语义、安全与权限、冗余重复执行/生命周期、测试隔离和并发兼容。未发现证据的“调用不存在库/方法”案例不编造。Git片段不等于TraeCN最初输出，原始AI对话仍需本人据实补充。')
def defect(n,title,kind,before,analysis,after,verification,source):
 h(f'5.{n+1} 案例{n}：{title}')
 p('类型：'+kind+'。来源：'+source+'。')
 h('① 修正前代码',3);code(before)
 h('② 问题分析',3);p(analysis)
 h('③ 修正代码',3);code(after)
 h('④ 运行验证结果',3);p(verification)
defect(1,'新增设备传入null使默认参数失效','参数与空值边界',
'''// deviceForm(d = {})内部模板读取：
value="${esc(d.device_code || "")}"
$("#addBtn").addEventListener("click", () => openEditor(null));''',
'默认参数仅在参数为undefined时生效，显式传null后访问device_code会报错。该问题发生在设备新增流程，而不是编辑已存在对象时。',
'''$("#addBtn").addEventListener("click", () => openEditor());''',
'浏览器回归的管理员导航子场景点击新增设备，确认出现一个弹窗并可取消；本轮9个子场景通过。',
'0924751，frontend/js/pages/devices.js')
defect(2,'部门看板预警未限制数据范围','安全隐患/数据越权',
'''def list_open(db):
    alerts = db.scalars(select(OrderAlert).where(
        OrderAlert.is_handled.is_(False)))''',
'只筛选“未处理”会把其他部门预警返回给部门管理员。菜单隐藏和看板总数受限不能替代预警查询本身的数据隔离。',
'''visible_orders = order_service.scope_filter(select(RepairOrder.id), user)
alerts = db.scalars(select(OrderAlert).where(
    OrderAlert.is_handled.is_(False),
    OrderAlert.order_id.in_(visible_orders)))''',
'test_department_alerts_follow_order_scope比较部门可见工单与预警集合，确认只返回本部门预警且计数一致；本轮通过。',
'0924751，services/alert_service.py')
defect(3,'共享知识错误复用完整工单详情','业务语义与权限边界',
'''<a href="order-detail.html?id=${h.order_id}">${esc(h.device_name)}</a>''',
'知识库应共享维修经验，但员工查看他人工单会受到行级权限拦截。放开完整工单又会暴露人员、图片和流转信息，因此需要独立只读案例资源。',
'''<a href="knowledge-detail.html?id=${h.order_id}">${esc(h.device_name)}</a>
# 新增 GET /api/ai/knowledge/{order_id}
# 仅返回归档知识：现象、处理、设备和类别等字段''',
'test_shared_knowledge_does_not_grant_order_access验证案例200、他人工单404、未归档案例404、无登录401，并检查返回字段集合；本轮通过。',
'0924751，pages/knowledge.js、services/ai/knowledge.py')
defect(4,'原始长度检查与日志前缀造成边界漏洞','参数校验与持久化边界',
'''FaultDesc = Annotated[str, Form(min_length=5, max_length=500)]
# 故障描述可能全为空白；500字描述加“提交报修：”后超过日志列长度
content = f"提交报修：{fault_desc}"''',
'原始文本长度达标并不代表去空白后有效。日志列最多500字，而业务描述本身也可500字，再加前缀会超限；正确做法是业务全文保留、日志截断摘要。',
'''FaultDesc = Annotated[str,
    StringConstraints(strip_whitespace=True, min_length=5, max_length=500),
    Form()]
if len(content) > 500:
    content = content[:499] + "…"''',
'test_full_length_descriptions_and_results、test_resubmit_validates_trimmed_description及AI参数化测试验证全空白/501字返回422、500字可走完闭环且日志长度为500；本轮通过。',
'0924751，routers/orders.py、services/order_service.py')
defect(5,'集成测试强制重建业务库','安全隐患/测试隔离',
'''@pytest.fixture(scope="module")
def client():
    subprocess.run([sys.executable, "scripts/init_db.py", "--force"])
    with TestClient(app) as c:
        yield c''',
'测试直接读取默认配置并执行--force可能清空业务库；仅覆盖HTTP依赖仍不足以阻止后台预警任务连接原库。需要同时隔离连接、后台Session和上传目录。',
'''test_name = settings.db_name[:59] + "_test"
env = {**os.environ, "DB_NAME": test_name}
# 独立engine/session、临时uploads，并覆盖后台SessionLocal
app.dependency_overrides[get_db] = test_db
patch.setattr(alert_service, "SessionLocal", sessions)''',
'本轮以随机临时前缀运行，51项后端测试通过；结束后删除测试库，不重建生产cyf_jxrepair。',
'0924751，backend/tests/test_api_flow.py')
defect(6,'登录密码错误被误判为会话过期','业务逻辑',
'''if (payload.code === 401) {
  toLogin("expired");
  throw new ApiError(payload.message, 401);
}''',
'登录接口自身的401表示账号或密码错误，此时没有会话；无条件跳转会刷新登录页并抹掉错误提示。只有原请求携带token时才按登录失效处理。',
'''if (payload.code === 401 && token) {
  toLogin("expired");
  throw new ApiError(payload.message, 401);
}''',
'后端登录与鉴权测试检查错误密码401和未登录401。前端分支由780dc87差异核对；本轮没有把源代码检查虚写为历史登录页截图。',
'780dc87，frontend/js/core/http.js')
defect(7,'全页导航重复初始化并留下旧页面任务','冗余重复执行/生命周期',
'''// 旧版：每个页面分别执行入口逻辑
mountLayout(...);
$("#keyword").addEventListener("input", debounce((e) => {
  state.keyword = e.target.value; state.page = 1; loadList();
}, 400));
// 普通a链接触发新document''',
'导航导致整个文档重新创建；切换后旧请求和延迟任务缺少统一退出机制。仅拦截链接不能解决图表、Object URL和事件绑定的资源生命周期。',
'''export async function mount({ root, signal }) {
  const api = createApi(signal);
  signal.addEventListener("abort", () => chart?.dispose(), { once:true });
  // 请求、延迟任务和图片资源均随视图退出清理
}
// 站内切换保留页框架，模板和模块可复用''',
'9组浏览器回归验证document请求为0、页框架DOM不变、模板复用、图表已释放、慢请求不覆盖后页及初始化输入不丢失。',
'1ffecd2、a03eee1，core/router.js及页面模块；上方为机制摘录')
defect(8,'MariaDB快照冲突直接暴露数据库异常','并发与平台兼容',
'''stmt = stmt.with_for_update(of=RepairOrder)
order = db.scalar(stmt)  # 等锁后可能产生1020''',
'事务先读用户建立快照，竞争工单已被另一事务更改，MariaDB严格快照隔离可能拒绝锁定。单独收窄JOIN仍不足以消除此异常，必须在尚未发生业务写入的锁阶段回滚重取，再校验新状态。',
'''for attempt in range(3):
    stmt = scope_filter(select(RepairOrder).where(
        RepairOrder.id == order_id), user)
    if for_update:
        stmt = stmt.options(lazyload("*")).with_for_update(of=RepairOrder)
    try:
        order = db.scalar(stmt)
        break
    except OperationalError as exc:
        if not for_update or exc.orig.args[0] != 1020:
            raise
        db.rollback()
        if attempt == 2:
            raise Conflict("工单正在被其他人处理，请刷新后重试") from exc''',
'10轮各10个独立会话：修正前每轮1成功+9个1020；修正后每轮1成功+9个409+1条日志。新增test_concurrent_dispatch_with_existing_read_snapshot通过；修正尚未上线。',
'当前本地工作区；presentation/research/results-before.json与results.json')
h('5.10 排查与回归日志（本次复核记录）')
p('下表记录实际复核项目，不伪称为开发当天遗失的历史日志。测试项的通过结果来自本轮pytest、浏览器回归或受控实验；静态核对项单独注明。')
logs=[
('错误密码与未登录访问','区分登录失败和会话过期','登录401交页面；携带token的401才清会话','test_unified_response_and_auth通过；前端条件由Git核对'),
('新增设备空值报错','核对默认参数仅对undefined生效','openEditor(null)改为无参调用','浏览器新增弹窗可打开和取消'),
('部门预警越界','对照工单可见集合与预警集合','查询加入scope_filter','部门预警范围测试通过'),
('共享案例打不开','区分经验共享与工单权限','新建只读案例接口','案例200、他人工单404、未登录401'),
('空白/超长描述','按trim后长度与模型边界检查','去空白后检查5—500字','422拒绝空白/501字，500字可提交'),
('日志超过列长度','计算业务全文与前缀总长度','仅截断日志摘要','完整结果保留，日志500字'),
('测试库可能误清空','核对配置、后台任务和uploads','独立库与临时上传目录','本轮51项通过，生产不参与重建'),
('格式伪装/超大图片','检查扩展名、文件头和限额','限制jpg/png与单张5MB','test_upload_validation通过'),
('越权或跳步流转','核对角色、归属、终态和源状态','统一ensure_can','状态机参数化用例全部通过'),
('页面切换整页刷新','监听document请求和页框架引用','持久页框架与路由','站内document请求0'),
('慢请求覆盖新页面','延迟响应并快速切换','退出abort，旧任务不渲染','慢请求与返回当前菜单回归通过'),
('初始化覆盖用户输入','延迟设备初始化并提前操作','初始化完成前设inert/aria-busy','初始化保护子场景通过'),
('并发派单数据库1020','10会话屏障重现，核对隔离设置','锁阶段回滚重取并重新校验','10轮各1成功/9冲突/1日志'),
('诊断消融开关不完整','检索层仍自动扩展同义词','仅在实验中统一patch两路开关','重测11/24、19/24、23/24')]
table(['现象/检查项','排查思路','解决方案','证据/结果'],logs,[3.3,4.3,4.3,4.3])

# VI. Integration.
h('六、系统联调与业务闭环',1)
h('6.1 复核环境与操作数据')
p('本轮在127.0.0.1:8027启动隔离实例，使用随机前缀数据库与临时uploads；后端从当前工作区加载，前端为当前版本。另一端口仅用于Git旧前端对照。浏览器版本为Chromium '+E['browser']+'。报告采集没有在生产库创建、删除或修改工单。')
p('新增设备“报告联调夹爪测试台”，工单'+E['orderNo']+'（ID39），报修人emp01、设备科sbk01、维修工wx03。上传图片为生成的机械臂素材，用于验证传输、存储、保留和展示，不能当作真实故障设备照片。')
h('6.2 主流程与驳回重提的分步验证')
workflow_rows=[('提交','emp01','PENDING','编号生成，图片路径返回'),('驳回','sbk01','REJECTED','意见：补充漏气位置、压力读数与试机情况'),('修改重提','emp01','PENDING','补充0.25MPa读数，原照片保留'),('派单','sbk01','ASSIGNED','指派wx03（ID12）'),('接单','wx03','REPAIRING','记录到场与气路检查'),('完工','wx03','TO_ACCEPT','确认气动故障，填写密封圈更换与试机结果'),('验收','emp01','ARCHIVED','5星评价，形成ACCEPT与ARCHIVE日志')]
table(['步骤','账号','结果状态','实测要点'],workflow_rows,[2,2,3.4,8.8])
for name,caption in [('13-pending.png','图6-1 员工提交后的待派单工单。'),('14-reject-dialog.png','图6-2 设备科填写驳回意见。'),('15-rejected.png','图6-3 报修人查看驳回状态和意见。'),('16-resubmit-form.png','图6-4 修改重提并保留原照片。'),('17-dispatch-dialog.png','图6-5 设备科选择推荐维修工并填写派单备注。'),('20-repairing.png','图6-6 维修工接单后进入维修中。'),('21-complete-dialog.png','图6-7 完工时确认实际类别并记录处理结果。'),('23-evaluate-dialog.png','图6-8 员工验收评价。'),('24-archived.png','图6-9 验收归档后的维修单与流转记录。')]:fig(name,caption,10)
p('最终日志动作序列为：'+ ' → '.join(x['action'] for x in E['finalOrder']['logs'])+'。本次实测完整覆盖驳回重提分支；验收不通过返修由后端集成用例和种子历史案例验证，不将其写成此次ID39实际发生的动作。')
h('6.3 四种角色权限隔离')
table(['角色','页面/操作范围','数据范围','核验方式'],[
('普通员工','报修、本人列表、验收、知识','本人报修；共享知识不含完整工单权限','员工访问他人工单404；派单403'),('部门管理员','本部门统计和人员管理、报修','本部门员工工单、预警','部门预警集合与可见工单一致'),('设备科管理员','全厂统计、派单、台账、人员','全厂','可派单；已归档再派单409'),('维修工','工作台、接单、完工','指派给本人','越权流转由状态机及接口测试拦截')],[2.2,5.2,4.3,4.5])
fig('09-department.png','图6-10 部门管理员看板，范围限制为本部门。',9)
fig('11-employee-scope.png','图6-11 员工列表与角色菜单；维修工范围画面见图4-5。',9)
h('6.4 统计看板四类图表与口径')
fig('03-four-charts.png','图6-12 月度工单量、状态分布、平均处理时长与设备故障排行四类图表。',13)
p('月度工单量分别按created_at与archived_at统计提交和归档；状态分布以当前工单状态GROUP BY汇总；平均时长只取归档工单，响应为提交到接单、维修为接单到完工，总时长为提交到归档；设备故障排行排除已驳回工单。部门管理员统计统一按本部门员工报修范围过滤。')
p('test_stats_match_db验证状态分布总和等于summary.total，并检查其余统计接口可返回。本次另以独立SQL逐项对账设备科全厂、dept01本部门两种范围的月度工单量、状态分布、平均处理时长与设备排行，共8项检查全部一致。月度对账同时检查提交与归档序列；时长对账检查类别、响应和维修小时数；排行对账检查设备ID与次数。原始接口结果和SQL对账结果见statistics-reconciliation.json。')
h('6.5 自动化验证结果与边界')
table(['检查','结果','范围'],[
('后端pytest','51 passed','状态机、算法、初始化、接口、权限、上传、并发回归'),('前端浏览器回归','9个子场景通过','node总数10包含外层测试；四角色导航与生命周期'),('未登录访问','HTTP401','GET /api/orders'),('员工查看他人工单','HTTP404','GET /api/orders/5'),('空白诊断描述','HTTP422','POST /api/ai/diagnose'),('归档后再派单','HTTP409','POST /api/orders/39/dispatch'),('单工单竞争','10轮均1成功/9冲突/1日志','独立会话业务层实验，非HTTP压测'),('四类图表独立SQL对账','8项一致','设备科全厂与dept01本部门各4项'),('浏览器覆盖','Chromium156','Microsoft Edge实际测试尚待补齐')],[3.3,4,8.9])
code((OUT/'backend-tests.txt').read_text().split('===============================')[0].strip(),'本轮pytest输出')
code('\n'.join((OUT/'frontend-tests.txt').read_text().splitlines()[-9:]),'本轮前端测试输出（父测试与子测试计数）')
h('6.6 一键启动与部署说明')
code('''# Linux/macOS：MySQL已安装并启动后，在项目根目录执行
./start.sh
# Windows：双击 start.bat
# 首次运行后，在backend/.env配置数据库连接，再启动
# 默认页面：http://127.0.0.1:8000
# 接口文档：http://127.0.0.1:8000/docs''')
p('启动脚本创建独立Python虚拟环境、安装requirements、数据库不存在时初始化、再启动Uvicorn。init_db.py --force会删除并重建目标库，仅适用于明确的临时测试数据；业务库不执行该操作。数据库账号应限制权限，正式部署不使用演示密码。')
p('既有域名为https://jxrepair.oiya.net，宝塔Nginx反代至127.0.0.1:8026，后端由cyf-jxrepair服务管理；数据库与uploads持久化。该部署信息来自本次项目会话的既有交付记录，本轮报告验证针对隔离实例，不把本地并发修正写成线上已发布。')

# VII. AI.
h('七、AI智能拓展功能说明',1)
h('7.1 本地离线方案与可选模型')
p('项目采用本地可运行的规则与信息检索方案，实现故障诊断、知识检索、结构化摘要、超期预警4项题设拓展，并提供维修工推荐。配置模型接口后可增强诊断与摘要，失败时回退本地。当前部署未配置大模型密钥；没有将未启用的外部模型写成已验证能力。')
table(['功能','本地方法','页面与接口','效果/限制'],[
('故障诊断','规则+案例+同义词，启发式融合','报修页；POST /api/ai/diagnose','可追溯关键词与案例；结论需维修工确认'),('知识检索','中文二元组+BM25','知识库；GET /api/ai/knowledge','归档后自动沉淀，只读共享'),('工单摘要','规则抽取故障、风险、处理建议','派单、看板、详情；/summaries、/{id}/summary','结构化提取，非默认大模型生成'),('超期预警','48小时规则；默认300秒周期','看板；/alerts、/alerts/scan、/handle','超期未派单可推荐派单；未完工写催办日志'),('维修工推荐','人工设权线性评分','派单弹窗；GET /api/repairers','技能40%+空闲30%+经验15%+满意度15%，非训练模型')],[2.6,4.4,4.8,4.4])
h('7.2 算法逻辑、文献引用与代码')
p('BM25采用词频饱和与文档长度归一，参考Robertson与Zaragoza（2009）[1]；中文不依赖分词词典，而以连续双字片段生成词项。项目的IDF使用恒正形式，k1=1.2、b=0.75。故障现象字段重复一次以提高权重，这是简化字段加权，不是完整BM25F实现。')
code('''score(q,d) = Σ IDF(t) × tf(t,d)×(k1+1)
             / [tf(t,d)+k1×(1-b+b×|d|/avgdl)]
IDF(t) = ln[1+(N-df(t)+0.5)/(df(t)+0.5)]
k1=1.2, b=0.75''','BM25排序公式')
p('案例推理参考Aamodt与Plaza（1994）的CBR循环[2]：检索相似案例、复用处理经验、由维修工和验收人确认修正、归档保留。项目将Top-5案例按相似度加权投票，与关键词规则组合；归档保留新案例不等于准确率必然提高，仍需维护标签质量。')
code('''规则证据：r = s / (s + 4)
案例证据：类别相似度之和 / 全部相似度之和 × 可靠度折扣
融合评分：1 - (1-r)×(1-c)
# 返回命中关键词与证据工单编号，供人工复核''')
p('融合式是项目启发式排序分。规则与案例可能相关，未验证独立性，也未进行概率校准；界面“匹配度/置信度”不能解释为真实故障发生概率。')
fig('08-knowledge.png','图7-1 已归档维修案例的BM25检索结果。诊断证据见图4-2，摘要与预警见图4-4及图6-12所在看板。',9)
fig('28-summary.png','图7-2 当前工单的结构化摘要与本地引擎标识。',7)
fig('29-overdue-alert.png','图7-3 超期预警、未派单/未完工分类与一键处理入口。',8)
h('7.3 诊断消融实验')
p('固定26条种子归档案例、24条自建口语描述与6类故障。A仅规则；B规则+案例；C再加同义词。原脚本的use_synonyms=False未关闭BM25内部扩展，本次在独立实验中统一控制两路开关后重测，生产默认行为不变。')
table(['方案','Top-1正确数','Top-1','相对纯规则'],[
('A 仅规则','11/24','45.8%','基线'),('B 规则+案例','19/24','79.2%','+33.3个百分点'),('C 再加同义词','23/24','95.8%','+50.0个百分点')],[5.2,3,3,5])
p('样本由项目自建，与词典和案例开发同分布，存在词汇及分布重叠；没有独立盲测或外部专家标注证明。95.8%仅是开发集自测Top-1，不能外推为真实车间准确率，也不能宣称优于未经同条件测试的其他项目。逐条输入、标签和预测保存在presentation/research/results.json。')
h('7.4 索引缓存、复杂度与性能对照')
p('基线为每次重新构建BM25再查询，当前实现复用内存索引，归档版本变化时重建。按26条种子案例重复并添加唯一编号，构成1千、5千、1万条合成文档；固定同一查询，各40次，缓存查询先预热5次，核对输出一致。ARM64、4个可见逻辑CPU、Python3.11.15；共享主机负载会影响耗时。')
table(['合成文档数','重建+查询中位数','复用索引中位数','中位耗时比'],[[r['documents'],f"{r['rebuild_and_query']['median_ms']:.3f} ms",f"{r['warm_query']['median_ms']:.3f} ms",str(r['median_speedup'])+'×'] for r in BENCH['retrieval']],[3,4.5,4.5,4.2])
p('万条时中位数303.735ms降至18.858ms，约16.11倍；P95为350.192ms与20.083ms。这里只测纯Python构建与检索，不包含数据库版本检查、HTTP、序列化和网络，不能将该倍率写成整站响应速度或容量提升。')
table(['环节','当前复杂度','解释'],[
('索引构建','O(T+N)，非空文档常简记O(T)','T语料总长度；N案例数'),('检索主体','O(NQ + H log H)','Q去重查询词数，H阈值以上命中数'),('查询预处理','O(L + S·L)','L查询长度，S固定同义词变体数'),('索引空间','O(T+N)上界','词频字典、长度、IDF等'),('状态流转规则查找','字典平均O(1)','只表示内存规则查找，不代表SQL锁等待或整个接口O(1)')],[3.5,5.2,7.5])
p('当前BM25逐文档评分并对全部命中排序，没有倒排索引；缓存减少重复计算，不改变检索的渐近复杂度。后续可研究倒排候选与Top-K堆，但不将尚未实现的优化列为项目成果。')

# VIII. Reflection.
h('八、总结与反思',1)
h('8.1 项目完成情况')
p('工程已将报修提交、驳回重提、派单、接单、完工、验收归档、查询统计和知识沉淀连接起来。四类角色使用统一状态机和数据范围，减少前后端规则不一致；数据库通过关系约束组织事实，页面通过生命周期避免导航重复加载。当前具备企业场景需要的一部分工程措施，但尚未验证高可用、跨进程缓存与限流、分布式调度或大规模容量，不能笼统称为已经完成企业级平台。')
h('8.2 AI辅助开发中的认识')
p('AI可帮助生成模块骨架、接口说明和排查候选，但输出正确性不能由“能运行”替代。默认参数与null、登录401语义、跨部门预警和快照隔离冲突，分别说明语法、业务和平台行为都需要复核。有效的过程是先限定输入输出与边界，再检查代码，再用可复现用例验证；引用论文也要说明具体采用了哪部分方法，而不是只在报告里列一个算法名称。')
p('本次性能与准确率实验同样需要审查测量本身：关闭一个开关未必关闭所有层的功能；开发集高分不等于生产准确率；复用索引的算法耗时不等于全站延迟。报告保留原始JSON与条件说明，以便解释结果来自什么比较。')
h('8.3 后续改进方向')
table(['方向','当前边界','下一步'],[
('现场知识质量','自建样本和种子案例','采集独立样本、双人标注、盲测并分析混淆类别'),('检索规模','逐文档扫描，全命中排序','倒排索引、候选召回、Top-K与端到端测量'),('并发一致性','已验证单工单派单竞争','覆盖重复报修、验收与预警竞争等路径'),('多进程部署','缓存、限流、定时任务在进程内','共享存储、单例调度与幂等约束'),('安全运维','基础鉴权、校验与持久化','更细粒度上传授权、备份恢复、日志脱敏与权限审计'),('兼容性','Chromium本轮通过','在Microsoft Edge及指定MySQL8.0环境复核')],[3,5.2,8])
h('8.4 提交材料与待补证据')
p('本报告正文、真实运行截图、接口清单、字段说明、版本差异和量化实验已整理。以下材料具有个人过程属性，无法用生成图或事后文字替代，应由本人据实补齐后再提交。')
table(['材料','当前状态','处理方式'],[
('封面姓名/学号/班级','已填：【姓名】、【学号】、【专业班级】','核对无误后保留'),('指导老师','未取得确认，封面留空','本人填写真实指导教师'),('四类TraeCN执行截图','缺真实记录；仅有带标记概念图','在TraeCN实际执行并替换留存'),('AI最初生成片段/人工审核过程','Git版本片段已列，不等同原始对话','补原始输出和本人修改说明'),('源码人工修改注释','部分存在，未统一覆盖前端','由本人按实际变动补齐规定标记'),('Microsoft Edge实测','未提供','补充浏览器版本与真实截图'),('考场MySQL8.0环境','SQL目标已说明；本轮MariaDB复核','按指定环境重新验证并保存结果'),('个人过程复核','报告为辅助整理文本','逐条确认理解、经历与证据后使用')],[4.1,6,6.1])
p('源码包建议按“【学号】-CYF-捷修云.zip”命名。完整工程源码包与本报告应同时提交；本次“报告与证据包”只包含报告、截图、复核数据与生成脚本，不代替完整项目源码。')
h('8.5 评分记录（教师填写）')
table(['考查点','满分','得分'],[('需求拆解与结构化提示词设计',10,''),('数据库设计',15,''),('后端接口开发',20,''),('前端页面开发',15,''),('AI代码缺陷甄别与人工优化',15,''),('系统联调与业务闭环',15,''),('AI智能拓展功能',10,''),('总分',100,'')],[11,2,3.2])
h('参考资料',2)
refs=[
'[1] Robertson S, Zaragoza H. The Probabilistic Relevance Framework: BM25 and Beyond. Foundations and Trends in Information Retrieval, 2009,3(4):333–389. DOI:10.1561/1500000019. https://www.staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf',
'[2] Aamodt A, Plaza E. Case-Based Reasoning: Foundational Issues, Methodological Variations, and System Approaches. AI Communications,1994,7(1):39–59. DOI:10.3233/AIC-1994-7104. https://www.iiia.csic.es/~enric/papers/Aamodt_1994_Case.pdf',
'[3] MariaDB官方文档. SET TRANSACTION / innodb_snapshot_isolation. https://mariadb.com/docs/server/reference/sql-statements/transactions/set-transaction （核对日期：2026-11-18）',
'[4] SQLAlchemy官方文档. Joined Eager Loading / SELECT FOR UPDATE. https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html#joined-eager-loading （核对日期：2026-11-18）',
'[5] 本项目源码、sql/01_schema.sql、sql/02_seed.sql、docs/；Git e1928e8、574d3a0、780dc87、0924751、1ffecd2、a03eee1及当前本地并发修正。',
'[6] 用户提供《AI编程项目实战》A卷及评分标准，2026—2027学年第一学期，2024级人工智能技术应用专业。']
for r in refs:p(r)

# Render editable Word.
BLOCKS=json.loads(personal(json.dumps(BLOCKS,ensure_ascii=False)))
def font(run,size=12,bold=False,east='Noto Serif CJK SC',latin='Times New Roman',color=None):
 run.text=personal(run.text)
 run.font.name=latin;run.font.size=Pt(size);run.font.bold=bold
 run._element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),east)
 if color:run.font.color.rgb=RGBColor.from_string(color)

def shade(element,color):
 prop=element.get_or_add_tcPr() if element.tag==qn('w:tc') else element.get_or_add_pPr()
 sh=OxmlElement('w:shd');sh.set(qn('w:fill'),color);prop.append(sh)

def build():
 doc=Document();sec=doc.sections[0];sec.page_width=Cm(21);sec.page_height=Cm(29.7)
 sec.top_margin=Cm(2.2);sec.bottom_margin=Cm(2.0);sec.left_margin=Cm(2.5);sec.right_margin=Cm(2.3)
 sec.header_distance=Cm(.9);sec.footer_distance=Cm(.9);sec.different_first_page_header_footer=True
 normal=doc.styles['Normal'];normal.font.name='Times New Roman';normal.font.size=Pt(12)
 normal._element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'Noto Serif CJK SC')
 normal.paragraph_format.line_spacing=1.4;normal.paragraph_format.space_after=Pt(6)
 normal.paragraph_format.widow_control=True
 for i in (1,2,3):
  sty=doc.styles[f'Heading {i}'];sty.font.name='Noto Sans CJK SC';sty.font.size=Pt({1:18,2:14,3:12}[i]);sty.font.color.rgb=RGBColor.from_string('203E50');sty.font.bold=True
  sty._element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'Noto Sans CJK SC')
  sty.paragraph_format.keep_with_next=True;sty.paragraph_format.space_before=Pt(12);sty.paragraph_format.space_after=Pt(7)
  if i==1:sty.paragraph_format.page_break_before=True
 hp=sec.header.paragraphs[0];font(hp.add_run('CYF捷修云报修工单管理系统报告  |  【姓名】  【学号】'),9,east='Noto Sans CJK SC',color='697A85')
 foot=sec.footer.paragraphs[0];foot.alignment=WD_ALIGN_PARAGRAPH.CENTER
 font(foot.add_run('第 '),9)
 field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');foot._p.append(field);font(foot.add_run(' 页'),9)
 doc.core_properties.title='CYF捷修云报修工单管理系统报告';doc.core_properties.author=PROFILE['name'];doc.core_properties.subject='AI编程项目实战课程项目报告'
 for text,size in [('福州软件职业技术学院',20),('《AI编程项目实战》课程项目报告',17)]:
  pr=doc.add_paragraph();pr.alignment=WD_ALIGN_PARAGRAPH.CENTER;pr.paragraph_format.space_before=Pt(16);font(pr.add_run(text),size,True,east='Noto Sans CJK SC')
 doc.add_paragraph();pr=doc.add_paragraph();pr.alignment=WD_ALIGN_PARAGRAPH.CENTER;pr.paragraph_format.space_before=Pt(28);pr.paragraph_format.space_after=Pt(50)
 font(pr.add_run('CYF捷修云\n报修工单管理系统报告'),22,True,east='Noto Sans CJK SC')
 cover=[('课程名称','AI编程项目实战'),('系    别','智能产业学院'),('专业班级','【专业班级】'),('年    级','2024级'),('学    号','【学号】'),('姓    名','【姓名】'),('指导老师','________________')]
 for k,v in cover:
  pr=doc.add_paragraph();pr.alignment=WD_ALIGN_PARAGRAPH.CENTER;pr.paragraph_format.space_after=Pt(14);font(pr.add_run(k+'：  '+v),14)
 pr=doc.add_paragraph();pr.alignment=WD_ALIGN_PARAGRAPH.CENTER;pr.paragraph_format.space_before=Pt(35);font(pr.add_run('2026年11月19日'),14)
 doc.add_page_break();pr=doc.add_paragraph();pr.alignment=WD_ALIGN_PARAGRAPH.CENTER;font(pr.add_run('目  录'),20,True,east='Noto Sans CJK SC')
 tocfile=OUT/'toc-pages.json';toc=json.loads(tocfile.read_text()) if tocfile.exists() else {}
 for b in BLOCKS:
  if b['kind']=='h' and b['level']==1:
   pr=doc.add_paragraph();pr.paragraph_format.space_after=Pt(14);pr.paragraph_format.tab_stops.add_tab_stop(Cm(16),WD_TAB_ALIGNMENT.RIGHT,WD_TAB_LEADER.DOTS);font(pr.add_run(b['text']+'\t'+str(toc.get(b['text'],'—'))),12)
 pr=doc.add_paragraph();pr.paragraph_format.space_before=Pt(25)
 font(pr.add_run('资料说明：正文依据源码、版本差异和隔离实例运行结果编写。AI概念图、开发集评测、当前部署与本地未发布修正均已分别说明来源及范围。'),10,color='697A85')
 for b in BLOCKS:
  kind=b['kind']
  if kind=='h':doc.add_heading(b['text'],b['level'])
  elif kind=='p':
   pr=doc.add_paragraph(b['text']);pr.paragraph_format.first_line_indent=Pt(24);pr.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
  elif kind=='code':
   if b['label']:
    pr=doc.add_paragraph();pr.paragraph_format.keep_with_next=True;font(pr.add_run(b['label']),10,True,east='Noto Sans CJK SC')
   pr=doc.add_paragraph();pr.paragraph_format.first_line_indent=Pt(0);pr.paragraph_format.line_spacing=1.1;pr.paragraph_format.space_after=Pt(8)
   # Avoid an unbreakable code block; keep each individual line legible.
   run=pr.add_run(b['text']);font(run,8.6,east='Noto Sans CJK SC',latin='Liberation Mono');shade(pr._p,'F0F4F6')
  elif kind=='table':
   rows=b['rows'];heads=b['headers'];t=doc.add_table(rows=1,cols=len(heads));t.style='Table Grid';t.autofit=False
   widths=b['widths'] or ([16.2/len(heads)]*len(heads))
   scale=16.2/sum(widths)
   for col,w in zip(t.columns,widths):col.width=Cm(w*scale)
   trpr=t.rows[0]._tr.get_or_add_trPr();repeat=OxmlElement('w:tblHeader');trpr.append(repeat)
   for j,value in enumerate(heads):
    c=t.rows[0].cells[j];c.width=Cm(widths[j]*scale);c.text=value;shade(c._tc,'203E50')
    for pr in c.paragraphs:
     pr.paragraph_format.space_after=Pt(3);pr.paragraph_format.line_spacing=1.1
     for r in pr.runs:font(r,9,True,east='Noto Sans CJK SC',color='FFFFFF')
   for n,row in enumerate(rows):
    cells=t.add_row().cells
    for j,value in enumerate(row):
     if j>=len(heads):break
     c=cells[j];c.width=Cm(widths[j]*scale);c.text=str(value)
     if n%2==1:shade(c._tc,'F3F6F7')
     for pr in c.paragraphs:
      pr.paragraph_format.line_spacing=1.12;pr.paragraph_format.space_after=Pt(3);pr.paragraph_format.space_before=Pt(3)
      for r in pr.runs:font(r,9,east='Noto Sans CJK SC',latin='Liberation Sans')
    prop=t.rows[-1]._tr.get_or_add_trPr();keep=OxmlElement('w:cantSplit');prop.append(keep)
   doc.add_paragraph().paragraph_format.space_after=Pt(1)
  elif kind=='image':
   path=A/b['name']
   if not path.exists():raise FileNotFoundError(path)
   with Image.open(path) as im:w,h0=im.size
   width=min(16.2,b['max_h']*w/h0);pr=doc.add_paragraph();pr.alignment=WD_ALIGN_PARAGRAPH.CENTER;pr.paragraph_format.keep_with_next=True;pr.paragraph_format.space_after=Pt(4)
   pr.add_run().add_picture(str(path),width=Cm(width))
   cap=doc.add_paragraph();cap.alignment=WD_ALIGN_PARAGRAPH.CENTER;cap.paragraph_format.space_after=Pt(10);cap.paragraph_format.line_spacing=1.1;font(cap.add_run(b['caption']),9,east='Noto Sans CJK SC',color='51616B')
 name='【学号】-【姓名】-CYF捷修云项目报告.docx';name=personal(name);doc.save(OUT/name)
 (OUT/'report-content.json').write_text(json.dumps(BLOCKS,ensure_ascii=False,indent=2))
 # Editable plain-text content is a companion to Word, not a substitute.
 (OUT/'报告正文.txt').write_text('\n\n'.join(b.get('text',b.get('caption','')) for b in BLOCKS if b['kind']!='table'))
 print(OUT/name);print('blocks',len(BLOCKS),'tables',sum(x['kind']=='table' for x in BLOCKS),'images',sum(x['kind']=='image' for x in BLOCKS),'API operations',len(apirows))
if __name__=='__main__':build()
