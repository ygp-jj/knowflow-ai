/**
 * 功能：封装智能问答相关接口。
 */
import httpClient from './http';
import { unwrapApiResponse } from '@/utils/api';

/**
 * 对知识库发起单次问答。
 * @param {{ knowledgeBaseId: number, question: string }} payload 请求参数。
 * @returns {Promise<{ answer: string, question: string, knowledge_base_id: number, references: any[] }>}
 */
export async function askQuestion(payload) {
  /** 问答响应对象。 */
  const response = await httpClient.post('/chat/ask', {
    knowledge_base_id: payload.knowledgeBaseId,
    question: payload.question,
  });

  return unwrapApiResponse(response.data);
}
