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
  }
}
```

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

## 性能优化

- **并发测试**: 使用多线程（最多 10 并发），速度提升 3-5 倍
- **热身请求**: 绕过首包惩罚，提高测速准确性
- **流式 API**: 优先使用流式 API 测试，更快更准确

## 许可证

MIT License
