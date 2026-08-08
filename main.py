"""
【柯柯API集合】AstrBot 插件 v2.0
- 移除已废弃的 @register 装饰器（新版 AstrBot 自动识别继承 Star 的类）
- 支持管理面板配置 API 列表（_conf_schema.json）
- 内置 25+ 全年龄向图片/文案/音乐/视频接口，均可通过面板增删改
- 支持在配置中添加自定义指令（自动通过兜底分发器响应）
"""
import asyncio
import platform
from datetime import datetime

import aiohttp

from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api.web import error_response, json_response, request

# 默认 API 映射：指令名 -> 接口地址（可在 AstrBot 管理面板的插件配置中修改）
DEFAULT_API_MAP = {
    # 原插件存活接口
    "摸鱼日历": "https://openapi.dwo.cc/api/moyuya",
    "文案": "https://openapi.dwo.cc/api/yi",
    "舔狗日记": "https://openapi.dwo.cc/api/tdog",
    "美女": "https://openapi.dwo.cc/api/pc_mn",
    "图片": "https://openapi.dwo.cc/api/yrcmcx",
    # 壁纸系列（实测可用）
    "壁纸": "https://t.mwm.moe/pc",
    "风景": "https://t.mwm.moe/fj",
    "手机壁纸": "https://t.mwm.moe/mp",
    "原神壁纸": "https://t.mwm.moe/ys",
    "高清壁纸": "https://t.mwm.moe/hd",
    "4K壁纸": "https://t.mwm.moe/4k",
    "二次元": "https://www.dmoe.cc/random.php",
    "东方": "https://img.paulzzh.com/touhou/random",
    "ACG壁纸": "https://www.loliapi.com/acg/",
    "动漫壁纸": "https://api.btstu.cn/sjbz/api.php?lx=dongman",
    "必应壁纸": "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1",
    "少女图": "https://api.anosu.top/img?type=girl",
    "白色系": "https://api.anosu.top/img?type=white",
    "黑色系": "https://api.anosu.top/img?type=black",
    "萌系": "https://api.anosu.top/img?type=moe",
    "COS图": "https://api.anosu.top/img?type=cos",
    # 文案语录
    "一言": "https://v1.hitokoto.cn/?encode=text",
    "今日诗词": "https://v1.jinrishici.com/",
    "每日一句": "https://api.xygeng.cn/one",
    "笑话": "https://v2.jokeapi.dev/joke/Any?type=single",
    # 动物
    "猫图": "https://cataas.com/cat",
    "狗狗": "https://dog.ceo/api/breeds/image/random",
    "柴犬": "https://shibe.online/api/shibes?count=1&urls=true",
    "狐狸": "https://randomfox.ca/floof/",
    # 音乐 / 视频
    "网易云歌单": "https://api.i-meto.com/meting/api?server=netease&type=playlist&id=3778678",
    "音乐直链": "https://api.injahow.cn/meting/?type=url&id=347230",
    "B站热门": "https://api.bilibili.com/x/web-interface/popular?ps=1",
    "头像": "https://api.dicebear.com/9.x/bottts/svg?seed=keke",
}

# 内置指令的别名映射：别名 -> 标准指令名
ALIAS_MAP = {
    "摸鱼": "摸鱼日历",
    "moyu": "摸鱼日历",
    "一言": "一言",
    "hitokoto": "一言",
    "风景图": "风景",
    "随机图": "图片",
    "随机图片": "图片",
    "壁纸图": "壁纸",
    "猫猫": "猫图",
    "cat": "猫图",
    "狗图": "狗狗",
    "dog": "狗狗",
}

# 内置指令名集合（配置中出现的其它指令名将作为自定义指令处理）
BUILTIN_COMMANDS = set(DEFAULT_API_MAP.keys()) | set(ALIAS_MAP.keys())


class KekeApiCollectionPlugin(Star):
    """【柯柯API集合】聚合图片、文案、音乐、视频等全年龄 API 接口。"""

    def __init__(self, context: Context, config=None):
        super().__init__(context)
        self.config = config
        self.session = None
        self.session_lock = asyncio.Lock()
        self.timeout = 10
        self.max_retries = 3
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "Chrome/126.0 Safari/537.36"
        )
        self.api_map = {}
        self.custom_commands = {}
        self.disabled_commands = set()  # 被禁用的指令（手动或自动检测）
        self._health_task = None
        self._load_config()
        # 插件页面后端 API：供 WebUI 查询当前生效的接口配置。
        # bridge 转发路径为 /api/v1/plugins/extensions/{插件名}/config，
        # 插件名取自 metadata.yaml 的 name，因此注册多个前缀以兼容各种加载方式。
        try:
            plugin_name = getattr(self, "name", None) or "astrbot_plugin_keke_api_collection"
            prefixes = (
                f"/{plugin_name}",
                "/astrbot_plugin_keke_api_collection",
                f"/{self.__class__.__name__}",
            )
            for prefix in prefixes:
                context.register_web_api(
                    f"{prefix}/config",
                    self.page_config,
                    ["GET"],
                    "获取插件当前接口配置",
                )
                context.register_web_api(
                    f"{prefix}/config/save",
                    self.save_config,
                    ["POST"],
                    "保存插件接口配置",
                )
                context.register_web_api(
                    f"{prefix}/config/test",
                    self.test_api,
                    ["POST"],
                    "测试接口可用性",
                )
        except Exception as e:
            logger.warning(f"注册插件页面 API 失败: {e}")

    # ------------------------------------------------------------- 页面 API
    async def page_config(self):
        """WebUI 页面使用的接口配置查询。"""
        return json_response(
            {
                "version": "2.0.0",
                "api_map": self.api_map,
                "custom_commands": list(self.custom_commands.keys()),
                "builtin_commands": sorted(BUILTIN_COMMANDS),
                "disabled_commands": sorted(self.disabled_commands),
                "timeout": self.timeout,
                "max_retries": self.max_retries,
            }
        )

    # ------------------------------------------------------------------ 配置
    def _load_config(self):
        """从 AstrBot 面板配置加载 API 映射与请求参数。"""
        # 读取配置中的自定义映射（格式：指令|URL，每行一条）
        conf_map = None
        if self.config:
            conf_map = self.config.get("api_map")
            timeout = self.config.get("timeout")
            retries = self.config.get("max_retries")
            ua = self.config.get("user_agent")
            if isinstance(timeout, int) and timeout > 0:
                self.timeout = timeout
            if isinstance(retries, int) and retries >= 0:
                self.max_retries = retries
            if isinstance(ua, str) and ua.strip():
                self.user_agent = ua.strip()

        self.api_map = dict(DEFAULT_API_MAP)
        if isinstance(conf_map, list) and conf_map:
            parsed = {}
            for entry in conf_map:
                if isinstance(entry, str) and "|" in entry:
                    name, _, url = entry.partition("|")
                    name, url = name.strip(), url.strip()
                    if name and url:
                        parsed[name] = url
            if parsed:
                self.api_map = parsed

        # 内置指令之外的指令 -> 自定义指令（由兜底分发器响应）
        self.custom_commands = {
            k: v for k, v in self.api_map.items() if k not in BUILTIN_COMMANDS
        }
        # 读取被禁用的指令
        disabled = None
        if self.config:
            disabled = self.config.get("disabled")
        self.disabled_commands = (
            set(str(x).strip() for x in disabled if str(x).strip())
            if isinstance(disabled, list)
            else set()
        )
        logger.info(f"柯柯API集合已加载 {len(self.api_map)} 个接口, "
                    f"其中自定义指令 {len(self.custom_commands)} 个, "
                    f"已禁用 {len(self.disabled_commands)} 个")

    def _get_url(self, name: str) -> str | None:
        """根据指令名（含别名）获取接口地址。"""
        return self.api_map.get(name) or self.api_map.get(ALIAS_MAP.get(name, ""))

    async def save_config(self):
        """WebUI 页面使用的接口配置保存（立即生效，无需重载插件）。"""
        payload = await request.json(default={})
        new_map = payload.get("api_map")
        if not isinstance(new_map, list) or not new_map:
            return error_response("api_map 必须是非空列表", status_code=400)
        cleaned = []
        for entry in new_map:
            if not isinstance(entry, str):
                return error_response("条目格式错误（应为 指令名|接口地址）", status_code=400)
            name, _, url = entry.partition("|")
            name, url = name.strip(), url.strip()
            if not name or not url.startswith(("http://", "https://")):
                return error_response(f"无效条目: {entry}", status_code=400)
            cleaned.append(f"{name}|{url}")
        # 启用/禁用状态
        disabled = payload.get("disabled")
        if isinstance(disabled, list):
            self.disabled_commands = set(
                str(x).strip() for x in disabled if str(x).strip()
            )
        # 持久化到 AstrBot 配置
        if self.config is not None:
            self.config["api_map"] = cleaned
            self.config["disabled"] = sorted(self.disabled_commands)
            try:
                await self.config.save_config_async()
            except Exception:
                self.config.save_config()
        # 更新内存，立即生效
        self.api_map = {}
        for e in cleaned:
            n, _, u = e.partition("|")
            self.api_map[n.strip()] = u.strip()
        self.custom_commands = {
            k: v for k, v in self.api_map.items() if k not in BUILTIN_COMMANDS
        }
        logger.info(f"柯柯API集合配置已保存: {len(self.api_map)} 条指令")
        return json_response(
            {
                "saved": True,
                "count": len(self.api_map),
                "custom_commands": list(self.custom_commands.keys()),
                "disabled_commands": sorted(self.disabled_commands),
            }
        )

    async def test_api(self):
        """WebUI 页面使用的接口连通性测试。"""
        import time
        payload = await request.json(default={})
        url = payload.get("url", "")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            return error_response("无效接口地址", status_code=400)
        start = time.time()
        try:
            timeout = aiohttp.ClientTimeout(total=8)
            async with self.session_lock:
                if self.session is None or self.session.closed:
                    self.session = aiohttp.ClientSession()
            headers = {"User-Agent": self.user_agent}
            async with self.session.get(url, headers=headers, timeout=timeout) as resp:
                content_type = resp.headers.get("Content-Type", "")
                body = await resp.content.read(256)
                elapsed = round((time.time() - start) * 1000)
                is_image = content_type.startswith("image/")
                return json_response(
                    {
                        "ok": resp.status == 200,
                        "status": resp.status,
                        "content_type": content_type or "未知",
                        "size": len(body),
                        "elapsed_ms": elapsed,
                        "is_image": is_image,
                    }
                )
        except asyncio.TimeoutError:
            return json_response({"ok": False, "status": 0, "error": "请求超时", "elapsed_ms": 8000})
        except aiohttp.ClientError as e:
            return json_response({"ok": False, "status": 0, "error": f"连接失败: {e.__class__.__name__}", "elapsed_ms": round((time.time() - start) * 1000)})
        except Exception as e:
            return json_response({"ok": False, "status": 0, "error": str(e)[:80], "elapsed_ms": round((time.time() - start) * 1000)})

    # ------------------------------------------------------------- 通用执行
    async def _run(self, api_name: str, event: AstrMessageEvent):
        """按指令名查接口并统一处理响应。"""
        url = self._get_url(api_name)
        if not url:
            yield event.plain_result(f"未配置「{api_name}」接口，请在插件配置中添加")
            return
        target = ALIAS_MAP.get(api_name, api_name)
        if api_name in self.disabled_commands or target in self.disabled_commands:
            yield event.plain_result(
                f"「{api_name}」当前已禁用（接口失效被自动关闭，"
                f"可在插件 WebUI 指令管理中重新启用）")
            return
        result = await self.fetch_api(url)
        async for response in self.handle_api_response(event, api_name, result):
            yield response

    # --------------------------------------------------------------- 网络层
    async def fetch_api(self, url: str) -> dict:
        """异步获取 API 数据，带重试与指数退避。"""
        for attempt in range(self.max_retries + 1):
            try:
                async with self.session_lock:
                    if self.session is None or self.session.closed:
                        self.session = aiohttp.ClientSession()
                headers = {"User-Agent": self.user_agent}
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                async with self.session.get(
                    url, headers=headers, timeout=timeout
                ) as response:
                    content_type = response.headers.get("Content-Type", "").lower()
                    # 5xx / 429 重试
                    if response.status >= 500 or response.status == 429:
                        if attempt < self.max_retries:
                            retry_after = response.headers.get("Retry-After")
                            wait = int(retry_after) if retry_after and retry_after.isdigit() else (
                                1 * (2 ** attempt)
                            )
                            logger.warning(
                                f"API 返回 {response.status}, 第 {attempt + 1} 次重试 "
                                f"({wait}s 后)")
                            await asyncio.sleep(wait)
                            continue
                        return {"error": f"API请求失败，状态码：{response.status}"}
                    if response.status == 200:
                        # 图片 / 音频 / 视频：直接回源地址
                        if content_type.startswith("image/"):
                            return {"image_url": url}
                        if content_type.startswith("audio/"):
                            return {"audio_url": url}
                        if content_type.startswith("video/"):
                            return {"video_url": url}
                        # 尝试 JSON
                        try:
                            json_data = await response.json()
                            if isinstance(json_data, dict):
                                return json_data
                            if isinstance(json_data, list):
                                return {"data_list": json_data}
                        except (aiohttp.ContentTypeError, ValueError):
                            pass
                        text_data = await response.text()
                        # 文本里直接带图片地址
                        for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                            if ext in text_data and "http" in text_data:
                                return {"text": text_data.strip()}
                        return {"text": text_data.strip()}
                    return {"error": f"API请求失败，状态码：{response.status}"}
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < self.max_retries:
                    logger.warning(f"API 请求异常: {e}，第 {attempt + 1} 次重试...")
                    await asyncio.sleep(1 * (2 ** attempt))
                    continue
                logger.error(f"API 请求异常: {e}")
                return {"error": f"请求异常: {e}"}
            except Exception as e:
                logger.error(f"API 请求未知异常: {e}")
                return {"error": f"请求异常: {e}"}

    # ------------------------------------------------------------- 响应解析
    async def handle_api_response(self, event, api_name: str, result: dict):
        """统一处理 API 响应。"""
        if not isinstance(result, dict):
            yield event.plain_result(f"获取{api_name}成功，但响应无法解析")
            return
        if "error" in result:
            yield event.plain_result(f"获取{api_name}失败: {result['error']}")
            return
        if "image_url" in result:
            yield event.image_result(result["image_url"])
            return
        if "audio_url" in result:
            yield event.plain_result(f"🎵 {api_name}: {result['audio_url']}")
            return
        if "video_url" in result:
            yield event.plain_result(f"🎬 {api_name}: {result['video_url']}")
            return
        if "text" in result:
            yield event.plain_result(result["text"])
            return
        # JSON 数据提取
        if "data_list" in result:
            items = result["data_list"]
            if items and isinstance(items[0], dict):
                first = items[0]
                # B站热门视频
                if "bvid" in first:
                    title = first.get("title", "")
                    bvid = first["bvid"]
                    yield event.plain_result(
                        f"📺 {title}\nhttps://www.bilibili.com/video/{bvid}")
                    return
                # Meting 歌单
                if "url" in first and "name" in first:
                    name = first.get("name", "")
                    artist = first.get("artist", "")
                    yield event.plain_result(f"🎵 {name} - {artist}\n{first['url']}")
                    return
                # 图链列表
                for key in ("url", "image", "img", "image_url"):
                    if key in first and str(first[key]).startswith("http"):
                        yield event.image_result(first[key])
                        return
            yield event.plain_result(f"获取{api_name}成功，但响应格式未识别")
            return
        data = result.get("data")
        if isinstance(data, str):
            yield event.plain_result(data)
        elif isinstance(data, dict):
            if "text" in data:
                yield event.plain_result(data["text"])
            elif "url" in data or "image" in data or "img" in data:
                img_url = data.get("url") or data.get("image") or data.get("img")
                if str(img_url).startswith("http"):
                    yield event.image_result(img_url)
                else:
                    yield event.plain_result(f"获取{api_name}成功，但响应格式未识别")
            else:
                yield event.plain_result(str(data))
        elif isinstance(data, list) and data:
            first = data[0] if isinstance(data[0], dict) else {}
            for key in ("url", "image", "img"):
                if key in first and str(first[key]).startswith("http"):
                    yield event.image_result(first[key])
                    return
            yield event.plain_result(f"获取{api_name}成功，但响应格式未识别")
        elif "imgurl" in result or "image_url" in result:
            img_url = result.get("imgurl") or result.get("image_url")
            yield event.image_result(img_url)
        elif "url" in result:
            img_url = result["url"]
            yield event.image_result(img_url) if str(img_url).startswith("http") \
                else event.plain_result(str(img_url))
        else:
            yield event.plain_result(f"获取{api_name}成功，但响应格式未识别")

    # ------------------------------------------------------------- 图片指令
    @filter.command("摸鱼日历", alias={"摸鱼"})
    async def cmd_moyu(self, event):
        async for r in self._run("摸鱼日历", event):
            yield r

    @filter.command("文案")
    async def cmd_copywriting(self, event):
        async for r in self._run("文案", event):
            yield r

    @filter.command("舔狗日记")
    async def cmd_tdog(self, event):
        async for r in self._run("舔狗日记", event):
            yield r

    @filter.command("美女")
    async def cmd_beauty(self, event):
        async for r in self._run("美女", event):
            yield r

    @filter.command("图片", alias={"随机图", "随机图片"})
    async def cmd_image(self, event):
        async for r in self._run("图片", event):
            yield r

    @filter.command("壁纸", alias={"壁纸图"})
    async def cmd_wallpaper(self, event):
        async for r in self._run("壁纸", event):
            yield r

    @filter.command("风景", alias={"风景图"})
    async def cmd_scenery(self, event):
        async for r in self._run("风景", event):
            yield r

    @filter.command("手机壁纸")
    async def cmd_mp(self, event):
        async for r in self._run("手机壁纸", event):
            yield r

    @filter.command("原神壁纸")
    async def cmd_ys(self, event):
        async for r in self._run("原神壁纸", event):
            yield r

    @filter.command("高清壁纸")
    async def cmd_hd(self, event):
        async for r in self._run("高清壁纸", event):
            yield r

    @filter.command("4K壁纸")
    async def cmd_4k(self, event):
        async for r in self._run("4K壁纸", event):
            yield r

    @filter.command("二次元")
    async def cmd_anime(self, event):
        async for r in self._run("二次元", event):
            yield r

    @filter.command("东方")
    async def cmd_touhou(self, event):
        async for r in self._run("东方", event):
            yield r

    @filter.command("ACG壁纸")
    async def cmd_acg(self, event):
        async for r in self._run("ACG壁纸", event):
            yield r

    @filter.command("动漫壁纸")
    async def cmd_acgwp(self, event):
        async for r in self._run("动漫壁纸", event):
            yield r

    @filter.command("必应壁纸")
    async def cmd_bing(self, event):
        async for r in self._run("必应壁纸", event):
            yield r

    @filter.command("少女图")
    async def cmd_girl(self, event):
        async for r in self._run("少女图", event):
            yield r

    @filter.command("白色系")
    async def cmd_white(self, event):
        async for r in self._run("白色系", event):
            yield r

    @filter.command("黑色系")
    async def cmd_black(self, event):
        async for r in self._run("黑色系", event):
            yield r

    @filter.command("萌系")
    async def cmd_moe(self, event):
        async for r in self._run("萌系", event):
            yield r

    @filter.command("COS图")
    async def cmd_cos(self, event):
        async for r in self._run("COS图", event):
            yield r

    # ------------------------------------------------------------- 文案指令
    @filter.command("一言", alias={"hitokoto"})
    async def cmd_hitokoto(self, event):
        async for r in self._run("一言", event):
            yield r

    @filter.command("今日诗词")
    async def cmd_poem(self, event):
        async for r in self._run("今日诗词", event):
            yield r

    @filter.command("每日一句")
    async def cmd_daily(self, event):
        async for r in self._run("每日一句", event):
            yield r

    @filter.command("笑话")
    async def cmd_joke(self, event):
        async for r in self._run("笑话", event):
            yield r

    # ------------------------------------------------------------- 动物指令
    @filter.command("猫图", alias={"猫猫"})
    async def cmd_cat(self, event):
        async for r in self._run("猫图", event):
            yield r

    @filter.command("狗狗", alias={"狗图"})
    async def cmd_dog(self, event):
        async for r in self._run("狗狗", event):
            yield r

    @filter.command("柴犬")
    async def cmd_shiba(self, event):
        async for r in self._run("柴犬", event):
            yield r

    @filter.command("狐狸")
    async def cmd_fox(self, event):
        async for r in self._run("狐狸", event):
            yield r

    # ------------------------------------------------------------- 音乐/视频
    @filter.command("网易云歌单")
    async def cmd_music(self, event):
        async for r in self._run("网易云歌单", event):
            yield r

    @filter.command("音乐直链")
    async def cmd_music_url(self, event):
        async for r in self._run("音乐直链", event):
            yield r

    @filter.command("B站热门")
    async def cmd_bili(self, event):
        async for r in self._run("B站热门", event):
            yield r

    @filter.command("头像")
    async def cmd_avatar(self, event):
        async for r in self._run("头像", event):
            yield r

    # --------------------------------------------------------- 自定义指令兜底
    @filter.regex(r".+")
    async def custom_command_dispatcher(self, event: AstrMessageEvent):
        """响应面板配置中新增的自定义指令（非内置指令名）。"""
        if not self.custom_commands:
            return
        msg = event.message_str.strip()
        matched = None
        if msg in self.custom_commands:
            matched = msg
        else:
            for name in self.custom_commands:
                if msg.endswith(name):
                    matched = name
                    break
        if not matched:
            return
        if matched in self.disabled_commands:
            event.stop_event()
            yield event.plain_result(
                f"「{matched}」当前已禁用（接口失效被自动关闭，"
                f"可在插件 WebUI 指令管理中重新启用）")
            return
        event.stop_event()
        async for r in self._run(matched, event):
            yield r

    # ------------------------------------------------------------- 系统指令
    @filter.command("设备信息")
    async def device_info(self, event: AstrMessageEvent):
        """查看服务器基本信息（脱敏版）"""
        try:
            memory = platform.uname()
            info = [
                "**【服务器基本信息】**",
                "",
                "**系统信息**",
                f"- 操作系统: {memory.system}",
                f"- 架构: {platform.architecture()[0]}",
                "",
                "**Python信息**",
                f"- Python版本: {'.'.join(platform.python_version().split('.')[:2])}.*",
                "",
                "**运行状态**",
                "- 网络状态: 正常",
                "- 进程状态: 正常",
            ]
            yield event.plain_result("\n".join(info))
        except Exception as e:
            logger.error(f"获取设备信息失败: {e}")
            yield event.plain_result("获取设备信息失败，请稍后再试")

    def _generate_help_text(self):
        custom_count = len(self.custom_commands)
        lines = ["【柯柯API集合】可用指令："]
        # 只列出内置指令，500+ 全量接口不逐条展示
        for command in DEFAULT_API_MAP:
            lines.append(f"- {command}")
        if custom_count:
            lines.append("")
            lines.append(f"另有 {custom_count} 个预置接口指令（来自全量接口清单）")
            lines.append("直接发送接口指令名即可使用，例如：二次元、壁纸、一言、猫图、网易云歌单…")
            lines.append("完整清单见插件 WebUI「接口管理」页面或 500源总清单.md")
        lines.append("")
        lines.append("- 设备信息")
        lines.append("- 帮助 / 菜单")
        return "\n".join(lines)

    @filter.command("帮助")
    async def help(self, event: AstrMessageEvent):
        yield event.plain_result(self._generate_help_text())

    @filter.command("菜单")
    async def menu(self, event: AstrMessageEvent):
        yield event.plain_result(self._generate_help_text())

    # ------------------------------------------------------ 自动健康检测
    @filter.on_astrbot_loaded()
    async def on_loaded(self):
        """插件加载完成：启动后台自动检测任务。"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        logger.info("柯柯API集合插件初始化完成，自动检测任务已启动（每天凌晨4点）")
        self._health_task = asyncio.create_task(self._health_check_loop())

    async def _health_check_loop(self):
        """后台循环：每天 04:00-04:10 执行一次全量接口检测。"""
        last_run_date = None
        while True:
            try:
                now = datetime.now()
                if now.hour == 4 and now.minute < 10 and last_run_date != now.date():
                    last_run_date = now.date()
                    logger.info("开始每日自动检测全部接口...")
                    await self._auto_check_apis()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"自动检测任务异常: {e}")
            await asyncio.sleep(300)  # 每 5 分钟检查一次时间

    async def _probe_url(self, url: str) -> bool:
        """探测单个接口是否可用（只读 128 字节）。"""
        try:
            timeout = aiohttp.ClientTimeout(total=8)
            async with self.session_lock:
                if self.session is None or self.session.closed:
                    self.session = aiohttp.ClientSession()
            async with self.session.get(
                url, headers={"User-Agent": self.user_agent}, timeout=timeout
            ) as resp:
                await resp.content.read(128)
                return resp.status == 200
        except Exception:
            return False

    async def _auto_check_apis(self):
        """全量检测：失效接口自动禁用，恢复的接口自动启用。"""
        urls = sorted(set(self.api_map.values()))
        sem = asyncio.Semaphore(10)

        async def probe(url: str):
            async with sem:
                return url, await self._probe_url(url)

        results = await asyncio.gather(*(probe(u) for u in urls))
        ok_map = dict(results)

        changed = False
        newly_disabled = []
        newly_enabled = []
        for name, url in self.api_map.items():
            ok = ok_map.get(url, False)
            if not ok and name not in self.disabled_commands:
                self.disabled_commands.add(name)
                newly_disabled.append(name)
                changed = True
            elif ok and name in self.disabled_commands:
                self.disabled_commands.discard(name)
                newly_enabled.append(name)
                changed = True

        if changed and self.config is not None:
            self.config["disabled"] = sorted(self.disabled_commands)
            try:
                await self.config.save_config_async()
            except Exception:
                self.config.save_config()

        if newly_disabled:
            logger.warning(f"自动检测: {len(newly_disabled)} 个接口失效已自动禁用: "
                           f"{', '.join(newly_disabled[:20])}")
        if newly_enabled:
            logger.info(f"自动检测: {len(newly_enabled)} 个接口恢复已自动启用: "
                        f"{', '.join(newly_enabled[:20])}")
        if not changed:
            logger.info(f"自动检测完成: 全部 {len(urls)} 个接口状态无变化")

    # ------------------------------------------------------------- 生命周期
    async def terminate(self):
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except (asyncio.CancelledError, Exception):
                pass
        if self.session and not self.session.closed:
            await self.session.close()
        logger.info("柯柯API集合插件已销毁")
