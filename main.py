from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import aiohttp
import json
import base64

@register("keke_api_collection", "落梦陳", "【柯柯API集合】包含多种图片和文案API，支持摸鱼日历、文案、舔狗日记、美女、图片、白丝、黑丝、美腿、R18、色图", "1.1.1")
class KekeApiCollectionPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # Base64编码的API映射关系
        self.encoded_api_map = {
            "摸鱼日历": "aHR0cHM6Ly9vcGVuYXBpLmR3by5jYy9hcGkvbW95dXlh",
            "文案": "aHR0cHM6Ly9vcGVuYXBpLmR3by5jYy9hcGkveWk=",
            "舔狗日记": "aHR0cHM6Ly9vcGVuYXBpLmR3by5jYy9hcGkvdGRvZw==",
            "美女": "aHR0cHM6Ly9vcGVuYXBpLmR3by5jYy9hcGkvcGMtbW4=",
            "图片": "aHR0cHM6Ly9vcGVuYXBpLmR3by5jYy9hcGkveXJjbWN4",
            "白丝": "aHR0cHM6Ly9hcGkucGxkZHVjay5jb20vYXBpL2JhaXNp",
            "黑丝": "aHR0cHM6Ly9hcGkucGxkZHVjay5jb20vYXBpL2hlaXNp",
            "美腿": "aHR0cHM6Ly9zYnR4cXEuY29tL2FwaS90dWkucGhw",
            "R18": "aHR0cHM6Ly9yYW5kLXIxOC5tb3NzaWEudG9w",
            "色图": "aHR0cHM6Ly9yYW5kLXgubW9zc2lhLnRvcA=="
        }
        # 解码后的API映射
        self.api_map = {}
        for key, encoded_url in self.encoded_api_map.items():
            try:
                decoded_url = base64.b64decode(encoded_url).decode('utf-8')
                self.api_map[key] = decoded_url
            except Exception as e:
                logger.error(f"解码API地址失败: {e}")
                self.api_map[key] = ""

    async def initialize(self):
        """插件初始化方法"""
        logger.info("柯柯API集合插件初始化完成")

    async def fetch_api(self, url):
        """异步获取API数据"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        # 尝试解析JSON响应
                        try:
                            return await response.json()
                        except:
                            # 如果不是JSON，返回文本或二进制数据
                            content_type = response.headers.get('Content-Type', '')
                            if 'image' in content_type:
                                # 对于图片，返回图片URL
                                return {"image_url": url}
                            else:
                                return {"text": await response.text()}
                    else:
                        return {"error": f"API请求失败，状态码：{response.status}"}
        except Exception as e:
            logger.error(f"API请求异常: {e}")
            return {"error": f"请求异常: {str(e)}"}

    async def handle_api_request(self, event: AstrMessageEvent, api_name):
        """处理API请求"""
        url = self.api_map.get(api_name)
        if not url:
            yield event.plain_result(f"未找到API: {api_name}")
            return

        # 获取API数据
        result = await self.fetch_api(url)

        # 处理响应
        if "error" in result:
            yield event.plain_result(f"获取{api_name}失败: {result['error']}")
        elif "image_url" in result:
            # 发送图片
            try:
                yield event.image_result(result["image_url"])
            except Exception as e:
                logger.error(f"发送图片失败: {e}")
                yield event.plain_result(f"获取{api_name}成功，但发送图片失败")
        elif "text" in result:
            # 发送文本
            yield event.plain_result(result["text"])
        elif isinstance(result, dict):
            # 处理JSON响应
            # 尝试提取有用信息
            if "data" in result:
                data = result["data"]
                if isinstance(data, str):
                    yield event.plain_result(data)
                elif isinstance(data, dict):
                    # 尝试提取文本或图片
                    if "text" in data:
                        yield event.plain_result(data["text"])
                    elif "image" in data or "img" in data:
                        img_url = data.get("image") or data.get("img")
                        try:
                            yield event.image_result(img_url)
                        except Exception as e:
                            logger.error(f"发送图片失败: {e}")
                            yield event.plain_result(f"获取{api_name}成功，但发送图片失败")
                    else:
                        # 转换为字符串发送
                        yield event.plain_result(str(data))
                else:
                    yield event.plain_result(str(result))
            else:
                # 转换为字符串发送
                yield event.plain_result(str(result))
        else:
            # 其他情况
            yield event.plain_result(str(result))

    # 注册指令
    @filter.command("摸鱼日历")
    async def moyu_calendar(self, event: AstrMessageEvent):
        """获取摸鱼日历"""
        async for result in self.handle_api_request(event, "摸鱼日历"):
            yield result

    @filter.command("文案")
    async def get_copywriting(self, event: AstrMessageEvent):
        """获取文案"""
        async for result in self.handle_api_request(event, "文案"):
            yield result

    @filter.command("舔狗日记")
    async def get_tdog(self, event: AstrMessageEvent):
        """获取舔狗日记"""
        async for result in self.handle_api_request(event, "舔狗日记"):
            yield result

    @filter.command("美女")
    async def get_beauty(self, event: AstrMessageEvent):
        """获取美女图片"""
        async for result in self.handle_api_request(event, "美女"):
            yield result

    @filter.command("图片")
    async def get_image(self, event: AstrMessageEvent):
        """获取随机图片"""
        async for result in self.handle_api_request(event, "图片"):
            yield result

    @filter.command("白丝")
    async def get_baisi(self, event: AstrMessageEvent):
        """获取白丝图片"""
        async for result in self.handle_api_request(event, "白丝"):
            yield result

    @filter.command("黑丝")
    async def get_heisi(self, event: AstrMessageEvent):
        """获取黑丝图片"""
        async for result in self.handle_api_request(event, "黑丝"):
            yield result

    @filter.command("美腿")
    async def get_meitui(self, event: AstrMessageEvent):
        """获取美腿图片"""
        async for result in self.handle_api_request(event, "美腿"):
            yield result

    @filter.command("R18")
    async def get_r18(self, event: AstrMessageEvent):
        """获取R18图片"""
        async for result in self.handle_api_request(event, "R18"):
            yield result

    @filter.command("色图")
    async def get_setu(self, event: AstrMessageEvent):
        """获取色图"""
        async for result in self.handle_api_request(event, "色图"):
            yield result

    @filter.command("帮助")
    async def help(self, event: AstrMessageEvent):
        """查看所有可用指令"""
        help_message = "【柯柯API集合】可用指令：\n"
        for command in self.api_map.keys():
            help_message += f"- {command}\n"
        help_message += "\n发送以上指令即可调用对应API获取内容"
        yield event.plain_result(help_message)

    @filter.command("菜单")
    async def menu(self, event: AstrMessageEvent):
        """查看所有可用指令"""
        # 复用help方法的逻辑
        help_message = "【柯柯API集合】可用指令：\n"
        for command in self.api_map.keys():
            help_message += f"- {command}\n"
        help_message += "\n发送以上指令即可调用对应API获取内容"
        yield event.plain_result(help_message)

    async def terminate(self):
        """插件销毁方法"""
        logger.info("柯柯API集合插件已销毁")
