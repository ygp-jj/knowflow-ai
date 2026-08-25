-- KnowFlow AI 演示数据脚本（单演示账号版）
-- 用途：
-- 1. 仅保留演示账号 hr_admin（id=101，密码 demo123456）
-- 2. 清理其余种子用户及其知识库/文档/会话等关联数据
-- 3. 写入归属 hr_admin 的请假库、远程办公库演示数据
--
-- 注意：
-- 1. 这份脚本假设表已经存在
-- 2. 再次执行时会清理多余用户并 upsert 演示数据

BEGIN;

-- =========================================================
-- 0. 清理多余演示用户（CASCADE 会带走其知识库/文档/会话等）
-- =========================================================
DELETE FROM users WHERE id IN (102, 103, 104);
DELETE FROM users WHERE username IN ('finance_admin', 'ops_admin', 'employee_demo');
-- 清理历史上归属其他用户、现已无主的演示知识库（若仍存在）
DELETE FROM knowledge_bases WHERE id IN (202, 203);

-- =========================================================
-- 1. 用户表：仅 1 个演示账号
-- =========================================================
INSERT INTO users (id, username, email, hashed_password, created_at, updated_at)
VALUES
    -- 演示密码 demo123456（bcrypt）
    (101, 'hr_admin', 'hr_admin@knowflow.ai', '$2b$12$jLRQnn2kAn3atfpId52Xsuxk58qSlsblfVt4mDxlwZEFHTyNbYP..', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
    username = EXCLUDED.username,
    email = EXCLUDED.email,
    hashed_password = EXCLUDED.hashed_password,
    updated_at = NOW();

-- =========================================================
-- 2. 知识库表：归属 hr_admin 的 2 个制度库
-- =========================================================
INSERT INTO knowledge_bases (id, name, description, owner_id, created_at, updated_at)
VALUES
    (201, '员工请假制度库', '用于回答年假、病假、事假和请假流程相关问题。', 101, NOW(), NOW()),
    (204, '远程办公制度库', '用于回答远程办公申请、审批和考勤要求相关问题。', 101, NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    owner_id = EXCLUDED.owner_id,
    updated_at = NOW();

-- =========================================================
-- 3. 文档表
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
-- 4. 文档切片表
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
-- 5. 聊天会话表（归属 hr_admin）
-- =========================================================
INSERT INTO chat_sessions (id, knowledge_base_id, user_id, title, created_at, updated_at)
VALUES
    (501, 201, 101, '年假申请需要提前多久提交', NOW(), NOW()),
    (504, 204, 101, '每周远程办公是否需要审批', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
    knowledge_base_id = EXCLUDED.knowledge_base_id,
    user_id = EXCLUDED.user_id,
    title = EXCLUDED.title,
    updated_at = NOW();

-- =========================================================
-- 6. 聊天消息表
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
-- 7. 聊天引用表
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
    (704, 604, 304, 404, 0.98, '员工每周最多可申请 2 天远程办公，并需主管审批。', 4, NOW())
ON CONFLICT (id) DO UPDATE SET
    message_id = EXCLUDED.message_id,
    document_id = EXCLUDED.document_id,
    chunk_id = EXCLUDED.chunk_id,
    score = EXCLUDED.score,
    content_preview = EXCLUDED.content_preview,
    page_number = EXCLUDED.page_number;

-- =========================================================
-- 8. Prompt 模板表
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
-- 9. 模型配置表
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
-- 10. 问答反馈表
-- =========================================================
INSERT INTO question_feedbacks (id, message_id, rating, comment, created_at)
VALUES
    (1001, 601, 'like', '回答清楚，年假和病假的区别解释得很明确。', NOW()),
    (1004, 604, 'dislike', '建议补充未审批直接远程办公的风险提示。', NOW())
ON CONFLICT (id) DO UPDATE SET
    message_id = EXCLUDED.message_id,
    rating = EXCLUDED.rating,
    comment = EXCLUDED.comment;

-- =========================================================
-- 11. 评测用例表
-- =========================================================
INSERT INTO evaluation_cases (id, knowledge_base_id, question, expected_answer, created_at)
VALUES
    (1101, 201, '年假需要提前多久申请？', '员工申请年假需至少提前 3 个工作日提交审批。', NOW()),
    (1104, 204, '远程办公是否需要主管审批？', '需要至少提前 1 天提交申请，并获得直属主管审批。', NOW())
ON CONFLICT (id) DO UPDATE SET
    knowledge_base_id = EXCLUDED.knowledge_base_id,
    question = EXCLUDED.question,
    expected_answer = EXCLUDED.expected_answer;

-- =========================================================
-- 12. 评测结果表
-- =========================================================
INSERT INTO evaluation_runs (id, knowledge_base_id, case_count, avg_score, created_at)
VALUES
    (1201, 201, 1, 0.96, NOW()),
    (1204, 204, 1, 0.91, NOW())
ON CONFLICT (id) DO UPDATE SET
    knowledge_base_id = EXCLUDED.knowledge_base_id,
    case_count = EXCLUDED.case_count,
    avg_score = EXCLUDED.avg_score;

-- =========================================================
-- 13. 清理已删除知识库遗留的评测/反馈孤立行（若有）
-- =========================================================
DELETE FROM evaluation_cases WHERE knowledge_base_id IN (202, 203);
DELETE FROM evaluation_runs WHERE knowledge_base_id IN (202, 203);
DELETE FROM documents WHERE id IN (302, 303);
DELETE FROM document_chunks WHERE id IN (402, 403);
DELETE FROM chat_sessions WHERE id IN (502, 503);
DELETE FROM chat_messages WHERE id IN (602, 603);
DELETE FROM chat_references WHERE id IN (702, 703);
DELETE FROM question_feedbacks WHERE id IN (1002, 1003);

-- =========================================================
-- 14. 调整自增序列
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
