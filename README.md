# Claude Switch

Claude API 模型切换工具，支持快速切换不同的 API 提供商，并实时监控 API 状态。

## 特性

- 🚀 **一键配置** - 自动配置别名，开箱即用
- 🔄 **快速切换** - 即时切换 API 提供商，环境变量立即生效
- 🌍 **全局可用** - 配置存储在 `~/.config/claude-switch/`，任何目录都能使用
- 📊 **状态监控** - 实时检测连接状态、响应时间
- ⚡ **并发测试** - 快速并发检测多个 API（3-5倍提速）
- 🎯 **交互模式** - 可视化选择，实时显示状态
- 🔐 **配置加密** - PBKDF2 + Fernet 加密保护敏感信息
- 📈 **使用统计** - 记录切换历史和使用频率
- 🏥 **健康监控** - 自动故障转移到可用 API
- 🔗 **深度链接** - 一键分享配置
- 🌐 **跨平台** - Windows / Linux / macOS

## 安装

```bash
git clone https://github.com/fengxinyuan/claude-switch.git
cd claude-switch

# 安装基础依赖
pip install requests urllib3

# 可选：加密功能
pip install cryptography
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
# 查看所有模型状态
claude-switch status

# 交互式选择模型
claude-switch

# 快速切换到指定模型（环境变量立即生效）
claude-switch MyAPI

# 查看当前模型
claude-switch current
```

**💡 现在可以在任何目录使用 `claude-switch` 命令了！**

## 使用方法

### 基础命令

```bash
# 切换模型（默认命令）
claude-switch <模型名>

# 交互模式
claude-switch

# 查看当前模型
claude-switch current

# 查看所有模型状态
claude-switch status
```

### 配置管理

```bash
# 添加模型
claude-switch add <名称> <URL> [TOKEN]

# 更新 URL
claude-switch update <名称> --url <URL>

# 更新 Token
claude-switch update <名称> --token <TOKEN>

# 删除模型
claude-switch remove <名称>

# 显示配置（Token 脱敏）
claude-switch show

# 备份配置
claude-switch backup

# 恢复配置
claude-switch restore <文件>
```

### 高级功能

```bash
# 自动切换到最快的可用 API
claude-switch auto

# 查看 API 健康状态
claude-switch health

# 查看使用统计
claude-switch stats

# 导出配置
claude-switch export config.json

# 导入配置
claude-switch import config.json

# 生成分享链接
claude-switch share <模型名>
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
claude-switch config-path
```

**自动迁移**: 首次使用时，如果检测到项目目录下的 `model_config.json`，会自动迁移到全局配置目录。

## 深度链接分享

快速分享 API 配置给他人：

```bash
# 生成分享链接（不含 Token）
claude-switch share MyAPI

# 生成分享链接（含完整 Token，谨慎使用）
claude-switch share MyAPI --with-token

# 对方导入配置
claude-switch import 'claude-switch://import?data=...'
```

## 命令别名

| 命令 | 别名 |
|------|------|
| `list` | `ls`, `-l` |
| `status` | `st`, `-s` |
| `current` | `cur`, `-c` |
| `interactive` | `i`, `-i` |
| `add` | `-a` |
| `update` | `up`, `-u` |
| `remove` | `rm`, `-r` |
| `show` | `info` |
| `backup` | `bak`, `-b` |
| `restore` | `res` |
| `auto` | `auto-switch` |
| `setup-alias` | `setup` |

## 环境变量

工具会自动设置以下环境变量：

- `ANTHROPIC_BASE_URL` - API 基础地址
- `ANTHROPIC_AUTH_TOKEN` - API 认证令牌

**Linux/macOS**: 写入 shell 配置文件（.bashrc / .zshrc），使用 `claude-switch` 命令时立即生效

**Windows**: 使用 `setx` 设置用户环境变量，需要重新打开命令行窗口

## 常见问题

### Q: 切换后环境变量没生效？

**A**: 使用 `claude-switch` 别名命令，环境变量会立即生效。如果使用 `python set_model.py` 方式，需要手动 `source ~/.bashrc`

### Q: 如何备份配置？

**A**:
```bash
# 备份
claude-switch backup  # 保存到 backups/ 目录

# 恢复
claude-switch restore backups/model_config_YYYYMMDD_HHMMSS.json
```

### Q: 如何在多台设备间同步配置？

**A**: 使用导入导出功能
```bash
# 源设备导出
claude-switch export config.json --with-tokens

# 目标设备导入
claude-switch import config.json
```

## 性能优化

- **并发测试**: 使用多线程（最多 10 并发），速度提升 3-5 倍
- **热身请求**: 绕过首包惩罚，提高测速准确性
- **流式 API**: 优先使用流式 API 测试，更快更准确

## 许可证

MIT License
