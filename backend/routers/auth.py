"""
认证路由
- 管理员登录 (JWT)
- YouTube cookies.txt 导入
- B站扫码登录
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import jwt
import bcrypt as bc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import os

from database import get_db
from models import User, AccountCookie, Platform
from config import settings

router = APIRouter()

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 72


class LoginRequest(BaseModel):
    username: str
    password: str


class CookieTextRequest(BaseModel):
    cookie_text: str
    platform: str = "youtube"  # youtube / bilibili


# ==================== 管理员登录 ====================

@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar()
    if not user or not bc.checkpw(req.password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = jwt.encode(
        {"sub": str(user.id), "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)},
        settings.secret_key,
        algorithm=ALGORITHM,
    )
    return {"token": token, "username": user.username}


@router.get("/me")
async def get_me():
    return {"username": "admin"}


# ==================== YouTube Cookies 导入 ====================

@router.post("/youtube/cookies")
async def import_youtube_cookies(req: CookieTextRequest, db: AsyncSession = Depends(get_db)):
    """
    导入 YouTube cookies.txt 内容
    用户从浏览器导出 Netscape 格式的 cookies.txt，粘贴文本
    """
    cookie_text = req.cookie_text.strip()
    if not cookie_text:
        raise HTTPException(400, "Cookie 内容不能为空")

    # 验证格式（Netscape cookies.txt 格式）
    lines = [l for l in cookie_text.split("\n") if l.strip() and not l.startswith("#")]
    if not lines:
        raise HTTPException(400, "无效的 cookies.txt 格式")

    # 保存到文件
    cookies_dir = "/data/cookies"
    os.makedirs(cookies_dir, exist_ok=True)
    cookies_path = os.path.join(cookies_dir, "youtube_cookies.txt")
    with open(cookies_path, "w") as f:
        f.write(cookie_text)

    # 更新 settings
    settings.youtube_cookies_file = cookies_path
    settings.save_to_file()

    # 保存到数据库
    cookie = AccountCookie(
        platform=Platform.YOUTUBE,
        account_name="YouTube (cookies.txt)",
        cookie_data=cookie_text[:500],  # 只存摘要
        extra_data={"cookies_file": cookies_path, "lines": len(lines)},
        is_valid=True,
    )
    db.add(cookie)
    await db.commit()

    return {"success": True, "message": f"YouTube cookies 已导入（{len(lines)} 条）"}


@router.post("/youtube/cookies/upload")
async def upload_youtube_cookies(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """上传 cookies.txt 文件"""
    content = await file.read()
    cookie_text = content.decode("utf-8", errors="ignore")

    # 保存到文件
    cookies_dir = "/data/cookies"
    os.makedirs(cookies_dir, exist_ok=True)
    cookies_path = os.path.join(cookies_dir, "youtube_cookies.txt")
    with open(cookies_path, "w") as f:
        f.write(cookie_text)

    settings.youtube_cookies_file = cookies_path
    settings.save_to_file()

    lines = [l for l in cookie_text.split("\n") if l.strip() and not l.startswith("#")]

    cookie = AccountCookie(
        platform=Platform.YOUTUBE,
        account_name="YouTube (cookies.txt)",
        cookie_data=f"文件上传: {file.filename}",
        extra_data={"cookies_file": cookies_path, "lines": len(lines)},
        is_valid=True,
    )
    db.add(cookie)
    await db.commit()

    return {"success": True, "message": f"YouTube cookies 文件已上传（{len(lines)} 条）"}


# ==================== B站扫码登录 ====================

@router.get("/bilibili/qrcode")
async def get_bili_qrcode():
    """获取B站登录二维码"""
    import aiohttp

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
    }

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(
                "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
            ) as resp:
                data = await resp.json(content_type=None)
    except Exception as e:
        raise HTTPException(500, f"请求B站API失败: {str(e)}")

    if data.get("code") != 0:
        raise HTTPException(500, f"获取B站二维码失败: {data}")

    qr_data = data["data"]
    return {
        "qr_url": qr_data["url"],
        "qrcode_key": qr_data["qrcode_key"],
    }


@router.post("/bilibili/check")
async def check_bili_qrcode(qrcode_key: str, db: AsyncSession = Depends(get_db)):
    """检查B站扫码状态"""
    import aiohttp

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(
            "https://passport.bilibili.com/x/passport-login/web/qrcode/poll",
            params={"qrcode_key": qrcode_key},
        ) as resp:
            data = await resp.json(content_type=None)

    qr_data = data.get("data", {})
    code = qr_data.get("code", -1)

    if code == 0:
        # 登录成功
        url = qr_data.get("url", "")
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        cookie_str = "; ".join(f"{k}={v[0]}" for k, v in params.items() if v)

        # 保存 cookies 文件（Netscape 格式）
        cookies_dir = "/data/cookies"
        os.makedirs(cookies_dir, exist_ok=True)
        cookies_path = os.path.join(cookies_dir, "bilibili_cookies.txt")

        # 写 Netscape cookies.txt 格式
        with open(cookies_path, "w") as f:
            f.write("# Netscape HTTP Cookie File\n")
            for k, v in params.items():
                if v:
                    f.write(f".bilibili.com\tTRUE\t/\tFALSE\t0\t{k}\t{v[0]}\n")

        settings.bilibili_cookies_file = cookies_path
        settings.save_to_file()

        cookie = AccountCookie(
            platform=Platform.BILIBILI,
            account_name="B站账号",
            cookie_data=cookie_str[:500],
            extra_data={"cookies_file": cookies_path},
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


# ==================== B站 Cookies 导入 ====================

@router.post("/bilibili/cookies")
async def import_bilibili_cookies(req: CookieTextRequest, db: AsyncSession = Depends(get_db)):
    """直接粘贴 B站 cookies.txt"""
    cookie_text = req.cookie_text.strip()
    if not cookie_text:
        raise HTTPException(400, "Cookie 内容不能为空")

    cookies_dir = "/data/cookies"
    os.makedirs(cookies_dir, exist_ok=True)
    cookies_path = os.path.join(cookies_dir, "bilibili_cookies.txt")
    with open(cookies_path, "w") as f:
        f.write(cookie_text)

    settings.bilibili_cookies_file = cookies_path
    settings.save_to_file()

    lines = [l for l in cookie_text.split("\n") if l.strip() and not l.startswith("#")]

    cookie = AccountCookie(
        platform=Platform.BILIBILI,
        account_name="B站 (cookies.txt)",
        cookie_data=cookie_text[:500],
        extra_data={"cookies_file": cookies_path, "lines": len(lines)},
        is_valid=True,
    )
    db.add(cookie)
    await db.commit()

    return {"success": True, "message": f"B站 cookies 已导入（{len(lines)} 条）"}


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
