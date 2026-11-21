"""File Storing Service: принимает и отдаёт сдачи и их файлы. Ничего не анализирует."""

from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from .repository import Submission, SubmissionRepository
from .settings import Settings

# id задания — часть URL сводки, поэтому только буквы, цифры, «_», «.» и «-».
ASSIGNMENT_ID_PATTERN = r"^[\w.-]{1,50}$"


def create_app(settings: Settings) -> FastAPI:
    repository = SubmissionRepository(settings.data_dir)
    app = FastAPI(
        title="ВышBuild · File Storing Service",
        description="Хранение сдач (кто, когда, по какому заданию) и их файлов.",
        version="1.0.0",
    )

    def find(submission_id: str) -> Submission:
        submission = repository.get(submission_id)
        if submission is None:
            raise HTTPException(404, f"Сдача {submission_id} не найдена")
        return submission

    @app.get("/health", tags=["service"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/submissions", status_code=201, tags=["submissions"])
    def upload(
        student: Annotated[str, Form(min_length=1, max_length=100)],
        assignment_id: Annotated[str, Form(pattern=ASSIGNMENT_ID_PATTERN)],
        file: Annotated[UploadFile, File()],
    ) -> Submission:
        student = student.strip()
        if not student:
            raise HTTPException(422, "Укажите студента")
        content = file.file.read(settings.max_file_bytes + 1)
        if len(content) > settings.max_file_bytes:
            raise HTTPException(413, f"Файл больше {settings.max_file_bytes // 2**20} МБ")
        return repository.add(
            student=student,
            assignment_id=assignment_id,
            filename=file.filename or "upload",
            content=content,
        )

    @app.get("/submissions", tags=["submissions"])
    def list_submissions(assignment_id: str) -> list[Submission]:
        return repository.list_by_assignment(assignment_id)

    @app.get("/submissions/{submission_id}", tags=["submissions"])
    def get_submission(submission_id: str) -> Submission:
        return find(submission_id)

    @app.get("/submissions/{submission_id}/file", tags=["submissions"])
    def download(submission_id: str) -> FileResponse:
        submission = find(submission_id)
        return FileResponse(repository.file_path(submission_id), filename=submission.filename)

    return app
