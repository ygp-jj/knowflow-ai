"""Token 估算服务。

第 3 阶段 MVP 使用字符长度近似 token_count，避免引入额外模型依赖。
第 4 阶段如需精确计数可切换为 tiktoken。
"""


def estimate_token_count(text: str) -> int:
    """估算文本 token 数量。

    参数:
        text: 切片正文。

    返回:
        非负整数，空文本返回 0。
    """

    if not text:
        return 0
    return len(text)
