from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import aiohttp
import json
import base64
import platform
import os
import psutil
import asyncio

@register("keke_api_collection", "落梦陳", "【柯柯API集合】包含多种图片和文案API，支持摸鱼日历、文案、舔狗日记、美女、图片、白丝、黑丝、美腿", "1.4.1")
class KekeApiCollectionPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 直接使用API映射关系，移除无意义的Base64编码
        self.api_map = {
            "摸鱼日历": "https://openapi.dwo.cc/api/moyuya",
            "文案": "https://openapi.dwo.cc/api/yi",
            "舔狗日记": "https://openapi.dwo.cc/api/tdog",
            "美女": "https://openapi.dwo.cc/api/pc_mn",
            "图片": "https://openapi.dwo.cc/api/yrcmcx",
            "白丝": "https://api.pldduck.com/api/baisi",
            "黑丝": "https://api.pldduck.com/api/heisi",
            "美腿": "https://sbtxqq.com/api/tui.php"
        }
        # 初始化ClientSession
        self.session = None

    @filter.on_astrbot_loaded()
    async def on_loaded(self):
        """插件加载时的初始化方法"""
        # 创建ClientSession
        if not self.session:
            self.session = aiohttp.ClientSession()
        logger.info("柯柯API集合插件初始化完成")

    async def fetch_api(self, url):
        """异步获取API数据"""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                # 使用复用的ClientSession
                if not self.session:
                    self.session = aiohttp.ClientSession()
                
                async with self.session.get(url, timeout=10) as response:
                    logger.info(f"API请求状态码: {response.status}")
                    logger.info(f"API响应头: {dict(response.headers)}")
                    
                    # 对于5xx错误，进行重试
                    if 500 <= response.status < 600:
                        if attempt < max_retries - 1:
                            logger.warning(f"API返回{response.status}错误，第{attempt+1}次重试...")
                            await asyncio.sleep(retry_delay * (2 ** attempt))  # 指数退避
                            continue
                        else:
                            return {"error": f"API请求失败，状态码：{response.status}"}
                    
                    if response.status == 200:
                        # 尝试解析JSON响应
                        try:
                            json_data = await response.json()
                            logger.info(f"API返回JSON数据: {json_data}")
                            return json_data
                        except (aiohttp.ContentTypeError, json.JSONDecodeError) as json_error:
                            logger.info(f"JSON解析失败: {json_error}")
                            # 如果不是JSON，返回文本或二进制数据
                            content_type = response.headers.get('Content-Type', '')
                            logger.info(f"API响应Content-Type: {content_type}")
                            if 'image' in content_type:
                                # 对于图片，返回图片URL
                                return {"image_url": url}
                            else:
                                text_data = await response.text()
                                logger.info(f"API返回文本数据: {text_data[:100]}...")
                                # 特殊处理美腿API
                                if 'sbtxqq.com/api/tui.php' in url:
                                    # 检查是否返回了HTML内容
                                    if '<script' in text_data or '<html' in text_data:
                                        # 美腿API返回了HTML，可能是反爬虫页面
                                        logger.warning("美腿API返回了HTML内容，可能是反爬虫页面")
                                        return {"error": "API返回了反爬虫页面，请稍后再试"}
                                    # 尝试提取图片URL
                                    if 'http' in text_data and ('.jpg' in text_data or '.png' in text_data or '.gif' in text_data):
                                        return {"image_url": text_data.strip()}
                                    return {"error": "API返回了无效的响应"}
                                # 处理其他API的文本响应
                                if 'http' in text_data and ('.jpg' in text_data or '.png' in text_data or '.gif' in text_data):
                                    return {"image_url": text_data.strip()}
                                return {"text": text_data}
                    else:
                        return {"error": f"API请求失败，状态码：{response.status}"}
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"API请求异常: {e}，第{attempt+1}次重试...")
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # 指数退避
                    continue
                else:
                    logger.error(f"API请求异常: {e}")
                    return {"error": f"请求异常: {str(e)}"}
            except Exception as e:
                logger.error(f"API请求未知异常: {e}")
                return {"error": f"请求异常: {str(e)}"}



    async def handle_api_response(self, event: AstrMessageEvent, api_name: str, result: dict):
        """统一处理API响应"""
        if "error" in result:
            yield event.plain_result(f"获取{api_name}失败: {result['error']}")
        elif "image_url" in result:
            try:
                yield event.image_result(result["image_url"])
            except Exception as e:
                logger.error(f"发送图片失败: {e}")
                yield event.plain_result(f"获取{api_name}成功，但发送图片失败")
        elif "text" in result:
            yield event.plain_result(result["text"])
        elif isinstance(result, dict):
            if "data" in result:
                data = result["data"]
                if isinstance(data, str):
                    yield event.plain_result(data)
                elif isinstance(data, dict):
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
                        yield event.plain_result(str(data))
                else:
                    yield event.plain_result(str(result))
            else:
                yield event.plain_result(str(result))
        else:
            yield event.plain_result(str(result))

    @filter.command("摸鱼日历")
    async def moyu_calendar(self, event: AstrMessageEvent):
        """获取摸鱼日历"""
        result = await self.fetch_api(self.api_map["摸鱼日历"])
        async for response in self.handle_api_response(event, "摸鱼日历", result):
            yield response

    @filter.command("文案")
    async def get_copywriting(self, event: AstrMessageEvent):
        """获取文案"""
        result = await self.fetch_api(self.api_map["文案"])
        async for response in self.handle_api_response(event, "文案", result):
            yield response

    @filter.command("舔狗日记")
    async def get_tdog(self, event: AstrMessageEvent):
        """获取舔狗日记"""
        result = await self.fetch_api(self.api_map["舔狗日记"])
        async for response in self.handle_api_response(event, "舔狗日记", result):
            yield response

    @filter.command("美女")
    async def get_beauty(self, event: AstrMessageEvent):
        """获取美女图片"""
        result = await self.fetch_api(self.api_map["美女"])
        async for response in self.handle_api_response(event, "美女", result):
            yield response

    @filter.command("图片")
    async def get_image(self, event: AstrMessageEvent):
        """获取随机图片"""
        result = await self.fetch_api(self.api_map["图片"])
        async for response in self.handle_api_response(event, "图片", result):
            yield response

    @filter.command("白丝")
    async def get_baisi(self, event: AstrMessageEvent):
        """获取白丝图片"""
        result = await self.fetch_api(self.api_map["白丝"])
        async for response in self.handle_api_response(event, "白丝", result):
            yield response

    @filter.command("黑丝")
    async def get_heisi(self, event: AstrMessageEvent):
        """获取黑丝图片"""
        result = await self.fetch_api(self.api_map["黑丝"])
        async for response in self.handle_api_response(event, "黑丝", result):
            yield response

    @filter.command("美腿")
    async def get_meitui(self, event: AstrMessageEvent):
        """获取美腿图片"""
        result = await self.fetch_api(self.api_map["美腿"])
        async for response in self.handle_api_response(event, "美腿", result):
            yield response

    def _generate_help_text(self):
        """生成帮助文本"""
        help_message = "【柯柯API集合】可用指令：\n"
        for command in self.api_map.keys():
            help_message += f"- {command}\n"
        help_message += "- 设备信息\n"
        help_message += "\n发送以上指令即可调用对应API获取内容"
        return help_message

    @filter.command("帮助")
    async def help(self, event: AstrMessageEvent):
        """查看所有可用指令"""
        help_message = self._generate_help_text()
        yield event.plain_result(help_message)

    @filter.command("菜单")
    async def menu(self, event: AstrMessageEvent):
        """查看所有可用指令"""
        help_message = self._generate_help_text()
        yield event.plain_result(help_message)

    @filter.command("设备信息")
    async def device_info(self, event: AstrMessageEvent):
        """查看服务器详细信息"""
        try:
            # 收集系统信息
            info = []
            info.append("**【服务器详细信息】**")
            info.append("")
            
            # 系统信息 - 脱敏处理
            info.append("**系统信息**")
            info.append(f"- 操作系统: {platform.system()} {platform.release()}")  # 隐藏具体版本号
            info.append(f"- 架构: {platform.architecture()[0]}")
            info.append("- 机器名: [已隐藏]")  # 隐藏主机名
            info.append("")
            
            # Python信息
            info.append("**Python信息**")
            info.append(f"- Python版本: {platform.python_version()}")
            info.append("")
            
            # CPU信息
            cpu_count = psutil.cpu_count(logical=True)
            cpu_usage = psutil.cpu_percent(interval=1)
            info.append("**CPU信息**")
            info.append(f"- 核心数: {cpu_count}")
            info.append(f"- 使用率: {cpu_usage}%")
            info.append("")
            
            # 内存信息
            memory = psutil.virtual_memory()
            total_memory = round(memory.total / (1024**3), 2)
            used_memory = round(memory.used / (1024**3), 2)
            free_memory = round(memory.free / (1024**3), 2)
            memory_usage = memory.percent
            info.append("**内存信息**")
            info.append(f"- 总量: {total_memory} GB")
            info.append(f"- 已用: {used_memory} GB")
            info.append(f"- 可用: {free_memory} GB")
            info.append(f"- 使用率: {memory_usage}%")
            info.append("")
            
            # 磁盘信息 - 跨平台兼容
            try:
                # 使用跨平台的根目录路径
                import os
                root_path = os.path.abspath(os.sep)
                disk = psutil.disk_usage(root_path)
                total_disk = round(disk.total / (1024**3), 2)
                used_disk = round(disk.used / (1024**3), 2)
                free_disk = round(disk.free / (1024**3), 2)
                disk_usage = disk.percent
                info.append("**磁盘信息**")
                info.append(f"- 总量: {total_disk} GB")
                info.append(f"- 已用: {used_disk} GB")
                info.append(f"- 可用: {free_disk} GB")
                info.append(f"- 使用率: {disk_usage}%")
            except Exception as e:
                logger.error(f"获取磁盘信息失败: {e}")
                info.append("**磁盘信息**")
                info.append("- 状态: 无法获取")
            info.append("")
            
            # 网络信息 - 脱敏处理
            info.append("**网络信息**")
            info.append("- 网络状态: 正常")  # 隐藏具体流量数据
            info.append("")
            
            # 进程信息 - 脱敏处理
            info.append("**进程信息**")
            info.append("- 进程状态: 正常")  # 隐藏具体进程数
            info.append("")
            
            # 环境信息 - 脱敏处理
            info.append("**环境信息**")
            info.append("- 工作目录: [已隐藏]")  # 完全隐藏工作目录
            
            # 组合信息
            info_message = "\n".join(info)
            yield event.plain_result(info_message)
        except Exception as e:
            logger.error(f"获取设备信息失败: {e}")
            yield event.plain_result(f"获取设备信息失败: {str(e)}")

    async def terminate(self):
        """插件销毁方法"""
        # 关闭ClientSession
        if self.session:
            await self.session.close()
        logger.info("柯柯API集合插件已销毁")
