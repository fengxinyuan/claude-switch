#!/bin/bash
# Claude 模型切换工具 - Shell Wrapper
# 使用此脚本可以让环境变量在当前 shell 会话中立即生效
#
# 使用方法：
#   source switch_model.sh [命令] [参数]
# 或设置别名：
#   alias claude-switch='source /path/to/switch_model.sh'

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/set_model.py"

# 检查 Python 脚本是否存在
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "❌ 错误：找不到 set_model.py"
    return 1 2>/dev/null || exit 1
fi

# 检测 shell 配置文件
if [ -f ~/.zshrc ]; then
    SHELL_CONFIG=~/.zshrc
elif [ -f ~/.bashrc ]; then
    SHELL_CONFIG=~/.bashrc
elif [ -f ~/.bash_profile ]; then
    SHELL_CONFIG=~/.bash_profile
elif [ -f ~/.profile ]; then
    SHELL_CONFIG=~/.profile
else
    SHELL_CONFIG=""
fi

# 保存切换前的环境变量
OLD_BASE_URL="$ANTHROPIC_BASE_URL"
OLD_TOKEN="$ANTHROPIC_AUTH_TOKEN"

# 执行 Python 脚本
python3 "$PYTHON_SCRIPT" "$@"
EXIT_CODE=$?

# 如果 Python 脚本成功执行，重新加载环境变量
if [ $EXIT_CODE -eq 0 ] && [ -n "$SHELL_CONFIG" ]; then
    # 提取并导出 ANTHROPIC 环境变量（使用最新的两行）
    eval "$(grep -E '^export (ANTHROPIC_BASE_URL|ANTHROPIC_AUTH_TOKEN)=' "$SHELL_CONFIG" | tail -2)"

    # 检查环境变量是否发生了变化
    if [ "$OLD_BASE_URL" != "$ANTHROPIC_BASE_URL" ] || [ "$OLD_TOKEN" != "$ANTHROPIC_AUTH_TOKEN" ]; then
        if [ -n "$ANTHROPIC_BASE_URL" ]; then
            echo ""
            echo "✅ 环境变量已在当前会话中生效"
            echo "   BASE_URL: ${ANTHROPIC_BASE_URL:0:50}..."
        fi
    fi
fi

return $EXIT_CODE 2>/dev/null || exit $EXIT_CODE
