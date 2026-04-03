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
| 美腿 | https://sbtxqq.com/api/tui.php | 获取美腿图片 |
| R18 | https://rand-r18.mossia.top | 获取R18图片 |
| 色图 | https://rand-x.mossia.top | 获取色图 |

## 使用方法

1. 将插件放入ASTRBOT的插件目录
2. 重启ASTRBOT或加载插件
3. 在聊天中直接输入指令，例如：`摸鱼日历`，插件会自动调用对应API并返回结果

## 注意事项

- 部分API可能存在访问限制或不稳定情况
- 某些API（如R18、色图）可能包含敏感内容，请谨慎使用
- 插件使用了第三方API，请注意遵守相关服务的使用条款

## 技术实现

- 基于Python异步编程，使用`aiohttp`库实现异步API调用
- 自动识别JSON、文本和图片响应
- 完善的错误处理和用户提示
- 多平台适配，使用ASTRBOT的统一接口

## 版本信息

- 版本：1.1.3
- 作者：落梦陳
- 仓库地址：https://github.com/KeKe0904/astrbot_plugin_keke_api_collection

## 更新日志

### v1.1.3
- 优化"设备信息"指令，将返回内容改为图片形式呈现，提供更美观的展示效果
- 添加图片生成失败的容错处理，确保即使生成图片失败也能返回文本信息

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
