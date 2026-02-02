# Claude Switch

Claude API 模型切换工具，支持快速切换不同的 API 提供商，并实时监控 API 状态。

## 特性

- 🚀 **一键配置** - 自动配置别名，开箱即用
- 🔄 **快速切换** - 即时切换 API 提供商，环境变量立即生效
- 🌍 **全局可用** - 配置存储在 `~/.config/claude-switch/`，任何目录都能使用
- 📊 **状态监控** - 实时检测连接状态、响应时间
- ⚡ **并发测试** - 快速并发检测多个 API（3-5倍提速）
- 🎯 **交互模式** - 可视化选择，实时显示状态
- 🌐 **跨平台** - Windows / Linux / macOS

## 安装

```bash
git clone https://github.com/fengxinyuan/claude-switch.git
cd claude-switch

# 安装基础依赖
pip install requests urllib3
```

## 快速开始

### 1. 配置别名

```bash
# 自动配置 claude-switch 别名
python set_model.py setup-alias

# 重新加载配置
source ~/.bashrc  # 或 source ~/.zshrc
```

### 2. 添加 API 配置

```bash
# 交互式添加（推荐）
claude-switch add

# 命令行添加
claude-switch add MyAPI https://api.example.com sk-your-token
```

### 3. 开始使用

```bash
# 交互式选择模型（显示所有模型+状态）
claude-switch

# 快速切换到指定模型（环境变量立即生效）
claude-switch MyAPI

# 查看当前模型详情（含地址和Token）
claude-switch status

# 查看所有模型状态列表
claude-switch list
```

**💡 现在可以在任何目录使用 `claude-switch` 命令了！**

## 使用方法

### 基础命令

```bash
# 交互模式（显示所有模型状态+选择切换）
claude-switch

# 快速切换模型
claude-switch <模型名>

# 查看当前模型详情（地址、Token、状态）
claude-switch status

# 查看所有模型状态列表
claude-switch list
```

### 配置管理

```bash
# 添加模型（交互式或命令行）
claude-switch add                         # 交互式添加
claude-switch add <名称> <URL> [TOKEN]    # 命令行添加

# 更新模型配置（支持交互式和参数模式）
claude-switch update <名称>               # 交互式更新所有字段
claude-switch update <名称> --url <URL>   # 快速更新URL
claude-switch update <名称> --token <TOKEN>      # 快速更新Token
claude-switch update <名称> --name <新名称>       # 重命名模型
claude-switch update <名称> --url <URL> --token <TOKEN>  # 同时更新多个

# 删除模型
claude-switch remove <名称>

# 显示所有配置（Token 脱敏）
claude-switch show
```

## 配置文件

配置文件自动存储在：`~/.config/claude-switch/config.json`

```json
{
  "模型名称": {
    "ANTHROPIC_BASE_URL": "https://api.example.com",
    "ANTHROPIC_AUTH_TOKEN": "sk-your-token-here"
  },
  "自定义模型": {
    "ANTHROPIC_BASE_URL": "https://api.example.com",
    "ANTHROPIC_AUTH_TOKEN": "sk-your-token-here",
    "ANTHROPIC_MODEL": "custom-model-name",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "custom-model-name",
    "CLAUDE_CODE_SUBAGENT_MODEL": "custom-model-name"
  }
}
```

**支持自定义模型配置**：可以添加 `ANTHROPIC_MODEL`、`ANTHROPIC_DEFAULT_OPUS_MODEL` 等自定义配置，切换时会自动应用，切换到其他模型时会自动清理。

**查看配置路径**:
```bash
claude-switch config
```

**自动迁移**: 首次使用时，如果检测到项目目录下的 `model_config.json`，会自动迁移到全局配置目录。

## 命令别名

| 命令 | 别名 |
|------|------|
| `list` | `ls` |
| `status` | `st` |
| `update` | `up` |
| `remove` | `rm` |

## 环境变量

工具会自动设置以下环境变量：

- `ANTHROPIC_BASE_URL` - API 基础地址
- `ANTHROPIC_AUTH_TOKEN` - API 认证令牌

**Linux/macOS**: 写入 shell 配置文件（.bashrc / .zshrc），使用 `claude-switch` 命令时立即生效

**Windows**: 使用 `setx` 设置用户环境变量，需要重新打开命令行窗口

## 常见问题

### Q: 切换后环境变量没生效？

**A**: 使用 `claude-switch` 别名命令，环境变量会立即生效。如果使用 `python set_model.py` 方式，需要手动执行 `source ~/.bashrc`

### Q: 如何修改模型配置？

**A**: 使用 `claude-switch update <模型名>` 进入交互式编辑，或使用 `--url`, `--token`, `--name` 参数快速修改

### Q: 如何查看所有模型状态？

**A**: 直接运行 `claude-switch`（无参数）进入交互模式，会显示所有模型的实时状态、响应时间，并可以选择切换

### Q: 如何使用自定义模型名称？

**A**: 编辑配置文件 `~/.config/claude-switch/config.json`，添加自定义模型配置：
```json
{
  "MyAPI": {
    "ANTHROPIC_BASE_URL": "https://api.example.com",
    "ANTHROPIC_AUTH_TOKEN": "sk-token",
    "ANTHROPIC_MODEL": "custom-model-name",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "custom-model-name"
  }
}
```
切换时会自动应用这些配置，切换到其他模型时会自动清理。

### Q: 测活方式为什么用技术问题？

**A**: 使用真实的开发问题（如 "What's Python?"、"Explain REST API"）模拟真实用户查询，避免被API提供商检测为机器人或滥用。同时配合真实浏览器 User-Agent，更接近正常使用场景。

## 性能优化

- **并发测试**: 使用多线程（最多 10 并发），速度提升 3-5 倍
- **智能测活**: 模拟真实用户请求，使用技术问题作为测试消息，避免被检测为机器人
- **真实请求头**: 随机使用真实浏览器 User-Agent，降低被识别风险
- **超时优化**: 8秒超时，平衡准确性和速度
- **流式 API**: 优先使用流式 API 测试，更快更准确
- **自动清理**: 切换模型时自动清理旧模型的自定义配置，避免污染

## 许可证

MIT License
