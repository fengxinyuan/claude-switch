# Claude 模型切换工具

跨平台的 Claude API 模型切换工具，支持快速切换不同的 API 提供商，并实时监控 API 状态。

## 功能特性

- ✅ **跨平台支持**: Windows / Linux / macOS
- ✅ **API 状态监控**: 实时检测连接状态、响应时间
- ✅ **并发测试**: 快速并发检测多个 API 状态
- ✅ **进度显示**: 测试时显示实时进度条
- ✅ **交互式界面**: 可视化选择模型，实时显示状态
- ✅ **自动重载**: 切换后自动更新环境变量
- ✅ **配置管理**: 添加/更新/删除模型配置
- ✅ **配置备份**: 自动备份和恢复配置文件
- ✅ **敏感信息保护**: Token 信息自动脱敏显示
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
| `show` | 显示配置信息（脱敏） | `python set_model.py show` |
| `backup` | 备份配置文件 | `python set_model.py backup` |
| `restore <文件>` | 从备份恢复配置 | `python set_model.py restore backups/model_config_20240101_120000.json` |

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
| `show` | 显示配置信息 | `info` |
| `backup` | 备份配置 | `bak`, `-b` |
| `restore` | 恢复配置 | `res` |

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
# 查看所有 API 的状态和响应速度（使用并发测试，速度更快）
python set_model.py status
```

输出示例：
```
📋 可用模型列表：
🔍 测试进度 [██████████████████████████████] 6/6 (100%)

序号   模型名             状态       响应时间
---------------------------------------------
1    88Code          ✅        1.15s
2    AnyRouter       ❌        N/A
3    FoxCode         ✅        0.66s
4    Privnode        ✅        0.89s
5    Ohmygpt         ✅        1.23s
6    Gemai           ✅        0.77s
```

### 场景 3: 交互式选择

```bash
# 启动交互模式
python set_model.py
```

交互界面会显示：
- 当前使用的模型
- 所有模型的实时状态（并发测试，带进度条）
- 响应时间

直接输入序号即可切换。

### 场景 4: 配置管理

```bash
# 显示当前配置（Token 自动脱敏）
python set_model.py show

# 添加新的 API
python set_model.py add NewAPI https://api.new.com sk-token123

# 更新现有 API 的地址
python set_model.py update 哈吉米 --url https://new-url.com

# 同时更新地址和 Token
python set_model.py update 哈吉米 --url https://new-url.com --token sk-new-token

# 删除不用的 API
python set_model.py remove OldAPI
```

### 场景 5: 配置备份与恢复

```bash
# 备份当前配置
python set_model.py backup
# 输出: ✅ 配置已备份至: backups/model_config_20240101_120000.json

# 从备份恢复配置
python set_model.py restore backups/model_config_20240101_120000.json
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
- **并发测试**: status 和交互模式使用并发测试，大幅提升检测速度
- **实时进度**: 测试多个 API 时显示实时进度条，清晰展示进度

### API 测试准确性

- 优先使用流式 API 测试（更快更准确）
- 流式失败时自动回退到非流式请求
- 只要收到响应就认为 API 在线（关注连接性而非请求成功与否）
- 支持 400/429 等状态码（API 在线但受限）
- 自动处理 SSL 证书问题
- 超时时间优化（10秒）

### 配置管理增强

- **自动备份**: 支持配置文件备份，自动生成时间戳
- **一键恢复**: 可快速从备份恢复配置
- **信息脱敏**: 显示配置时自动脱敏 Token 信息，保护安全
- **配置预览**: 可查看所有配置信息而不泄露完整 Token

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

A:
- **快速备份**: `python set_model.py backup`
- 备份文件会保存到 `backups/` 目录，文件名包含时间戳
- **从备份恢复**: `python set_model.py restore backups/model_config_YYYYMMDD_HHMMSS.json`

## 性能优化

### 并发测试性能

- 使用多线程并发测试（最多 5 个并发）
- 相比串行测试，速度提升 **3-5 倍**
- 6 个 API 的测试时间从 ~60 秒降至 ~12 秒

### 进度可视化

- 实时进度条显示测试进度
- 清晰的视觉反馈，提升用户体验

## 开发计划

- [x] 并发测试优化
- [x] 进度条显示
- [x] 配置文件备份与恢复
- [x] 敏感信息脱敏显示
- [ ] 支持配置文件加密
- [ ] 添加 API 使用统计
- [ ] 支持自定义测试超时时间
- [ ] 添加 API 健康监控和自动切换
- [ ] 支持配置文件导入导出

## 许可证

MIT License
