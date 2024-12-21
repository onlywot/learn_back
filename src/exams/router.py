import uuid
from typing import List

from fastapi import APIRouter, Depends, Query

from src.exams.dependencies import get_exam_service
from src.exams.schemas import ExamAnswerResponseSchema, ExamSchema
from src.exams.service import ExamService

router = APIRouter(
    prefix="/exam",
    tags=["exam"]
)


@router.get("/exam", response_model=ExamSchema)
async def start_exam(
        telegram_id: int,
        exam_service: ExamService = Depends(get_exam_service)
):
    return await exam_service.start_exam(telegram_id)


@router.get("/check-exam-sentence-answer", response_model=ExamAnswerResponseSchema)
async def check_exam_sentence_answer(
        sentence_id: uuid.UUID,
        telegram_id: int,
        user_words: List[str] = Query(...),
        exam_service: ExamService = Depends(get_exam_service)
):
    return await exam_service.check_exam_sentence_answer(sentence_id, telegram_id, user_words)


@router.get("/check-exam-answer", response_model=ExamAnswerResponseSchema)
async def check_exam_answer(
        word_for_translate_id: uuid.UUID,
        user_word_id: uuid.UUID,
        telegram_id: int,
        exam_service: ExamService = Depends(get_exam_service)
):
    return await exam_service.check_exam_answer(word_for_translate_id, user_word_id, telegram_id)
