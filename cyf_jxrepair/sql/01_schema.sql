-- =============================================================
-- CYF捷修云报修工单管理系统 —— 建表脚本
-- 数据库：cyf_jxrepair    MySQL 8.0+    字符集 utf8mb4
-- 核心表 5 张：sys_user / device / repair_order / order_log / repair_evaluation
-- 支撑表 3 张：sys_dept（部门）/ fault_knowledge（故障知识库）/ order_alert（超期预警）
-- =============================================================

DROP DATABASE IF EXISTS cyf_jxrepair;
CREATE DATABASE cyf_jxrepair DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE cyf_jxrepair;

-- -------------------------------------------------------------
-- 部门表：用户与设备都归属部门，避免在用户表中重复存储部门名称
-- -------------------------------------------------------------
CREATE TABLE sys_dept (
    id            INT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '主键',
    dept_name     VARCHAR(50)   NOT NULL                COMMENT '部门名称',
    factory_area  VARCHAR(20)   NOT NULL                COMMENT '所在厂区',
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_dept_name (dept_name)
) ENGINE = InnoDB COMMENT = '部门表';

-- -------------------------------------------------------------
-- 用户表：4 种角色
-- -------------------------------------------------------------
CREATE TABLE sys_user (
    id             INT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '主键',
    username       VARCHAR(30)   NOT NULL                COMMENT '登录账号',
    password_hash  VARCHAR(128)  NOT NULL                COMMENT '密码哈希（PBKDF2-SHA256 + 盐）',
    real_name      VARCHAR(30)   NOT NULL                COMMENT '真实姓名',
    phone          VARCHAR(20)       NULL                COMMENT '联系电话',
    role           ENUM ('EMPLOYEE', 'DEPT_ADMIN', 'DEVICE_ADMIN', 'REPAIRER')
                                 NOT NULL DEFAULT 'EMPLOYEE'
                                 COMMENT '角色：普通员工/部门管理员/设备科管理员/维修工',
    dept_id        INT UNSIGNED  NOT NULL                COMMENT '所属部门',
    skills         VARCHAR(100)      NULL                COMMENT '维修工擅长方向，逗号分隔，用于智能派单',
    is_active      TINYINT(1)    NOT NULL DEFAULT 1      COMMENT '是否启用',
    created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_username (username),
    KEY idx_user_role (role),
    CONSTRAINT fk_user_dept FOREIGN KEY (dept_id) REFERENCES sys_dept (id)
) ENGINE = InnoDB COMMENT = '用户表';

-- -------------------------------------------------------------
-- 设备台账表
-- -------------------------------------------------------------
CREATE TABLE device (
    id             INT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '主键',
    device_code    VARCHAR(30)   NOT NULL                COMMENT '设备编号',
    device_name    VARCHAR(50)   NOT NULL                COMMENT '设备名称',
    category       VARCHAR(20)   NOT NULL                COMMENT '设备类别',
    model          VARCHAR(50)       NULL                COMMENT '规格型号',
    dept_id        INT UNSIGNED  NOT NULL                COMMENT '使用部门（厂区由部门决定）',
    location       VARCHAR(50)   NOT NULL                COMMENT '安装位置',
    status         ENUM ('NORMAL', 'REPAIRING', 'SCRAPPED')
                                 NOT NULL DEFAULT 'NORMAL' COMMENT '设备状态：正常/维修中/已报废',
    purchase_date  DATE              NULL                COMMENT '购置日期',
    created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_device_code (device_code),
    KEY idx_device_category (category),
    CONSTRAINT fk_device_dept FOREIGN KEY (dept_id) REFERENCES sys_dept (id)
) ENGINE = InnoDB COMMENT = '设备台账表';

-- -------------------------------------------------------------
-- 报修工单表：只存外键，不冗余设备名称、人员姓名
-- 状态流转：PENDING待派单 → ASSIGNED待接单 → REPAIRING维修中 → TO_ACCEPT待验收 → ARCHIVED已归档
--           PENDING待派单 → REJECTED已驳回 → (重新提交) PENDING
-- -------------------------------------------------------------
CREATE TABLE repair_order (
    id             INT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '主键',
    order_no       CHAR(14)      NOT NULL                COMMENT '工单编号：CYF + yyyyMMdd + 3 位流水',
    device_id      INT UNSIGNED  NOT NULL                COMMENT '报修设备',
    reporter_id    INT UNSIGNED  NOT NULL                COMMENT '报修人',
    dispatcher_id  INT UNSIGNED      NULL                COMMENT '派单人（设备科）',
    repairer_id    INT UNSIGNED      NULL                COMMENT '维修工',
    fault_desc     VARCHAR(500)  NOT NULL                COMMENT '故障描述',
    photo_paths    JSON              NULL                COMMENT '现场照片相对路径数组，如 ["uploads/202611/a.jpg"]',
    urgency        ENUM ('LOW', 'NORMAL', 'HIGH')
                                 NOT NULL DEFAULT 'NORMAL' COMMENT '紧急程度：一般/较急/紧急',
    status         ENUM ('PENDING', 'ASSIGNED', 'REPAIRING', 'TO_ACCEPT', 'ARCHIVED', 'REJECTED')
                                 NOT NULL DEFAULT 'PENDING'
                                 COMMENT '工单状态：待派单/待接单/维修中/待验收/已归档/已驳回',
    reject_reason  VARCHAR(200)      NULL                COMMENT '最近一次驳回意见',
    repair_result  VARCHAR(500)      NULL                COMMENT '处理结果',
    created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
    dispatched_at  DATETIME          NULL                COMMENT '派单时间',
    taken_at       DATETIME          NULL                COMMENT '接单时间',
    completed_at   DATETIME          NULL                COMMENT '完工时间',
    archived_at    DATETIME          NULL                COMMENT '归档时间',
    updated_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_order_no (order_no),
    KEY idx_order_status_created (status, created_at),
    KEY idx_order_reporter (reporter_id),
    KEY idx_order_repairer (repairer_id),
    KEY idx_order_device (device_id),
    CONSTRAINT fk_order_device     FOREIGN KEY (device_id)     REFERENCES device (id),
    CONSTRAINT fk_order_reporter   FOREIGN KEY (reporter_id)   REFERENCES sys_user (id),
    CONSTRAINT fk_order_dispatcher FOREIGN KEY (dispatcher_id) REFERENCES sys_user (id),
    CONSTRAINT fk_order_repairer   FOREIGN KEY (repairer_id)   REFERENCES sys_user (id)
) ENGINE = InnoDB COMMENT = '报修工单表';

-- -------------------------------------------------------------
-- 工单流转日志表：每一次状态变化都留痕
-- -------------------------------------------------------------
CREATE TABLE order_log (
    id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    order_id     INT UNSIGNED    NOT NULL                COMMENT '工单',
    operator_id  INT UNSIGNED    NOT NULL                COMMENT '操作人',
    action       ENUM ('SUBMIT', 'DISPATCH', 'REJECT', 'RESUBMIT', 'TAKE', 'COMPLETE',
                       'ACCEPT', 'ACCEPT_FAIL', 'ARCHIVE', 'URGE')
                                 NOT NULL                COMMENT '操作类型',
    from_status  VARCHAR(20)         NULL                COMMENT '操作前状态',
    to_status    VARCHAR(20)     NOT NULL                COMMENT '操作后状态',
    content      VARCHAR(500)    NOT NULL                COMMENT '操作内容',
    created_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    PRIMARY KEY (id),
    KEY idx_log_order (order_id, created_at),
    CONSTRAINT fk_log_order    FOREIGN KEY (order_id)    REFERENCES repair_order (id) ON DELETE CASCADE,
    CONSTRAINT fk_log_operator FOREIGN KEY (operator_id) REFERENCES sys_user (id)
) ENGINE = InnoDB COMMENT = '工单流转日志表';

-- -------------------------------------------------------------
-- 维修评价表：一张工单最多一条评价
-- -------------------------------------------------------------
CREATE TABLE repair_evaluation (
    id            INT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '主键',
    order_id      INT UNSIGNED  NOT NULL                COMMENT '工单',
    evaluator_id  INT UNSIGNED  NOT NULL                COMMENT '评价人',
    score         TINYINT       NOT NULL                COMMENT '满意度 1-5 星',
    comment       VARCHAR(300)      NULL                COMMENT '评价内容',
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '评价时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_eval_order (order_id),
    CONSTRAINT ck_eval_score CHECK (score BETWEEN 1 AND 5),
    CONSTRAINT fk_eval_order     FOREIGN KEY (order_id)     REFERENCES repair_order (id) ON DELETE CASCADE,
    CONSTRAINT fk_eval_evaluator FOREIGN KEY (evaluator_id) REFERENCES sys_user (id)
) ENGINE = InnoDB COMMENT = '维修评价表';

-- -------------------------------------------------------------
-- 故障知识库：离线故障诊断使用的关键词规则
-- -------------------------------------------------------------
CREATE TABLE fault_knowledge (
    id          INT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '主键',
    category    VARCHAR(20)   NOT NULL                COMMENT '故障大类，与维修工 skills 对应',
    keywords    VARCHAR(200)  NOT NULL                COMMENT '触发关键词，逗号分隔',
    cause       VARCHAR(200)  NOT NULL                COMMENT '可能原因',
    suggestion  VARCHAR(300)  NOT NULL                COMMENT '处理建议',
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    KEY idx_kb_category (category)
) ENGINE = InnoDB COMMENT = '故障知识库';

-- -------------------------------------------------------------
-- 超期预警表：定时任务扫描写入，处理后标记
-- -------------------------------------------------------------
CREATE TABLE order_alert (
    id             INT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '主键',
    order_id       INT UNSIGNED  NOT NULL                COMMENT '工单',
    alert_type     ENUM ('DISPATCH_TIMEOUT', 'REPAIR_TIMEOUT') NOT NULL COMMENT '预警类型：超时未派单/超时未完工',
    overdue_hours  INT UNSIGNED  NOT NULL                COMMENT '扫描时已超时小时数',
    is_handled     TINYINT(1)    NOT NULL DEFAULT 0      COMMENT '是否已处理',
    handled_by     INT UNSIGNED      NULL                COMMENT '处理人，NULL 表示系统自动解除',
    handle_note    VARCHAR(200)      NULL                COMMENT '处理说明',
    created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '预警时间',
    handled_at     DATETIME          NULL                COMMENT '处理时间',
    PRIMARY KEY (id),
    KEY idx_alert_open (is_handled, alert_type),
    CONSTRAINT fk_alert_order   FOREIGN KEY (order_id)   REFERENCES repair_order (id) ON DELETE CASCADE,
    CONSTRAINT fk_alert_handler FOREIGN KEY (handled_by) REFERENCES sys_user (id)
) ENGINE = InnoDB COMMENT = '超期工单预警表';
