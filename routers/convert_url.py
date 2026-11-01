from fastapi import APIRouter
from pydantic import BaseModel

from utils.parse_kleinanzeigen_url import (
    map_to_inserate_params,
    parse_kleinanzeigen_url,
)

router = APIRouter()


class ConvertUrlRequest(BaseModel):
    url: str


@router.post("/convert-url")
async def convert_url(request: ConvertUrlRequest):
    parsed = parse_kleinanzeigen_url(request.url)
    inserate_params, unmapped = map_to_inserate_params(parsed)
    return {"inserate_params": inserate_params, "unmapped": unmapped}
