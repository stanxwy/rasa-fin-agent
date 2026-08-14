from fastapi import (
    APIRouter,
    Request,
)

router = APIRouter(tags=["health"])

@router.get("/health")
async def health(request: Request):
    print(request.app.state.key)
    return {"ok": True}