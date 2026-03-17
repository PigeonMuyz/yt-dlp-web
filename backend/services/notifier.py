"""
通知推送服务 — 支持 Telegram / Bark / Webhook
"""
import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)


async def send_notification(title: str, body: str = "", url: str = ""):
    """发送通知"""
    notify_type = getattr(settings, "notify_type", "")
    if not notify_type:
        return

    try:
        if notify_type == "telegram":
            await _send_telegram(title, body)
        elif notify_type == "bark":
            await _send_bark(title, body, url)
        elif notify_type == "webhook":
            await _send_webhook(title, body, url)
    except Exception as e:
        logger.warning(f"通知发送失败: {e}")


async def _send_telegram(title: str, body: str):
    """Telegram Bot 推送"""
    token = settings.notify_token
    if not token or ":" not in token:
        return
    # token 格式: bot_token:chat_id（用冒号分隔前面是 bot token，最后一段是 chat_id）
    # 或者用户在 notify_webhook_url 填 chat_id
    parts = token.rsplit("@", 1)
    bot_token = parts[0]
    chat_id = parts[1] if len(parts) > 1 else settings.notify_webhook_url

    if not chat_id:
        return

    text = f"*{title}*\n{body}" if body else f"*{title}*"
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        )


async def _send_bark(title: str, body: str, url: str = ""):
    """Bark 推送 (iOS)"""
    key = settings.notify_token
    if not key:
        return

    bark_url = settings.notify_webhook_url or "https://api.day.app"
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"{bark_url}/{key}",
            json={"title": title, "body": body or title, "url": url},
        )


async def _send_webhook(title: str, body: str, url: str = ""):
    """通用 Webhook 推送"""
    webhook_url = settings.notify_webhook_url
    if not webhook_url:
        return

    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            webhook_url,
            json={"title": title, "body": body, "url": url},
        )


# 快捷方法
async def notify_download_complete(title: str, codec: str = "", size_mb: float = 0):
    body = f"编码: {codec}" if codec else ""
    if size_mb > 0:
        body += f" · {size_mb:.1f} MB"
    await send_notification(f"✅ 下载完成: {title}", body)


async def notify_download_failed(title: str, error: str = ""):
    await send_notification(f"❌ 下载失败: {title}", error[:200])


async def notify_subscription_new(sub_name: str, count: int):
    await send_notification(f"📢 {sub_name}", f"发现 {count} 个新视频")
