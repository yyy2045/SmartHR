"""
岗位 API - 岗位相关接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/job", tags=["岗位"])


class ExtractTagsRequest(BaseModel):
    """提取标签请求"""
    text: str


@router.post("/extract-tags")
async def extract_tags(request: ExtractTagsRequest):
    """
    从岗位描述文本中使用 LLM 提取技能标签
    """
    from src.services.llm_service import llm_service

    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="文本不能为空")

    system_prompt = """你是一个专业的招聘 HR。从岗位描述文本中提取关键技能标签。
返回格式要求：
- 返回一个 JSON 对象，包含 "tags" 字段，值为技能标签数组
- 技能标签应该简洁、准确，控制在 2-4 个字或 2-5 个英文单词
- 只返回技能相关的标签，不要返回软技能或通用能力描述
- 只返回 JSON 对象，不要添加其他文本

例如输入：
"要求熟悉 Java、Spring Boot、MySQL，有 3 年以上开发经验"
应该返回：
{"tags": ["Java", "Spring Boot", "MySQL"]}"""

    user_prompt = f"请从以下岗位描述中提取关键技能标签：\n\n{request.text[:4000]}"

    try:
        result = llm_service.generate(prompt=user_prompt, system_prompt=system_prompt)

        import json
        text = result.strip()
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1:
            parsed = json.loads(text[start_idx:end_idx+1])
            tags = parsed.get("tags", [])
            return {"tags": tags}

        # Fallback: return empty tags
        return {"tags": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"标签提取失败: {str(e)}")