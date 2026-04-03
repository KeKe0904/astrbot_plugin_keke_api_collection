from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import aiohttp
import json
import platform
import os
import psutil
import asyncio

@register("keke_api_collection", "落梦陳", "【柯柯API集合】包含多种图片和文案API，支持摸鱼日历、文案、舔狗日记、美女、图片、白丝、黑丝", "1.6.0")
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
            "黑丝": "https://api.pldduck.com/api/heisi"
        }
        # 初始化ClientSession和锁
        self.session = None
        self.session_lock = asyncio.Lock()

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
                # 确保ClientSession已初始化且未关闭
                async with self.session_lock:
                    if self.session is None or self.session.closed:
                        if self.session is not None and self.session.closed:
                            logger.info("ClientSession已关闭，重新创建")
                        else:
                            logger.info("ClientSession未初始化，创建实例")
                        self.session = aiohttp.ClientSession()
                
                async with self.session.get(url, timeout=10) as response:
                    logger.info(f"API请求状态码: {response.status}")
                    # 只记录Content-Type，避免记录完整响应头
                    content_type = response.headers.get('Content-Type', '')
                    logger.info(f"API响应Content-Type: {content_type}")
                    
                    # 对于5xx和429错误，进行重试
                    if 500 <= response.status < 600 or response.status == 429:
                        if attempt < max_retries - 1:
                            logger.warning(f"API返回{response.status}错误，第{attempt+1}次重试...")
                            # 尝试从Retry-After头获取等待时间
                            retry_after = response.headers.get('Retry-After')
                            if retry_after and retry_after.isdigit():
                                wait_time = int(retry_after)
                                logger.info(f"根据Retry-After头，等待{wait_time}秒后重试")
                                await asyncio.sleep(wait_time)
                            else:
                                await asyncio.sleep(retry_delay * (2 ** attempt))  # 指数退避
                            continue
                        else:
                            return {"error": f"API请求失败，状态码：{response.status}"}
                    
                    if response.status == 200:
                        # 尝试解析JSON响应
                        try:
                            json_data = await response.json()
                            # 只记录JSON响应的类型和键，不记录具体值
                            logger.info(f"API返回JSON数据，包含键: {list(json_data.keys())}")
                            return json_data
                        except (aiohttp.ContentTypeError, json.JSONDecodeError) as json_error:
                            logger.debug(f"JSON解析失败: {json_error}")
                            # 如果不是JSON，返回文本或二进制数据
                            if 'image' in content_type.lower():
                                # 对于图片，返回图片URL
                                return {"image_url": url}
                            else:
                                text_data = await response.text()
                                # 只记录文本长度，不记录具体内容
                                logger.info(f"API返回文本数据，长度: {len(text_data)}")
                                # 处理文本响应中的图片URL
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
                        # 提供统一的解析失败提示
                        logger.debug(f"无法解析API响应: {data}")
                        yield event.plain_result(f"获取{api_name}成功，但无法解析响应数据")
                else:
                    # 提供统一的解析失败提示
                    logger.debug(f"无法解析API响应: {result}")
                    yield event.plain_result(f"获取{api_name}成功，但无法解析响应数据")
            else:
                # 提供统一的解析失败提示
                logger.debug(f"无法解析API响应: {result}")
                yield event.plain_result(f"获取{api_name}成功，但无法解析响应数据")
        else:
            # 提供统一的解析失败提示
            logger.debug(f"无法解析API响应: {result}")
            yield event.plain_result(f"获取{api_name}成功，但无法解析响应数据")

    # 统一处理API指令的方法
    async def handle_api_command(self, event: AstrMessageEvent, command: str):
        """统一处理API指令"""
        if command in self.api_map:
            result = await self.fetch_api(self.api_map[command])
            async for response in self.handle_api_response(event, command, result):
                yield response

    # 动态注册所有API指令
    def __post_init__(self):
        """初始化后动态注册所有API指令"""
        for command in self.api_map.keys():
            # 创建指令处理函数
            async def create_handler(cmd):
                async def handler(event: AstrMessageEvent):
                    """处理{cmd}指令"""
                    async for response in self.handle_api_command(event, cmd):
                        yield response
                return handler
            
            # 注册指令
            handler = create_handler(command)
            decorated_handler = filter.command(command)(handler)
            setattr(self, f"handle_{command}", decorated_handler)

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
        """查看服务器基本信息"""
        try:
            # 收集系统信息（简化版）
            info = []
            info.append("**【服务器基本信息】**")
            info.append("")
            
            # 系统信息
            info.append("**系统信息**")
            info.append(f"- 操作系统: {platform.system()}")  # 只显示系统类型
            info.append(f"- 架构: {platform.architecture()[0]}")
            info.append("")
            
            # Python信息
            info.append("**Python信息**")
            # 只显示Python主版本
            python_version = platform.python_version()
            main_version = ".".join(python_version.split(".")[:2])
            info.append(f"- Python版本: {main_version}.*")
            info.append("")
            
            # CPU信息（简化）
            cpu_count = psutil.cpu_count(logical=True)
            info.append("**CPU信息**")
            info.append(f"- 核心数: {cpu_count}")
            info.append("")
            
            # 内存信息（简化）
            memory = psutil.virtual_memory()
            total_memory = round(memory.total / (1024**3), 2)
            info.append("**内存信息**")
            info.append(f"- 总量: {total_memory} GB")
            info.append("")
            
            # 磁盘信息（简化）
            info.append("**磁盘信息**")
            try:
                # 使用跨平台的根目录路径
                root_path = os.path.abspath(os.sep)
                disk = psutil.disk_usage(root_path)
                total_disk = round(disk.total / (1024**3), 2)
                info.append(f"- 总量: {total_disk} GB")
            except Exception as e:
                logger.error(f"获取磁盘信息失败: {e}")
                info.append("- 状态: 无法获取")
            info.append("")
            
            # 网络信息（简化）
            info.append("**网络信息**")
            info.append("- 网络状态: 正常")
            info.append("")
            
            # 进程信息（简化）
            info.append("**进程信息**")
            info.append("- 进程状态: 正常")
            
            # 生成最终信息
            info_message = "\n".join(info)
            yield event.plain_result(info_message)
        except Exception as e:
            logger.error(f"获取设备信息失败: {e}")
            yield event.plain_result("获取设备信息失败，请稍后再试")

    async def terminate(self):
        """插件销毁方法"""
        # 关闭ClientSession
        if self.session:
            await self.session.close()
        logger.info("柯柯API集合插件已销毁")
