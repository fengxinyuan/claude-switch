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
- ✅ **配置文件加密**: 使用 PBKDF2 + Fernet 算法加密配置
- ✅ **API 使用统计**: 记录切换次数、使用频率等统计信息
- ✅ **自定义超时**: 支持自定义 API 测试超时时间
- ✅ **健康监控**: 自动检测 API 健康状态并切换到可用 API
- ✅ **配置导入导出**: 支持配置的跨设备迁移和分享
- 🆕 **热身请求**: 使用热身请求技术提高测速准确性
- 🆕 **深度链接**: 一键生成分享链接，快速导入配置

## 快速开始

### 安装依赖

```bash
# 基础依赖
pip install requests urllib3

# 可选：加密功能需要
pip install cryptography
```

### 基本用法

#### 方式 1: 使用 Shell Wrapper（推荐 - 切换立即生效）

```bash
# 首次使用，添加别名到 shell 配置文件
echo "alias claude-switch='source $(pwd)/switch_model.sh'" >> ~/.bashrc  # 或 ~/.zshrc
source ~/.bashrc  # 或 source ~/.zshrc

# 启动交互模式
claude-switch

# 快速切换到指定模型（切换后立即在当前会话生效）
claude-switch Gemai

# 查看当前模型状态
claude-switch current
```

#### 方式 2: 直接使用 Python（需要手动 source）

```bash
# 启动交互模式
python set_model.py

# 快速切换到指定模型
python set_model.py Gemai

# ⚠️ 切换后需要手动执行以下命令使环境变量生效：
source ~/.bashrc  # 或 source ~/.zshrc

# 查看当前模型状态（如果不可用会自动显示所有模型）
python set_model.py current

# 查看所有模型状态
python set_model.py status

# 自动检测并切换到最快的可用 API
python set_model.py auto
```

**💡 推荐使用方式 1（Shell Wrapper），切换后环境变量立即在当前会话生效，无需手动 source！**

## 命令详解

### 常用命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `python set_model.py` | 启动交互模式 | - |
| `python set_model.py <模型名>` | 快速切换模型 | `python set_model.py Gemai` |
| `python set_model.py current` | 查看当前模型状态 | `python set_model.py cur` |
| `python set_model.py status` | 查看所有模型状态 | `python set_model.py st` |

### 管理命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `add <名称> <URL> [TOKEN]` | 添加新模型 | `python set_model.py add MyAPI https://api.example.com sk-xxx` |
| `update <名称> --url <URL>` | 更新 API 地址 | `python set_model.py update Gemai --url https://new-url.com` |
| `update <名称> --token <TOKEN>` | 更新 API Token | `python set_model.py update Gemai --token sk-new-token` |
| `remove <模型名>` | 删除模型配置 | `python set_model.py remove MyAPI` |
| `show` | 显示配置信息（脱敏） | `python set_model.py show` |
| `backup` | 备份配置文件 | `python set_model.py backup` |
| `restore <文件>` | 从备份恢复配置 | `python set_model.py restore backups/model_config_20240101_120000.json` |

### 导入导出命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `export <文件> [--with-tokens]` | 导出配置 | `python set_model.py export config.json` |
| `import <文件> [--merge]` | 导入配置 | `python set_model.py import config.json --merge` |
| `share <模型名> [--with-token]` | 生成分享链接 | `python set_model.py share Gemai` |
| `import '<链接>'` | 从链接导入配置 | `python set_model.py import 'claude-switch://...'` |

### 统计命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `stats` | 查看使用统计 | `python set_model.py stats` |
| `reset-stats` | 重置统计数据 | `python set_model.py reset-stats` |

### 健康监控命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `health` | 查看所有 API 健康状态 | `python set_model.py health` |
| `auto` | 自动检查并切换到可用 API | `python set_model.py auto` |

### 安全命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `encrypt` | 加密配置文件 | `python set_model.py encrypt` |
| `decrypt` | 解密配置文件 | `python set_model.py decrypt` |

### 全局参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--timeout, -t <秒>` | 设置 API 测试超时时间 | `python set_model.py status -t 10` |

### 命令别名

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
2    AnyRouter       ✅        0.56s
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

### 场景 4: 自动故障转移

```bash
# 自动检测当前 API，如果不可用则切换到最快的可用 API
python set_model.py auto
```

输出示例：
```
⚠️  当前模型 'Gemai' 不可用
🔍 正在查找可用的替代API...
🔍 测试进度 [██████████████████████████████] 6/6 (100%)

✅ 找到最佳替代: AnyRouter (响应时间: 0.52s)
🔄 正在自动切换...
```

### 场景 5: 配置管理

```bash
# 显示当前配置（Token 自动脱敏）
python set_model.py show

# 添加新的 API
python set_model.py add NewAPI https://api.new.com sk-token123

# 更新现有 API 的地址
python set_model.py update Gemai --url https://new-url.com

# 同时更新地址和 Token
python set_model.py update Gemai --url https://new-url.com --token sk-new-token

# 删除不用的 API
python set_model.py remove OldAPI
```

### 场景 6: 配置备份与恢复

```bash
# 备份当前配置
python set_model.py backup
# 输出: ✅ 配置已备份至: backups/model_config_20240101_120000.json

# 从备份恢复配置
python set_model.py restore backups/model_config_20240101_120000.json
```

### 场景 7: 配置导入导出与分享

```bash
# 导出配置（不含 Token，安全分享）
python set_model.py export my_config.json

# 导出配置（含完整 Token）
python set_model.py export my_config.json --with-tokens

# 导入配置（覆盖模式）
python set_model.py import shared_config.json

# 导入配置（合并模式，保留现有配置）
python set_model.py import shared_config.json --merge

# 🆕 生成分享链接（快速分享配置）
python set_model.py share Gemai
```

**分享链接示例：**
```bash
# 生成不含 Token 的分享链接
python set_model.py share FoxCode

输出：
📤 分享链接已生成：
claude-switch://import?data=eyJuYW1lIjogIkZveENvZGUiLCAiYmFzZV91cmwiOiAiaHR0cHM6Ly9jb2RlLm5ld2NsaS5jb20vY2xhdWRlL2ZyZWUifQ==

💡 使用方式：
  1. 复制上面的链接发送给其他人
  2. 对方运行: python set_model.py import '<链接>'
  3. 自动添加配置到他们的工具中

💡 提示: Token 未包含，对方需要手动输入
```

```bash
# 对方导入配置（会提示输入 Token）
python set_model.py import 'claude-switch://import?data=...'

输出：
📥 正在导入配置: FoxCode
   BASE_URL: https://code.newcli.com/claude/free
   TOKEN: 未包含（需要手动输入）

请输入 TOKEN: sk-xxx...
✅ 配置导入成功！
```

```bash
# 生成含完整 Token 的分享链接（谨慎使用）
python set_model.py share Gemai --with-token

输出：
📤 分享链接已生成：
claude-switch://import?data=...

⚠️  安全提示: 链接包含完整 Token，请谨慎分享！
```

### 场景 8: 配置加密

```bash
# 加密配置文件（需要安装 cryptography）
python set_model.py encrypt
# 输入密码后，原始配置文件会被删除，生成加密文件

# 解密配置文件
python set_model.py decrypt
# 输入正确密码后恢复原始配置
```

### 场景 9: 使用统计

```bash
# 查看使用统计
python set_model.py stats
```

输出示例：
```
📊 API 使用统计
==================================================
总切换次数: 42
使用的模型数: 5
最后切换: Gemai (2025-12-16 15:30:00)
最常用模型: AnyRouter (15 次)

📈 各模型使用详情:
--------------------------------------------------
模型名             切换次数       最后使用
--------------------------------------------------
AnyRouter       15         2025-12-16 14:00:00
Gemai           12         2025-12-16 15:30:00
FoxCode         8          2025-12-15 10:00:00
...

📅 最近 7 天使用情况:
--------------------------------------------------
2025-12-16: 5 次 (Gemai:3, AnyRouter:2)
2025-12-15: 8 次 (FoxCode:5, Gemai:3)
...
```

### 场景 10: 健康监控

```bash
# 查看所有 API 的健康状态报告
python set_model.py health
```

输出示例：
```
🏥 API 健康状态报告
============================================================
检测时间: 2025-12-16 15:30:00

模型名             状态         响应时间         上次状态
------------------------------------------------------------
AnyRouter       ✅ 健康       0.52s        healthy
Gemai           ✅ 健康       0.54s        healthy
88Code          ✅ 健康       0.62s        healthy
FoxCode         ❌ 不可用     N/A          healthy
------------------------------------------------------------
总计: 5 个健康, 1 个不可用
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

**使环境变量生效的方式：**

1. **推荐方式：使用 Shell Wrapper**
   ```bash
   # 设置别名
   echo "alias claude-switch='source $(pwd)/switch_model.sh'" >> ~/.bashrc
   source ~/.bashrc

   # 切换模型后立即在当前会话生效
   claude-switch Gemai
   ```

2. **传统方式：手动 source**
   ```bash
   python set_model.py Gemai
   source ~/.bashrc  # 手动执行使变量生效
   ```

### Windows

使用 `setx` 命令设置用户环境变量，需要重新打开命令行窗口生效。

## 高级功能

### 智能工作流

- **current 命令优化**: 检测当前模型时，如果发现不可用，会自动显示所有模型状态，方便快速切换
- **自动重载**: 切换模型后自动更新当前会话的环境变量，无需手动 source
- **并发测试**: status 和交互模式使用并发测试，大幅提升检测速度
- **实时进度**: 测试多个 API 时显示实时进度条，清晰展示进度

### API 测试准确性

- 🆕 **热身请求技术**: 发送两次请求，第一次用于建立连接池，第二次测速更准确
- **流式 API 测试**: 优先使用流式 API 测试（更快更准确）
- **连接性优先**: 只要收到响应就认为 API 在线（关注连接性而非请求成功与否）
- **SSL 自动处理**: 自动处理 SSL 证书问题
- 支持自定义超时时间（默认 5 秒）

### 配置管理增强

- **自动备份**: 支持配置文件备份，自动生成时间戳
- **一键恢复**: 可快速从备份恢复配置
- **信息脱敏**: 显示配置时自动脱敏 Token 信息，保护安全
- **配置预览**: 可查看所有配置信息而不泄露完整 Token
- 🆕 **深度链接分享**: 生成 `claude-switch://` 协议链接，一键分享和导入配置
- **配置导入导出**: 支持配置的跨设备迁移和分享

### 安全功能

- **配置加密**: 使用 PBKDF2 密钥派生 + Fernet 对称加密
- **480000 次迭代**: 符合 OWASP 推荐的安全标准
- **Token 脱敏**: 所有输出中自动隐藏敏感信息

## 常见问题

### Q: 为什么某些 API 显示不可用？

A: 可能的原因：
1. API 服务暂时不可用
2. Token 已过期
3. 网络连接问题
4. API 地址错误

使用 `python set_model.py health` 查看详细健康状态。

### Q: 切换后环境变量没生效？

A:
- **Linux/macOS - 推荐方案（使用 Shell Wrapper）**:
  1. 首次设置别名：`echo "alias claude-switch='source $(pwd)/switch_model.sh'" >> ~/.bashrc`
  2. 重新加载配置：`source ~/.bashrc`
  3. 之后使用 `claude-switch` 命令切换，环境变量会立即生效，无需手动 source
- **Linux/macOS - 传统方案**: 使用 `python set_model.py` 切换后，需要手动执行 `source ~/.bashrc` 使环境变量在当前会话生效
- **Windows**: 需要重新打开命令行窗口

### Q: 如何备份配置？

A:
- **快速备份**: `python set_model.py backup`
- 备份文件会保存到 `backups/` 目录，文件名包含时间戳
- **从备份恢复**: `python set_model.py restore backups/model_config_YYYYMMDD_HHMMSS.json`

### Q: 忘记加密密码怎么办？

A: 加密密码无法找回。建议：
1. 定期备份未加密的配置文件
2. 使用密码管理器保存密码
3. 如果忘记密码，需要重新配置所有 API

### Q: 如何在多台设备间同步配置？

A: 使用导入导出功能：
1. 在源设备导出：`python set_model.py export config.json --with-tokens`
2. 将文件传输到目标设备
3. 在目标设备导入：`python set_model.py import config.json`

## 性能优化

### 并发测试性能

- 使用多线程并发测试（最多 10 个并发）
- 相比串行测试，速度提升 **3-5 倍**
- 6 个 API 的测试时间从 ~30 秒降至 ~6 秒

### 进度可视化

- 实时进度条显示测试进度
- 清晰的视觉反馈，提升用户体验

## 开发计划

- [x] 并发测试优化
- [x] 进度条显示
- [x] 配置文件备份与恢复
- [x] 敏感信息脱敏显示
- [x] 支持配置文件加密
- [x] 添加 API 使用统计
- [x] 支持自定义测试超时时间
- [x] 添加 API 健康监控和自动切换
- [x] 支持配置文件导入导出
- [ ] Web UI 界面
- [ ] 定时健康检查和告警
- [ ] API 负载均衡

## 许可证

MIT License
