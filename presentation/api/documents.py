"""文档浏览接口（Document Browsing Handler）。

路由：GET /api/v1/documents/  (文档列表)
路由：GET /api/v1/documents/{video_id}  (文档详情)
路由：DELETE /api/v1/documents/{video_id}/pages/{page}  (删除某分P的文件)
"""

import os

from fastapi import APIRouter, Depends, HTTPException

from domain.exceptions import TaskNotFoundError
from domain.repositories import VideoInfoRepository

from application.use_cases import ListDocumentsUseCase, GetDocumentDetailUseCase
from presentation.dependencies import get_depend_object

router = APIRouter(tags=["documents"])


@router.get("/")
async def list_documents(
    list_uc: ListDocumentsUseCase = Depends(get_depend_object(ListDocumentsUseCase)),
):
    """列出所有视频文档（每个 VideoInfo 为一条）。"""
    return await list_uc.execute()


@router.get("/{video_id}")
async def get_document_detail(
    video_id: str,
    detail_uc: GetDocumentDetailUseCase = Depends(get_depend_object(GetDocumentDetailUseCase)),
):
    """查询某视频的所有分P文本内容。"""
    try:
        return await detail_uc.execute(video_id)
    except TaskNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{video_id}/pages/{page}")
async def delete_page_content(
    video_id: str,
    page: int,
    video_repo: VideoInfoRepository = Depends(get_depend_object(VideoInfoRepository)),
):
    """删除某个分P的所有处理文件（音频、转录、加标点、总结）。"""
    video = await video_repo.find(id=video_id)
    if not video:
        raise HTTPException(status_code=404, detail="视频信息不存在")

    for p in video.pages:
        if p.page == page:
            for attr in ("audio_path", "txt_raw_path", "txt_punctuation_path", "txt_summarize_path"):
                filepath = getattr(p, attr)
                if filepath:
                    try:
                        os.remove(filepath)
                    except OSError:
                        pass
                setattr(p, attr, None)
            await video_repo.save(video)
            return {"status": "ok"}

    raise HTTPException(status_code=404, detail="分P不存在")
