"""
认证路由
- 管理员登录 (JWT)
- Google OAuth (空链接回调)
- B站扫码登录
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import jwt
from passlib.hash import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User, AccountCookie, Platform
from config import settings

router = APIRouter()

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


class LoginRequest(BaseModel):
    username: str
    password: str


class GoogleOAuthRequest(BaseModel):
    redirect_url: str  # 用户粘贴的回调 URL


class BiliQRResponse(BaseModel):
    qr_url: str
    qrcode_key: str


# ==================== 管理员登录 ====================

@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar()
    if not user or not bcrypt.verify(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = jwt.encode(
        {"sub": str(user.id), "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)},
        settings.secret_key,
        algorithm=ALGORITHM,
    )
    return {"token": token, "username": user.username}


@router.get("/me")
async def get_me(db: AsyncSession = Depends(get_db)):
    # TODO: 从 token 中提取用户信息
    return {"username": "admin"}


# ==================== Google OAuth ====================

@router.get("/google/url")
async def get_google_oauth_url():
    """生成 Google OAuth 授权 URL"""
    if not settings.google_client_id:
        raise HTTPException(400, "未配置 Google Client ID")

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/youtube.readonly",
        "access_type": "offline",
    }
    import urllib.parse
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return {"url": url}


@router.post("/google/callback")
async def google_callback(req: GoogleOAuthRequest, db: AsyncSession = Depends(get_db)):
    """
    处理用户粘贴的回调 URL，提取 auth code
    """
    import urllib.parse
    import aiohttp

    # 从 URL 提取 code
    parsed = urllib.parse.urlparse(req.redirect_url)
    params = urllib.parse.parse_qs(parsed.query)
    code = params.get("code", [None])[0]

    if not code:
        # 尝试从 fragment 中提取
        params = urllib.parse.parse_qs(parsed.fragment)
        code = params.get("code", [None])[0]

    if not code:
        raise HTTPException(400, "无法从 URL 中提取授权码")

    # 用 code 换取 token
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            }
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise HTTPException(400, f"Google token 交换失败: {text}")
            token_data = await resp.json()

    # 保存 cookie 信息
    cookie = AccountCookie(
        platform=Platform.YOUTUBE,
        account_name="Google Account",
        cookie_data="",  # YouTube cookie 通过 OAuth token 间接使用
        extra_data={
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "expires_in": token_data.get("expires_in"),
        },
        is_valid=True,
    )
    db.add(cookie)
    await db.commit()

    return {"success": True, "message": "Google 账号绑定成功"}


# ==================== B站扫码登录 ====================

@router.get("/bilibili/qrcode")
async def get_bili_qrcode():
    """获取B站登录二维码"""
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
        ) as resp:
            data = await resp.json()

    if data.get("code") != 0:
        raise HTTPException(500, "获取B站二维码失败")

    qr_data = data["data"]
    return {
        "qr_url": qr_data["url"],
        "qrcode_key": qr_data["qrcode_key"],
    }


@router.post("/bilibili/check")
async def check_bili_qrcode(qrcode_key: str, db: AsyncSession = Depends(get_db)):
    """检查B站扫码状态"""
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://passport.bilibili.com/x/passport-login/web/qrcode/poll",
            params={"qrcode_key": qrcode_key},
        ) as resp:
            data = await resp.json()
            # 从响应头获取 cookie
            cookies = resp.cookies

    qr_data = data.get("data", {})
    code = qr_data.get("code", -1)

    if code == 0:
        # 登录成功，保存 cookie
        url = qr_data.get("url", "")
        # 提取 SESSDATA 等 cookie
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)

        cookie_str = "; ".join(f"{k}={v[0]}" for k, v in params.items() if v)

        cookie = AccountCookie(
            platform=Platform.BILIBILI,
            account_name="B站账号",
            cookie_data=cookie_str,
            extra_data=dict(params),
            is_valid=True,
        )
        db.add(cookie)
        await db.commit()

        return {"status": "success", "message": "B站登录成功"}
    elif code == 86038:
        return {"status": "expired", "message": "二维码已过期"}
    elif code == 86090:
        return {"status": "scanned", "message": "已扫码，等待确认"}
    else:
        return {"status": "waiting", "message": "等待扫码"}


# ==================== Cookie 管理 ====================

@router.get("/cookies")
async def list_cookies(db: AsyncSession = Depends(get_db)):
    """获取已保存的账号列表"""
    result = await db.execute(select(AccountCookie))
    cookies = result.scalars().all()
    return [
        {
            "id": c.id,
            "platform": c.platform.value,
            "account_name": c.account_name,
            "is_valid": c.is_valid,
            "created_at": c.created_at.isoformat() if c.created_at else "",
        }
        for c in cookies
    ]


@router.delete("/cookies/{cookie_id}")
async def delete_cookie(cookie_id: int, db: AsyncSession = Depends(get_db)):
    """删除账号"""
    result = await db.execute(select(AccountCookie).where(AccountCookie.id == cookie_id))
    cookie = result.scalar()
    if not cookie:
        raise HTTPException(404, "未找到")
    await db.delete(cookie)
    await db.commit()
    return {"success": True}
