-- KnowFlow AI 演示数据脚本
-- 用途：
-- 1. 给已经建好的 KnowFlow 表插入一套可演示的假数据
-- 2. 每张表严格插入 4 条数据
-- 3. 数据围绕“公司制度知识库”主题，适合前端页面联动演示
--
-- 注意：
-- 1. 这份脚本假设表已经存在
-- 2. 这份脚本使用固定 ID，便于跨表建立稳定关联
-- 3. 再次执行时会基于主键做更新，不会重复插入同一批数据

BEGIN;

-- =========================================================
-- 1. 用户表：4 个内部账号
-- =========================================================
INSERT INTO users (id, username, email, hashed_password, created_at, updated_at)
VALUES
    -- 演示密码统一为 demo123456（bcrypt）；已有库可重跑本脚本或单独 UPDATE hashed_password
    (101, 'hr_admin', 'hr_admin@knowflow.ai', '$2b$12$jLRQnn2kAn3atfpId52Xsuxk58qSlsblfVt4mDxlwZEFHTyNbYP..', NOW(), NOW()),
    (102, 'finance_admin', 'finance_admin@knowflow.ai', '$2b$12$jLRQnn2kAn3atfpId52Xsuxk58qSlsblfVt4mDxlwZEFHTyNbYP..', NOW(), NOW()),
    (103, 'ops_admin', 'ops_admin@knowflow.ai', '$2b$12$jLRQnn2kAn3atfpId52Xsuxk58qSlsblfVt4mDxlwZEFHTyNbYP..', NOW(), NOW()),
    (104, 'employee_demo', 'employee_demo@knowflow.ai', '$2b$12$jLRQnn2kAn3atfpId52Xsuxk58qSlsblfVt4mDxlwZEFHTyNbYP..', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
    username = EXCLUDED.username,
    email = EXCLUDED.email,
    hashed_password = EXCLUDED.hashed_password,
    updated_at = NOW();

-- =========================================================
-- 2. 知识库表：4 个制度知识库
-- =========================================================
INSERT INTO knowledge_bases (id, name, description, owner_id, created_at, updated_at)
VALUES
    (201, '员工请假制度库', '用于回答年假、病假、事假和请假流程相关问题。', 101, NOW(), NOW()),
    (202, '员工报销制度库', '用于回答差旅、餐补、打车和发票报销相关问题。', 102, NOW(), NOW()),
    (203, '新员工入职制度库', '用于回答入职材料、试用期和入职流程相关问题。', 103, NOW(), NOW()),
    (204, '远程办公制度库', '用于回答远程办公申请、审批和考勤要求相关问题。', 101, NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    owner_id = EXCLUDED.owner_id,
    updated_at = NOW();

-- =========================================================
-- 3. 文档表：每个知识库 1 份制度文档
-- =========================================================
INSERT INTO documents (
    id,
    knowledge_base_id,
    file_name,
    file_type,
    file_path,
    file_size,
    status,
    error_message,
    chunk_count,
    created_at,
    updated_at
)
VALUES
    (301, 201, 'leave_policy_2026.pdf', 'pdf', '/demo/leave_policy_2026.pdf', 248576, 'chunked', NULL, 1, NOW(), NOW()),
    (302, 202, 'expense_policy_2026.pdf', 'pdf', '/demo/expense_policy_2026.pdf', 315904, 'chunked', NULL, 1, NOW(), NOW()),
    (303, 203, 'onboarding_guide_2026.pdf', 'pdf', '/demo/onboarding_guide_2026.pdf', 287232, 'chunked', NULL, 1, NOW(), NOW()),
    (304, 204, 'remote_work_policy_2026.pdf', 'pdf', '/demo/remote_work_policy_2026.pdf', 226304, 'chunked', NULL, 1, NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
    knowledge_base_id = EXCLUDED.knowledge_base_id,
    file_name = EXCLUDED.file_name,
    file_type = EXCLUDED.file_type,
    file_path = EXCLUDED.file_path,
    file_size = EXCLUDED.file_size,
    status = EXCLUDED.status,
    error_message = EXCLUDED.error_message,
    chunk_count = EXCLUDED.chunk_count,
    updated_at = NOW();

-- =========================================================
-- 4. 文档切片表：每个文档 1 个核心摘要切片，共 4 条
-- =========================================================
INSERT INTO document_chunks (
    id,
    document_id,
    knowledge_base_id,
    chunk_index,
    content,
    content_hash,
    page_number,
    token_count,
    vector_id,
    metadata,
    created_at
)
VALUES
    (
        401,
        301,
        201,
        0,
        '员工申请年假需至少提前 3 个工作日提交审批，病假 1 天以内可补提申请，超过 1 天需上传医院证明。',
        'hash_leave_policy_401',
        2,
        58,
        'vec_leave_401',
        '{"section":"请假申请","topic":"年假与病假规则"}'::jsonb,
        NOW()
    ),
    (
        402,
        302,
        202,
        0,
        '差旅报销需在行程结束后 10 个自然日内提交，餐饮发票需附消费明细，打车报销单次上限为 120 元。',
        'hash_expense_policy_402',
        3,
        64,
        'vec_expense_402',
        '{"section":"报销时限","topic":"差旅与打车报销"}'::jsonb,
        NOW()
    ),
    (
        403,
        303,
        203,
        0,
        '新员工入职当天需携带身份证、学历证明、银行卡信息和一寸照片，试用期默认 3 个月。',
        'hash_onboarding_policy_403',
        1,
        52,
        'vec_onboarding_403',
        '{"section":"入职材料","topic":"入职准备与试用期"}'::jsonb,
        NOW()
    ),
    (
        404,
        304,
        204,
        0,
        '员工每周最多可申请 2 天远程办公，需至少提前 1 天提交申请，并获得直属主管审批后方可执行。',
        'hash_remote_policy_404',
        4,
        60,
        'vec_remote_404',
        '{"section":"远程办公申请","topic":"审批与频次限制"}'::jsonb,
        NOW()
    )
ON CONFLICT (id) DO UPDATE SET
    document_id = EXCLUDED.document_id,
    knowledge_base_id = EXCLUDED.knowledge_base_id,
    chunk_index = EXCLUDED.chunk_index,
    content = EXCLUDED.content,
    content_hash = EXCLUDED.content_hash,
    page_number = EXCLUDED.page_number,
    token_count = EXCLUDED.token_count,
    vector_id = EXCLUDED.vector_id,
    metadata = EXCLUDED.metadata;

-- =========================================================
-- 5. 聊天会话表：4 个真实问题场景
-- =========================================================
INSERT INTO chat_sessions (id, knowledge_base_id, user_id, title, created_at, updated_at)
VALUES
    (501, 201, 104, '年假申请需要提前多久提交', NOW(), NOW()),
    (502, 202, 104, '差旅报销最晚多久内提交', NOW(), NOW()),
    (503, 203, 104, '入职第一天需要带什么材料', NOW(), NOW()),
    (504, 204, 104, '每周远程办公是否需要审批', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
    knowledge_base_id = EXCLUDED.knowledge_base_id,
    user_id = EXCLUDED.user_id,
    title = EXCLUDED.title,
    updated_at = NOW();

-- =========================================================
-- 6. 聊天消息表：每个会话 1 条助手回答，共 4 条
-- =========================================================
INSERT INTO chat_messages (id, session_id, role, content, token_count, created_at)
VALUES
    (
        601,
        501,
        'assistant',
        '根据请假制度，员工申请年假需要至少提前 3 个工作日提交审批；病假 1 天以内可以补提，超过 1 天需要补充医院证明。',
        78,
        NOW()
    ),
    (
        602,
        502,
        'assistant',
        '根据报销制度，差旅报销需要在行程结束后 10 个自然日内提交；如果涉及餐饮发票，还需要附消费明细。',
        74,
        NOW()
    ),
    (
        603,
        503,
        'assistant',
        '根据入职制度，新员工入职当天需要携带身份证、学历证明、银行卡信息和一寸照片，试用期默认是 3 个月。',
        71,
        NOW()
    ),
    (
        604,
        504,
        'assistant',
        '根据远程办公制度，员工每周最多可申请 2 天远程办公，且需要至少提前 1 天提交申请并获得直属主管审批。',
        76,
        NOW()
    )
ON CONFLICT (id) DO UPDATE SET
    session_id = EXCLUDED.session_id,
    role = EXCLUDED.role,
    content = EXCLUDED.content,
    token_count = EXCLUDED.token_count;

-- =========================================================
-- 7. 聊天引用表：每条回答对应 1 条核心引用
-- =========================================================
INSERT INTO chat_references (
    id,
    message_id,
    document_id,
    chunk_id,
    score,
    content_preview,
    page_number,
    created_at
)
VALUES
    (701, 601, 301, 401, 0.97, '员工申请年假需至少提前 3 个工作日提交审批。', 2, NOW()),
    (702, 602, 302, 402, 0.96, '差旅报销需在行程结束后 10 个自然日内提交。', 3, NOW()),
    (703, 603, 303, 403, 0.95, '新员工入职当天需携带身份证、学历证明、银行卡信息。', 1, NOW()),
    (704, 604, 304, 404, 0.98, '员工每周最多可申请 2 天远程办公，并需主管审批。', 4, NOW())
ON CONFLICT (id) DO UPDATE SET
    message_id = EXCLUDED.message_id,
    document_id = EXCLUDED.document_id,
    chunk_id = EXCLUDED.chunk_id,
    score = EXCLUDED.score,
    content_preview = EXCLUDED.content_preview,
    page_number = EXCLUDED.page_number;

-- =========================================================
-- 8. Prompt 模板表：4 种问答风格
-- =========================================================
INSERT INTO prompt_templates (id, name, description, template, is_default, created_at, updated_at)
VALUES
    (801, '默认问答模板', '用于通用制度问答场景。', '你是企业制度助手，请基于提供的知识库内容回答用户问题。', TRUE, NOW(), NOW()),
    (802, '制度解释模板', '适合解释规章条款和审批规则。', '请用清晰、正式的语气解释制度条款，并指出关键限制条件。', FALSE, NOW(), NOW()),
    (803, '简洁回答模板', '适合在前端展示精简回答。', '请在 3 句话内回答，并尽量给出可执行结论。', FALSE, NOW(), NOW()),
    (804, '严谨引用模板', '强调依据来源的问答风格。', '请仅根据引用内容回答，并显式指出答案依据。', FALSE, NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    template = EXCLUDED.template,
    is_default = EXCLUDED.is_default,
    updated_at = NOW();

-- =========================================================
-- 9. 模型配置表：4 个演示配置
-- =========================================================
INSERT INTO model_configs (id, provider, base_url, model_name, model_type, is_active, created_at, updated_at)
VALUES
    (901, 'deepseek', 'https://api.deepseek.com', 'deepseek-chat', 'chat', TRUE, NOW(), NOW()),
    (902, 'openai', 'https://api.openai.com/v1', 'gpt-4o-mini', 'chat', FALSE, NOW(), NOW()),
    (903, 'openai', 'https://api.openai.com/v1', 'text-embedding-3-small', 'embedding', TRUE, NOW(), NOW()),
    (904, 'cohere', 'https://api.cohere.com', 'rerank-v3.5', 'rerank', FALSE, NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
    provider = EXCLUDED.provider,
    base_url = EXCLUDED.base_url,
    model_name = EXCLUDED.model_name,
    model_type = EXCLUDED.model_type,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

-- =========================================================
-- 10. 问答反馈表：4 条反馈
-- =========================================================
INSERT INTO question_feedbacks (id, message_id, rating, comment, created_at)
VALUES
    (1001, 601, 'like', '回答清楚，年假和病假的区别解释得很明确。', NOW()),
    (1002, 602, 'dislike', '希望再补充一下发票丢失时怎么处理。', NOW()),
    (1003, 603, 'like', '入职材料列得很完整，前端展示效果也好。', NOW()),
    (1004, 604, 'dislike', '建议补充未审批直接远程办公的风险提示。', NOW())
ON CONFLICT (id) DO UPDATE SET
    message_id = EXCLUDED.message_id,
    rating = EXCLUDED.rating,
    comment = EXCLUDED.comment;

-- =========================================================
-- 11. 评测用例表：4 道标准题
-- =========================================================
INSERT INTO evaluation_cases (id, knowledge_base_id, question, expected_answer, created_at)
VALUES
    (1101, 201, '年假需要提前多久申请？', '员工申请年假需至少提前 3 个工作日提交审批。', NOW()),
    (1102, 202, '差旅报销最晚多久内提交？', '差旅报销需在行程结束后 10 个自然日内提交。', NOW()),
    (1103, 203, '入职第一天需要准备哪些材料？', '需要携带身份证、学历证明、银行卡信息和一寸照片。', NOW()),
    (1104, 204, '远程办公是否需要主管审批？', '需要至少提前 1 天提交申请，并获得直属主管审批。', NOW())
ON CONFLICT (id) DO UPDATE SET
    knowledge_base_id = EXCLUDED.knowledge_base_id,
    question = EXCLUDED.question,
    expected_answer = EXCLUDED.expected_answer;

-- =========================================================
-- 12. 评测结果表：4 次评测记录
-- =========================================================
INSERT INTO evaluation_runs (id, knowledge_base_id, case_count, avg_score, created_at)
VALUES
    (1201, 201, 1, 0.96, NOW()),
    (1202, 202, 1, 0.89, NOW()),
    (1203, 203, 1, 0.94, NOW()),
    (1204, 204, 1, 0.91, NOW())
ON CONFLICT (id) DO UPDATE SET
    knowledge_base_id = EXCLUDED.knowledge_base_id,
    case_count = EXCLUDED.case_count,
    avg_score = EXCLUDED.avg_score;

-- =========================================================
-- 13. 调整自增序列，避免后续插入撞上手工 ID
-- =========================================================
SELECT setval(pg_get_serial_sequence('users', 'id'), (SELECT GREATEST(COALESCE(MAX(id), 1), 1) FROM users), true);
SELECT setval(pg_get_serial_sequence('knowledge_bases', 'id'), (SELECT GREATEST(COALESCE(MAX(id), 1), 1) FROM knowledge_bases), true);
SELECT setval(pg_get_serial_sequence('documents', 'id'), (SELECT GREATEST(COALESCE(MAX(id), 1), 1) FROM documents), true);
SELECT setval(pg_get_serial_sequence('document_chunks', 'id'), (SELECT GREATEST(COALESCE(MAX(id), 1), 1) FROM document_chunks), true);
SELECT setval(pg_get_serial_sequence('chat_sessions', 'id'), (SELECT GREATEST(COALESCE(MAX(id), 1), 1) FROM chat_sessions), true);
SELECT setval(pg_get_serial_sequence('chat_messages', 'id'), (SELECT GREATEST(COALESCE(MAX(id), 1), 1) FROM chat_messages), true);
SELECT setval(pg_get_serial_sequence('chat_references', 'id'), (SELECT GREATEST(COALESCE(MAX(id), 1), 1) FROM chat_references), true);
SELECT setval(pg_get_serial_sequence('prompt_templates', 'id'), (SELECT GREATEST(COALESCE(MAX(id), 1), 1) FROM prompt_templates), true);
SELECT setval(pg_get_serial_sequence('model_configs', 'id'), (SELECT GREATEST(COALESCE(MAX(id), 1), 1) FROM model_configs), true);
SELECT setval(pg_get_serial_sequence('question_feedbacks', 'id'), (SELECT GREATEST(COALESCE(MAX(id), 1), 1) FROM question_feedbacks), true);
SELECT setval(pg_get_serial_sequence('evaluation_cases', 'id'), (SELECT GREATEST(COALESCE(MAX(id), 1), 1) FROM evaluation_cases), true);
SELECT setval(pg_get_serial_sequence('evaluation_runs', 'id'), (SELECT GREATEST(COALESCE(MAX(id), 1), 1) FROM evaluation_runs), true);

COMMIT;
