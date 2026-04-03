from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import aiohttp
import json
import base64
import platform
import os
import sys
import psutil
from PIL import Image, ImageDraw, ImageFont
import io

@register("keke_api_collection", "落梦陳", "【柯柯API集合】包含多种图片和文案API，支持摸鱼日历、文案、舔狗日记、美女、图片、白丝、黑丝、美腿、R18、色图", "1.1.3")
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
        help_message += "- 设备信息\n"
        help_message += "\n发送以上指令即可调用对应API获取内容"
        yield event.plain_result(help_message)

    @filter.command("菜单")
    async def menu(self, event: AstrMessageEvent):
        """查看所有可用指令"""
        # 复用help方法的逻辑
        help_message = "【柯柯API集合】可用指令：\n"
        for command in self.api_map.keys():
            help_message += f"- {command}\n"
        help_message += "- 设备信息\n"
        help_message += "\n发送以上指令即可调用对应API获取内容"
        yield event.plain_result(help_message)

    @filter.command("设备信息")
    async def device_info(self, event: AstrMessageEvent):
        """查看服务器详细信息"""
        try:
            # 收集系统信息
            info = []
            info.append("【服务器信息】")
            
            # 系统信息
            info.append(f"操作系统: {platform.system()} {platform.release()} {platform.version()}")
            info.append(f"架构: {platform.architecture()[0]}")
            info.append(f"机器名: {platform.node()}")
            
            # Python信息
            info.append(f"Python版本: {platform.python_version()}")
            
            # CPU信息
            cpu_count = psutil.cpu_count(logical=True)
            cpu_usage = psutil.cpu_percent(interval=1)
            info.append(f"CPU核心数: {cpu_count}")
            info.append(f"CPU使用率: {cpu_usage}%")
            
            # 内存信息
            memory = psutil.virtual_memory()
            total_memory = round(memory.total / (1024**3), 2)
            used_memory = round(memory.used / (1024**3), 2)
            free_memory = round(memory.free / (1024**3), 2)
            memory_usage = memory.percent
            info.append(f"内存总量: {total_memory} GB")
            info.append(f"已用内存: {used_memory} GB")
            info.append(f"可用内存: {free_memory} GB")
            info.append(f"内存使用率: {memory_usage}%")
            
            # 磁盘信息
            disk = psutil.disk_usage('/')
            total_disk = round(disk.total / (1024**3), 2)
            used_disk = round(disk.used / (1024**3), 2)
            free_disk = round(disk.free / (1024**3), 2)
            disk_usage = disk.percent
            info.append(f"磁盘总量: {total_disk} GB")
            info.append(f"已用磁盘: {used_disk} GB")
            info.append(f"可用磁盘: {free_disk} GB")
            info.append(f"磁盘使用率: {disk_usage}%")
            
            # 网络信息
            net_io = psutil.net_io_counters()
            bytes_sent = round(net_io.bytes_sent / (1024**2), 2)
            bytes_recv = round(net_io.bytes_recv / (1024**2), 2)
            info.append(f"已发送流量: {bytes_sent} MB")
            info.append(f"已接收流量: {bytes_recv} MB")
            
            # 进程信息
            process_count = len(psutil.pids())
            info.append(f"当前进程数: {process_count}")
            
            # 环境信息
            info.append(f"当前工作目录: {os.getcwd()}")
            
            # 生成图片
            try:
                # 创建图片
                width, height = 600, 600
                image = Image.new('RGB', (width, height), color=(240, 240, 240))
                draw = ImageDraw.Draw(image)
                
                # 尝试加载字体
                try:
                    # 尝试使用系统字体
                    font = ImageFont.truetype('arial.ttf', 14)
                except:
                    # 如果没有arial字体，使用默认字体
                    font = ImageFont.load_default()
                
                # 绘制标题
                title_font = ImageFont.truetype('arial.ttf', 18) if 'arial.ttf' in os.listdir() else font
                draw.text((50, 30), "服务器信息", fill=(0, 0, 0), font=title_font)
                
                # 绘制信息
                y_offset = 70
                line_height = 25
                for line in info[1:]:  # 跳过标题，因为已经单独绘制
                    draw.text((50, y_offset), line, fill=(0, 0, 0), font=font)
                    y_offset += line_height
                
                # 将图片转换为字节流
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                
                # 将字节流编码为base64
                img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
                
                # 构建data URL
                img_data_url = f"data:image/png;base64,{img_base64}"
                
                # 返回图片
                yield event.image_result(img_data_url)
            except Exception as img_error:
                logger.error(f"生成图片失败: {img_error}")
                # 如果生成图片失败，返回文本信息
                info_message = "\n".join(info)
                yield event.plain_result(info_message)
        except Exception as e:
            logger.error(f"获取设备信息失败: {e}")
            yield event.plain_result(f"获取设备信息失败: {str(e)}")

    async def terminate(self):
        """插件销毁方法"""
        logger.info("柯柯API集合插件已销毁")
