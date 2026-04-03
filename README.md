# astrbot_plugin_keke_api_collection

柯柯API集合插件 / Keke API Collection Plugin for AstrBot

## 插件介绍

这是一个为AstrBot开发的API调用插件，支持多个有趣的API接口，包括摸鱼日历、文案生成、舔狗日记、美女图片等多种内容。

### 支持平台
- QQ个人号(aiocqhttp)
- webchat
- QQ官方接口

## 支持的指令

| 指令 | API地址 | 功能描述 |
|------|---------|----------|
| 摸鱼日历 | https://openapi.dwo.cc/api/moyuya | 获取每日摸鱼日历 |
| 文案 | https://openapi.dwo.cc/api/yi | 生成随机文案 |
| 舔狗日记 | https://openapi.dwo.cc/api/tdog | 获取舔狗日记 |
| 美女 | https://openapi.dwo.cc/api/pc_mn | 获取美女图片 |
| 图片 | https://openapi.dwo.cc/api/yrcmcx | 获取随机图片 |
| 白丝 | https://api.pldduck.com/api/baisi | 获取白丝图片 |
| 黑丝 | https://api.pldduck.com/api/heisi | 获取黑丝图片 |

## 使用方法

1. 将插件放入ASTRBOT的插件目录
2. 重启ASTRBOT或加载插件
3. 在聊天中直接输入指令，例如：`摸鱼日历`，插件会自动调用对应API并返回结果

## 注意事项

- 部分API可能存在访问限制或不稳定情况
- 插件使用了第三方API，请注意遵守相关服务的使用条款

## 技术实现

- 基于Python异步编程，使用`aiohttp`库实现异步API调用
- 自动识别JSON、文本和图片响应
- 完善的错误处理和用户提示
- 多平台适配，使用ASTRBOT的统一接口

## 版本信息

- 版本：1.6.1
- 作者：落梦陳
- 仓库地址：https://github.com/KeKe0904/astrbot_plugin_keke_api_collection

## 更新日志

### v1.6.1
- 代码优化：将动态注册改回明确的指令注册方式，确保AstrBot能够正确识别和触发指令

### v1.6.0
- 安全优化：修复ClientSession并发初始化竞态问题，使用asyncio.Lock保护
- 安全优化：处理ClientSession已关闭状态，避免运行时错误
- 安全优化：对日志进行脱敏处理，避免泄露外部响应内容
- 安全优化：简化设备信息显示，减少敏感信息暴露
- 代码优化：抽象统一命令处理函数，减少重复代码
- 功能优化：增强HTTP状态码处理，支持429限流错误重试
- 功能优化：改进API响应处理，提供统一的解析失败提示

### v1.5.0
- 代码优化：移除无用导入（base64）
- 代码优化：移除重复导入（os）
- 功能优化：增强content_type判断，使用lower()进行更严谨的匹配
- 安全优化：修复ClientSession懒加载的竞态条件风险
- 性能优化：修复device_info方法中的事件循环阻塞问题，使用run_in_executor

### v1.4.2
- 移除美腿指令和API：由于API不稳定且存在反爬虫机制，移除该指令

### v1.4.1
- 修复美腿指令：添加对HTML响应的检测和处理，解决返回`<script src="/_guard/html.js?js=slider_html"></script>`错误的问题
- 增强美腿API错误处理：当API返回反爬虫页面时，提供友好的错误提示

### v1.4.0
- 重构指令注册方式：使用动态注册，减少重复代码，使代码更加优雅
- 移除无意义的Base64编码：直接使用明文API地址，提高代码可读性
- 修复跨平台兼容性问题：使用os.path.abspath(os.sep)获取根目录，解决Windows平台上的路径问题
- 优化插件初始化：使用@filter.on_astrbot_loaded()钩子，确保ClientSession在插件加载时正确创建
- 解决并发状态竞争问题：通过插件加载时初始化ClientSession，避免多个并发请求创建多个Session
- 简化代码结构：移除handle_api_request中间层，直接在指令处理函数中调用fetch_api

### v1.3.1
- 修复asyncio导入问题：添加全局asyncio导入，移除方法内的局部导入，解决"cannot access local variable 'asyncio'"错误

### v1.3.0
- 优化异步网络资源管理：在插件生命周期内复用ClientSession，提高性能和稳定性
- 添加网络请求重试机制：对超时、连接错误、5xx错误增加有限次重试与指数退避
- 增强设备信息安全性：默认脱敏输出，隐藏主机名、目录、进程信息等敏感内容
- 优化异常处理：捕获明确的异常类型，便于定位问题
- 重构帮助文案实现：提取私有方法统一生成帮助文本，避免代码重复
- 清理未使用导入：删除MessageEventResult、sys等未使用的导入项

### v1.2.1
- 修复美腿指令：优化API响应处理，添加特殊处理逻辑，确保美腿图片能正常显示
- 增强API请求日志：添加详细的请求和响应日志，便于调试

### v1.2.0
- 移除敏感内容：删除"R18"和"色图"指令
- 优化设备信息显示：隐藏具体路径，保护隐私
- 提升插件安全性和合规性

### v1.1.2
- 新增"设备信息"指令，返回服务器详细信息，包括系统、CPU、内存、磁盘、网络等信息
- 更新帮助和菜单指令，添加"设备信息"指令的说明

### v1.1.1
- 优化代码，移除API请求时的提示信息，提供更流畅的用户体验
- 对API地址进行Base64加密处理，提高代码安全性
- 添加"帮助"和"菜单"指令，方便用户查看所有可用指令
- 修复已知问题，提升插件稳定性

# Supports

- [AstrBot Repo](https://github.com/AstrBotDevs/AstrBot)
- [AstrBot Plugin Development Docs (Chinese)](https://docs.astrbot.app/dev/star/plugin-new.html)
- [AstrBot Plugin Development Docs (English)](https://docs.astrbot.app/en/dev/star/plugin-new.html)
