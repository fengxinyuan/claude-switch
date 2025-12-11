# Claude 模型切换工具

跨平台的 Claude API 模型切换工具，支持快速切换不同的 API 提供商，并实时监控 API 状态。

## 功能特性

- ✅ **跨平台支持**: Windows / Linux / macOS
- ✅ **API 状态监控**: 实时检测连接状态、余额、响应时间
- ✅ **交互式界面**: 可视化选择模型，实时显示状态
- ✅ **自动重载**: 切换后自动更新环境变量
- ✅ **配置管理**: 添加/更新/删除模型配置
- ✅ **智能提示**: 当前模型不可用时自动显示其他选项

## 快速开始

### 安装依赖

```bash
pip install requests urllib3
```

### 基本用法

```bash
# 启动交互模式（推荐）
python set_model.py

# 快速切换到指定模型
python set_model.py 哈吉米

# 查看当前模型状态（如果不可用会自动显示所有模型）
python set_model.py current

# 查看所有模型状态
python set_model.py status
```

## 命令详解

### 常用命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `python set_model.py` | 启动交互模式 | - |
| `python set_model.py <模型名>` | 快速切换模型 | `python set_model.py 哈吉米` |
| `python set_model.py current` | 查看当前模型状态 | `python set_model.py cur` |
| `python set_model.py status` | 查看所有模型状态 | `python set_model.py st` |

### 管理命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `add <名称> <URL> [TOKEN]` | 添加新模型 | `python set_model.py add MyAPI https://api.example.com sk-xxx` |
| `update <名称> --url <URL>` | 更新 API 地址 | `python set_model.py update 哈吉米 --url https://new-url.com` |
| `update <名称> --token <TOKEN>` | 更新 API Token | `python set_model.py update 哈吉米 --token sk-new-token` |
| `remove <模型名>` | 删除模型配置 | `python set_model.py remove MyAPI` |

### 其他命令

| 命令 | 说明 | 别名 |
|------|------|------|
| `list` | 列出所有模型（不测试） | `ls`, `-l` |
| `status` | 显示所有模型状态 | `st`, `-s` |
| `current` | 显示当前模型 | `cur`, `-c` |
| `interactive` | 交互模式 | `i`, `-i` |
| `add` | 添加模型 | `-a` |
| `update` | 更新模型 | `up`, `-u` |
| `remove` | 删除模型 | `rm`, `-r` |

## 使用场景

### 场景 1: 日常使用

```bash
# 查看当前模型状态
python set_model.py current

# 如果当前模型不可用，会自动显示所有模型状态
# 然后快速切换到可用的模型
python set_model.py FoxCode
```

### 场景 2: 批量检测

```bash
# 查看所有 API 的状态和响应速度
python set_model.py status
```

输出示例：
```
📋 可用模型列表：
序号   模型名             状态       余额              响应时间
------------------------------------------------------------
1    88Code          ✅        可用              1.15s
2    AnyRouter       ❌        连接失败          N/A
3    FoxCode         ✅        可用              0.66s
```

### 场景 3: 交互式选择

```bash
# 启动交互模式
python set_model.py
```

交互界面会显示：
- 当前使用的模型
- 所有模型的实时状态
- 余额信息
- 响应时间

直接输入序号即可切换。

### 场景 4: 管理配置

```bash
# 添加新的 API
python set_model.py add NewAPI https://api.new.com sk-token123

# 更新现有 API 的地址
python set_model.py update 哈吉米 --url https://new-url.com

# 同时更新地址和 Token
python set_model.py update 哈吉米 --url https://new-url.com --token sk-new-token

# 删除不用的 API
python set_model.py remove OldAPI
```

## 配置文件

配置文件 `model_config.json` 格式：

```json
{
  "模型名称": {
    "ANTHROPIC_BASE_URL": "https://api.example.com",
    "ANTHROPIC_AUTH_TOKEN": "sk-your-token-here"
  }
}
```

## 环境变量

工具会自动设置以下环境变量：

- `ANTHROPIC_BASE_URL`: API 基础地址
- `ANTHROPIC_AUTH_TOKEN`: API 认证令牌

### Linux/macOS

环境变量会写入到 shell 配置文件（按优先级）：
1. `~/.zshrc`
2. `~/.bashrc`
3. `~/.bash_profile`
4. `~/.profile`

切换后会自动在当前会话生效。

### Windows

使用 `setx` 命令设置用户环境变量，需要重新打开命令行窗口生效。

## 优化特性

### 智能工作流

- **current 命令优化**: 检测当前模型时，如果发现不可用，会自动显示所有模型状态，方便快速切换
- **自动重载**: 切换模型后自动更新当前会话的环境变量，无需手动 source
- **批量测试**: status 命令会并发测试所有 API，快速获取状态

### API 测试准确性

- 支持多种 HTTP 状态码判断
- 自动处理 SSL 证书问题
- 超时时间优化（10秒）
- 支持从响应头或响应体获取余额信息

## 常见问题

### Q: 为什么某些 API 显示不可用？

A: 可能的原因：
1. API 服务暂时不可用
2. Token 已过期
3. 网络连接问题
4. API 地址错误

使用 `python set_model.py status` 查看详细错误信息。

### Q: 切换后环境变量没生效？

A:
- **Linux/macOS**: 工具会自动更新当前会话，如果在新终端中需要重新加载配置文件
- **Windows**: 需要重新打开命令行窗口

### Q: 如何备份配置？

A: 直接复制 `model_config.json` 文件即可。

## 开发计划

- [ ] 支持配置文件加密
- [ ] 添加 API 使用统计
- [ ] 支持自定义测试超时时间
- [ ] 添加 API 健康监控和自动切换
- [ ] 支持配置文件导入导出

## 许可证

MIT License
