from fastapi import Header, HTTPException

from config import settings


async def verify_webhook_secret(
    x_webhook_secret: str = Header(...),
) -> None:
    if x_webhook_secret != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
