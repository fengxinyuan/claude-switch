import json
import sys
import subprocess
import os
import platform
import re
import time
import random
import requests
import urllib3
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from concurrent.futures import ThreadPoolExecutor, as_completed

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def mask_sensitive_info(value: str, show_chars: int = 8) -> str:
    """脱敏显示敏感信息"""
    if not value or len(value) <= show_chars:
        return "*" * len(value)
    return value[:show_chars] + "*" * (len(value) - show_chars)


def display_width(text: str) -> int:
    """计算字符串的实际显示宽度（考虑中文和emoji）"""
    width = 0
    for char in text:
        # ASCII字符宽度为1
        if ord(char) < 128:
            width += 1
        # emoji和中文等宽字符宽度为2
        else:
            width += 2
    return width


def pad_to_width(text: str, target_width: int) -> str:
    """填充字符串到指定显示宽度"""
    current_width = display_width(text)
    if current_width >= target_width:
        return text
    return text + ' ' * (target_width - current_width)


def print_progress_bar(current: int, total: int, prefix: str = "", length: int = 30):
    """打印进度条"""
    percent = current / total
    filled = int(length * percent)
    bar = "█" * filled + "░" * (length - filled)
    sys.stdout.write(f"\r{prefix} [{bar}] {current}/{total} ({percent*100:.0f}%)")
    sys.stdout.flush()
    if current == total:
        print()  # 完成后换行


class EnvManager:
    """环境变量管理器"""

    # 默认超时时间（秒）
    DEFAULT_TIMEOUT = 8

    # 全局配置目录
    DEFAULT_CONFIG_DIR = os.path.expanduser("~/.config/claude-switch")
    DEFAULT_CONFIG_FILE = "config.json"

    def __init__(self, config_path: str = None, timeout: int = None):
        # 如果没有指定配置文件，使用全局配置
        if config_path is None:
            config_path = os.path.join(self.DEFAULT_CONFIG_DIR, self.DEFAULT_CONFIG_FILE)

        self.config_path = config_path
        self.config_dir = os.path.dirname(config_path)
        self.system = platform.system()
        self.timeout = timeout or self.DEFAULT_TIMEOUT

        # 确保配置目录存在
        self._ensure_config_dir()

        self.config = self._load_config()

    def _ensure_config_dir(self):
        """确保配置目录存在"""
        os.makedirs(self.config_dir, exist_ok=True)

    def _load_config(self) -> dict:
        """加载配置文件"""
        config_file = Path(self.config_path)
        if not config_file.exists():
            # 如果配置文件不存在，尝试从本地迁移
            local_config = Path("model_config.json")
            if local_config.exists():
                print(f"💡 检测到本地配置文件，正在迁移到全局配置目录...")
                try:
                    import shutil
                    shutil.copy2(local_config, config_file)
                    print(f"✅ 配置已迁移到: {config_file}")
                    print(f"💡 现在可以在任何目录使用 claude-switch 命令了！")
                except Exception as e:
                    print(f"⚠️  迁移失败: {e}")
            else:
                # 创建空配置文件
                print(f"💡 首次使用，正在创建配置文件: {config_file}")
                with config_file.open("w", encoding="utf-8") as f:
                    json.dump({}, f, indent=2)
                print(f"✅ 配置文件已创建")
                print(f"💡 使用 'claude-switch add' 添加 API 配置")
                return {}

        try:
            with config_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ 错误：配置文件格式不正确 - {e}")
            sys.exit(1)

    def _get_shell_config(self) -> Optional[str]:
        """获取 shell 配置文件路径"""
        home = os.path.expanduser("~")

        # 检测常见的 shell 配置文件
        shell_configs = [
            f"{home}/.zshrc",  # zsh
            f"{home}/.bashrc",  # bash
            f"{home}/.bash_profile",  # bash (macOS)
            f"{home}/.profile"  # POSIX shell
        ]

        for config in shell_configs:
            if os.path.exists(config):
                return config

        # 默认使用 .bashrc
        return f"{home}/.bashrc"

    def _is_var_in_file(self, filepath: str, var_name: str) -> bool:
        """检查环境变量是否已在文件中"""
        if not os.path.exists(filepath):
            return False

        pattern = re.compile(rf'^\s*export\s+{re.escape(var_name)}\s*=', re.MULTILINE)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            return bool(pattern.search(content))

    def _update_var_in_file(self, filepath: str, var_name: str, var_value: str):
        """更新文件中的环境变量"""
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        pattern = re.compile(rf'^\s*export\s+{re.escape(var_name)}\s*=')
        updated = False

        with open(filepath, 'w', encoding='utf-8') as f:
            for line in lines:
                if pattern.match(line):
                    f.write(f'export {var_name}="{var_value}"\n')
                    updated = True
                else:
                    f.write(line)

            # 如果没有找到，追加到文件末尾
            if not updated:
                f.write(f'\nexport {var_name}="{var_value}"\n')

    def set_windows_env(self, env_vars: Dict[str, str]):
        """设置 Windows 环境变量"""
        print("🪟 Windows 系统检测到")
        for key, value in env_vars.items():
            try:
                # 使用 setx 设置用户环境变量
                result = subprocess.run(
                    ["setx", key, value],
                    shell=True,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print(f"✅ 已设置：{key}={value}")
                else:
                    print(f"⚠️  警告：设置 {key} 失败 - {result.stderr}")
            except Exception as e:
                print(f"❌ 错误：无法设置 {key} - {e}")

        print("\n⚠️  注意：需要重新打开命令行窗口才能生效")

    def set_linux_env(self, env_vars: Dict[str, str], silent: bool = False):
        """设置 Linux/macOS 环境变量

        Args:
            env_vars: 环境变量字典
            silent: 是否静默模式（不输出冗余信息）
        """
        shell_config = self._get_shell_config()

        if not silent:
            print(f"📝 配置文件：{shell_config}")

        for key, value in env_vars.items():
            try:
                if self._is_var_in_file(shell_config, key):
                    self._update_var_in_file(shell_config, key, value)
                    if not silent:
                        print(f"✓ {key}")
                else:
                    with open(shell_config, "a", encoding="utf-8") as f:
                        f.write(f'\nexport {key}="{value}"\n')
                    if not silent:
                        print(f"✓ {key}")
            except Exception as e:
                print(f"❌ 错误：无法设置 {key} - {e}")

    def set_env_variables(self, env_vars: Dict[str, str], silent: bool = False):
        """根据系统类型设置环境变量

        Args:
            env_vars: 环境变量字典
            silent: 是否静默模式
        """
        if self.system == "Windows":
            self.set_windows_env(env_vars)
        elif self.system in ["Linux", "Darwin"]:  # Darwin 是 macOS
            self.set_linux_env(env_vars, silent=silent)
        else:
            print(f"❌ 不支持的操作系统: {self.system}")
            sys.exit(1)

    def test_api(self, model_name: str, timeout: int = None, use_warmup: bool = False) -> Tuple[bool, Optional[float], Optional[str]]:
        """测试API连接（优化版本）

        Args:
            model_name: 模型名称
            timeout: 超时时间（秒）
            use_warmup: 是否使用热身请求（已废弃，保留参数兼容性）

        返回: (是否可用, 响应时间, 错误信息)
        """
        if model_name not in self.config:
            return False, None, "配置不存在"

        config = self.config[model_name]
        base_url = config.get("ANTHROPIC_BASE_URL", "")
        token = config.get("ANTHROPIC_AUTH_TOKEN", "")

        if not base_url or not token:
            return False, None, "配置不完整"

        # 使用实例的超时时间或传入的超时时间
        actual_timeout = timeout or self.timeout

        # 实际测速请求
        try:
            start_time = time.time()
            success, error_msg = self._make_test_request(base_url, token, actual_timeout, config)
            response_time = time.time() - start_time

            if success:
                return True, response_time, None
            else:
                return False, None, error_msg

        except requests.exceptions.Timeout:
            return False, None, "连接超时"
        except requests.exceptions.ConnectionError:
            return False, None, "连接失败"
        except Exception as e:
            return False, None, f"未知错误: {str(e)}"

    def _make_test_request(self, base_url: str, token: str, timeout: int, model_config: Dict = None) -> Tuple[bool, Optional[str]]:
        """发送测试请求的内部方法（模拟真实使用场景）

        返回: (是否成功, 错误信息)
        """
        test_url = f"{base_url.rstrip('/')}/v1/messages"

        # 模拟真实开发者查询的测试消息池（避免敏感词，看起来像真实问题）
        test_messages = [
            [{"role": "user", "content": "What's Python?"}],
            [{"role": "user", "content": "Explain REST API"}],
            [{"role": "user", "content": "JSON format basics"}],
            [{"role": "user", "content": "Git diff command"}],
            [{"role": "user", "content": "HTTP status codes"}],
            [{"role": "user", "content": "Define variable"}],
            [{"role": "user", "content": "List methods in Python"}],
            [{"role": "user", "content": "SQL select syntax"}],
            [{"role": "user", "content": "What is a function?"}],
            [{"role": "user", "content": "CSS flexbox"}],
            [{"role": "user", "content": "JavaScript array methods"}],
            [{"role": "user", "content": "Docker basic commands"}],
        ]

        # 真实的浏览器User-Agent池
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        ]

        # 随机选择消息和User-Agent
        messages = random.choice(test_messages)
        user_agent = random.choice(user_agents)

        # 从配置中获取自定义模型名称，如果没有则使用默认值
        model_name = model_config.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929") if model_config else "claude-sonnet-4-5-20250929"

        try:
            # 添加微小随机延迟，避免瞬时大量请求
            time.sleep(random.uniform(0.1, 0.3))

            response = requests.post(
                test_url,
                headers={
                    "x-api-key": token,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                    "user-agent": user_agent,
                    "accept": "application/json",
                },
                json={
                    "model": model_name,
                    "max_tokens": 3,
                    "messages": messages,
                    "stream": True
                },
                timeout=timeout,
                verify=False,
                stream=True
            )

            # 检查响应状态
            if response.status_code != 200:
                try:
                    # 读取响应内容（流式响应需要先读取）
                    content = response.content.decode('utf-8')
                    error_data = json.loads(content)

                    # 尝试多种常见的错误消息路径
                    error_msg = (
                        error_data.get("error", {}).get("message") or
                        error_data.get("message") or
                        error_data.get("error") or
                        content[:200]  # 如果没有标准字段，显示前200字符
                    )
                except Exception as e:
                    # 如果JSON解析失败，尝试显示原始内容
                    try:
                        content = response.content.decode('utf-8')
                        error_msg = content[:200] if content else f"HTTP {response.status_code}"
                    except:
                        error_msg = f"HTTP {response.status_code}"

                response.close()
                return False, error_msg

            # 读取流式响应的前几个chunk，确保连接真实可用
            chunk_count = 0
            max_chunks = 3  # 只读取前3个chunk
            try:
                for line in response.iter_lines():
                    if line:
                        chunk_count += 1
                        if chunk_count >= max_chunks:
                            break
            except Exception as e:
                response.close()
                return False, f"读取响应失败: {str(e)}"

            response.close()

            # 确保至少收到了一些数据
            if chunk_count == 0:
                return False, "未收到响应数据"

            return True, None

        except requests.exceptions.RequestException as e:
            raise  # 让外层处理超时和连接错误

    def get_current_model(self) -> Optional[str]:
        """获取当前使用的模型"""
        current_url = os.environ.get("ANTHROPIC_BASE_URL", "")
        current_token = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")

        if not current_url:
            return None

        for model_name, config in self.config.items():
            if (config.get("ANTHROPIC_BASE_URL") == current_url and
                config.get("ANTHROPIC_AUTH_TOKEN") == current_token):
                return model_name

        return "未知"

    def list_models(self, show_status: bool = False, show_config: bool = False):
        """列出所有可用模型

        Args:
            show_status: 是否显示状态和响应时间
            show_config: 是否显示配置信息（URL和Token）
        """
        current = self.get_current_model()

        if current and current != "未知":
            print(f"当前: {current}\n")

        if show_status:
            # 使用并发测试
            results = self.test_apis_concurrent(show_progress=True)

            # 打印表头（使用自定义宽度对齐）
            print()
            header = f"{pad_to_width('序号', 4)} {pad_to_width('模型名', 20)} {pad_to_width('状态', 8)} {pad_to_width('响应时间', 12)} 说明"
            print(header)
            print("-" * 90)

            for i, model in enumerate(self.config.keys(), 1):
                status, resp_time, error_msg = results.get(model, (False, None, None))
                status_icon = "✅" if status else "❌"
                time_str = f"{resp_time:.2f}s" if resp_time else "N/A"

                # 准备说明信息
                if model == current:
                    info = "⭐ 当前"
                elif not status and error_msg:
                    # 截断过长的错误信息
                    info = error_msg if len(error_msg) <= 38 else error_msg[:35] + "..."
                else:
                    info = ""

                # 使用自定义宽度对齐
                num_str = pad_to_width(str(i), 4)
                model_str = pad_to_width(model, 20)
                status_str = pad_to_width(status_icon, 8)
                time_str_padded = pad_to_width(time_str, 12)

                print(f"{num_str} {model_str} {status_str} {time_str_padded} {info}")

            # 如果需要显示配置信息
            if show_config:
                print("\n" + "=" * 60)
                print("配置信息 (Token 已脱敏)")
                print("=" * 60)
                for model in self.config.keys():
                    config = self.config[model]
                    marker = " ⭐" if model == current else ""
                    print(f"\n{model}{marker}")
                    print(f"  URL:   {config.get('ANTHROPIC_BASE_URL', 'N/A')}")
                    token = config.get('ANTHROPIC_AUTH_TOKEN', '')
                    print(f"  TOKEN: {mask_sensitive_info(token, 10)}")
        else:
            print("📋 可用模型：")
            for i, model in enumerate(self.config.keys(), 1):
                marker = " ⭐" if model == current and current != "未知" else ""
                print(f"  {i}. {model}{marker}")

    def switch_model(self, model_name: str, auto_reload: bool = True):
        """切换到指定模型"""
        if model_name not in self.config:
            print(f"❌ 模型 '{model_name}' 未配置")
            print(f"可用模型：{', '.join(self.config.keys())}")
            sys.exit(1)

        print(f"🔄 切换到：{model_name}")

        # 核心变量（必须保留）
        core_vars = {"ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN"}

        # 收集所有模型配置中的变量名
        all_config_vars = set()
        for model_config in self.config.values():
            all_config_vars.update(model_config.keys())

        # 清除旧模型配置中的变量（除了核心变量和新模型的变量）
        if self.system in ["Linux", "Darwin"]:
            shell_config = self._get_shell_config()
            if os.path.exists(shell_config):
                with open(shell_config, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                # 识别需要删除的行
                new_lines = []
                vars_removed = []

                for line in lines:
                    # 检查是否是配置文件中的变量
                    match = re.match(r'^\s*export\s+(\w+)\s*=', line)
                    if match:
                        var_name = match.group(1)
                        # 只删除：是配置中的变量 且 不是核心变量 且 不在新模型配置中
                        if (var_name in all_config_vars and
                            var_name not in core_vars and
                            var_name not in self.config[model_name]):
                            vars_removed.append(var_name)
                            continue  # 跳过这一行（删除）
                    new_lines.append(line)

                # 如果有变量需要删除，写回文件
                if vars_removed:
                    with open(shell_config, 'w', encoding='utf-8') as f:
                        f.writelines(new_lines)
                    # 清除当前进程的环境变量
                    for var in vars_removed:
                        if var in os.environ:
                            del os.environ[var]

        # 静默模式设置环境变量（不输出冗余信息）
        self.set_env_variables(self.config[model_name], silent=True)

        # 自动重载环境变量
        if auto_reload and self.system in ["Linux", "Darwin"]:
            try:
                # 更新当前进程的环境变量
                for key, value in self.config[model_name].items():
                    os.environ[key] = value
                print(f"✅ 已切换到 {model_name}")
            except Exception as e:
                print(f"⚠️ 警告：{e}")
                print(f"✅ 配置已更新到 shell 文件")

    def interactive_select_model(self, action_name: str = "操作") -> Optional[str]:
        """交互式选择模型（用于编辑等操作）

        Args:
            action_name: 操作名称（如"编辑"、"删除"等）

        Returns:
            选择的模型名称，如果取消则返回 None
        """
        if not self.config:
            print("❌ 还没有配置任何模型")
            print("💡 使用 'claude-switch add' 添加模型配置")
            return None

        print(f"\n🎯 选择要{action_name}的模型")
        print("=" * 60)

        # 显示当前模型
        current = self.get_current_model()
        if current and current != "未知":
            print(f"当前: {current}\n")

        # 列出所有模型
        models = list(self.config.keys())
        print(f"{'序号':<4} {'模型名':<25} {'标记':<10}")
        print("-" * 60)

        for i, model in enumerate(models, 1):
            marker = "⭐ 当前" if model == current and current != "未知" else ""
            print(f"{i:<4} {model:<25} {marker:<10}")

        print("-" * 60)
        print("💡 输入序号选择模型，或输入 'q' 退出")

        while True:
            try:
                choice = input("\n请选择: ").strip()

                if choice.lower() == 'q':
                    print("👋 取消操作")
                    return None

                if not choice.isdigit():
                    print("❌ 请输入有效的序号")
                    continue

                index = int(choice) - 1
                if 0 <= index < len(models):
                    selected = models[index]
                    print(f"✅ 已选择: {selected}")
                    return selected
                else:
                    print("❌ 序号超出范围")

            except KeyboardInterrupt:
                print("\n\n👋 取消操作")
                return None
            except Exception as e:
                print(f"❌ 错误: {e}")

    def interactive_mode(self):
        """交互式选择模型"""
        print("\n🎯 Claude 模型切换工具")
        print("=" * 60)

        # 显示当前模型
        current = self.get_current_model()
        if current and current != "未知":
            print(f"当前: {current}\n")
        else:
            print(f"当前: 未设置\n")
        # 使用并发测试
        models = list(self.config.keys())
        results = self.test_apis_concurrent(models, show_progress=True)

        # 打印表头（使用自定义宽度对齐）
        print()
        header = f"{pad_to_width('序号', 4)} {pad_to_width('模型名', 20)} {pad_to_width('状态', 8)} {pad_to_width('响应时间', 12)} 说明"
        print(header)
        print("-" * 90)

        for i, model in enumerate(models, 1):
            status, resp_time, error_msg = results.get(model, (False, None, None))
            status_icon = "✅" if status else "❌"
            time_str = f"{resp_time:.2f}s" if resp_time else "N/A"

            # 准备说明信息
            if model == current and current != "未知":
                info = "⭐ 当前启用"
            elif not status and error_msg:
                # 截断过长的错误信息
                info = error_msg if len(error_msg) <= 38 else error_msg[:35] + "..."
            else:
                info = ""

            # 使用自定义宽度对齐
            num_str = pad_to_width(str(i), 4)
            model_str = pad_to_width(model, 20)
            status_str = pad_to_width(status_icon, 8)
            time_str_padded = pad_to_width(time_str, 12)

            print(f"{num_str} {model_str} {status_str} {time_str_padded} {info}")

        print("\n" + "-" * 70)
        print("输入序号切换模型，输入 'r' 刷新状态，或输入 'q' 退出")

        while True:
            try:
                choice = input("\n请选择: ").strip()

                if choice.lower() == 'q':
                    print("👋 退出")
                    break

                if choice.lower() == 'r':
                    # 刷新状态，递归调用
                    return self.interactive_mode()

                if not choice.isdigit():
                    print("❌ 请输入有效的序号")
                    continue

                index = int(choice) - 1
                if 0 <= index < len(models):
                    self.switch_model(models[index])
                    print("\n✅ 切换完成！")
                    break  # 切换成功后直接退出
                else:
                    print("❌ 序号超出范围")

            except KeyboardInterrupt:
                print("\n\n👋 退出")
                break
            except Exception as e:
                print(f"❌ 错误: {e}")

    def add_model(self, name: str, base_url: str, token: str):
        """添加新模型配置"""
        if name in self.config:
            print(f"⚠️  模型 '{name}' 已存在，是否覆盖？(y/n): ", end="")
            if input().strip().lower() != 'y':
                print("❌ 取消添加")
                return

        self.config[name] = {
            "ANTHROPIC_BASE_URL": base_url,
            "ANTHROPIC_AUTH_TOKEN": token
        }

        self._save_config()
        print(f"✅ 模型 '{name}' 已添加")

    def update_model(self, name: str, base_url: Optional[str] = None, token: Optional[str] = None):
        """更新模型配置"""
        if name not in self.config:
            print(f"❌ 模型 '{name}' 不存在")
            print(f"提示: 使用 'add' 命令添加新模型")
            return

        # 在修改配置之前先检查是否是当前模型
        current = self.get_current_model()
        is_current_model = (name == current)

        if base_url:
            self.config[name]["ANTHROPIC_BASE_URL"] = base_url
            print(f"✅ 已更新 BASE_URL")

        if token:
            self.config[name]["ANTHROPIC_AUTH_TOKEN"] = token
            print(f"✅ 已更新 TOKEN")

        if not base_url and not token:
            print("❌ 请至少提供一个要更新的参数")
            return

        self._save_config()
        print(f"✅ 模型 '{name}' 配置已更新")

        # 检查是否更新了当前使用的模型，自动重载
        if is_current_model:
            print(f"\n💡 检测到更新了当前使用的模型，正在自动重载...")
            # 更新shell配置文件和当前进程环境变量
            self.set_env_variables(self.config[name], silent=True)
            if self.system in ["Linux", "Darwin"]:
                try:
                    # 更新当前进程的环境变量
                    for key, value in self.config[name].items():
                        os.environ[key] = value
                    print(f"✅ 环境变量已更新")
                except Exception as e:
                    print(f"⚠️ 警告：{e}")

    def remove_model(self, name: str):
        """删除模型配置"""
        if name not in self.config:
            print(f"❌ 模型 '{name}' 不存在")
            return

        print(f"⚠️  确认删除模型 '{name}'？(y/n): ", end="")
        if input().strip().lower() != 'y':
            print("❌ 取消删除")
            return

        del self.config[name]
        self._save_config()
        print(f"✅ 模型 '{name}' 已删除")

    def rename_model(self, old_name: str, new_name: str) -> bool:
        """重命名模型配置"""
        if old_name not in self.config:
            print(f"❌ 模型 '{old_name}' 不存在")
            return False

        if not new_name.strip():
            print("❌ 新模型名称不能为空")
            return False

        if new_name in self.config and new_name != old_name:
            print(f"⚠️  模型 '{new_name}' 已存在，是否覆盖？(y/n): ", end="")
            if input().strip().lower() != 'y':
                print("❌ 取消重命名")
                return False
            del self.config[new_name]

        self.config[new_name] = self.config.pop(old_name)
        self._save_config()

        current = self.get_current_model()
        print(f"✅ 模型已重命名: {old_name} → {new_name}")

        if old_name == current:
            print(f"💡 当前使用的模型已重命名")
            shell_config = self._get_shell_config()
            if shell_config:
                print(f"   请运行: source {shell_config}")

        return True

    def interactive_edit_model(self, name: str) -> bool:
        """交互式编辑模型配置"""
        if name not in self.config:
            print(f"❌ 模型 '{name}' 不存在")
            return False

        current_name = name  # 跟踪当前名称，可能会被重命名
        config = self.config[name]
        changes = {}
        new_name = None

        print(f"\n✏️  编辑模型配置")
        print("=" * 60)
        print(f"模型名: {current_name}")
        print(f"当前配置:")
        print(f"  URL:   {config.get('ANTHROPIC_BASE_URL', 'N/A')}")
        token = config.get('ANTHROPIC_AUTH_TOKEN', '')
        print(f"  TOKEN: {mask_sensitive_info(token, 10)}")
        print("=" * 60)

        while True:
            try:
                # 显示待保存的修改
                if changes or new_name:
                    print("\n📝 待保存的修改:")
                    if new_name and new_name != name:
                        print(f"  • 新名称: {new_name}")
                    if 'ANTHROPIC_BASE_URL' in changes:
                        print(f"  • 新URL: {changes['ANTHROPIC_BASE_URL']}")
                    if 'ANTHROPIC_AUTH_TOKEN' in changes:
                        print(f"  • 新TOKEN: {mask_sensitive_info(changes['ANTHROPIC_AUTH_TOKEN'], 10)}")

                print("\n请选择要编辑的内容:")
                print("  1. 编辑URL地址")
                print("  2. 编辑API Token")
                print("  3. 重命名模型")
                print("  0. 保存并退出")
                print("  q. 取消操作")

                choice = input("\n请选择: ").strip().lower()

                if choice == 'q':
                    print("❌ 取消编辑")
                    return False

                if choice == '0':
                    # 先处理重命名
                    if new_name and new_name != current_name:
                        if new_name in self.config and new_name != current_name:
                            print(f"⚠️  模型 '{new_name}' 已存在，是否覆盖？(y/n): ", end="")
                            if input().strip().lower() != 'y':
                                print("❌ 取消保存")
                                return False
                            del self.config[new_name]

                        # 执行重命名
                        self.config[new_name] = self.config.pop(current_name)
                        current_name = new_name
                        print(f"✅ 模型已重命名为: {new_name}")

                    # 再应用其他修改
                    if changes:
                        return self._apply_model_changes(current_name, changes)
                    elif new_name and new_name != name:
                        # 只有重命名，没有其他修改
                        self._save_config()

                        # 检查是否重命名了当前使用的模型
                        current_model = self.get_current_model()
                        if name == current_model:
                            print(f"💡 当前使用的模型已重命名")
                            shell_config = self._get_shell_config()
                            if shell_config:
                                print(f"   请运行: source {shell_config}")
                        return True
                    else:
                        print("💡 没有进行任何修改")
                        return True

                if choice == '1':
                    new_url = input("新的URL地址: ").strip()
                    if new_url:
                        changes['ANTHROPIC_BASE_URL'] = new_url
                        print("✅ URL已记录（保存后生效）")
                    else:
                        print("❌ URL不能为空")

                elif choice == '2':
                    new_token = input("新的API Token: ").strip()
                    if new_token:
                        changes['ANTHROPIC_AUTH_TOKEN'] = new_token
                        print("✅ TOKEN已记录（保存后生效）")
                    else:
                        print("❌ TOKEN不能为空")

                elif choice == '3':
                    print(f"当前名称: {current_name}")
                    input_name = input("新的模型名称: ").strip()
                    if input_name:
                        if input_name == current_name:
                            print("💡 名称未改变")
                        else:
                            new_name = input_name
                            print(f"✅ 新名称已记录: {new_name}（保存后生效）")
                    else:
                        print("❌ 名称不能为空")

                else:
                    print("❌ 无效选择，请输入 0-3 或 q")

            except KeyboardInterrupt:
                print("\n\n❌ 取消编辑")
                return False
            except Exception as e:
                print(f"❌ 错误: {e}")

    def edit_model(self, name: str, base_url: Optional[str] = None,
                   token: Optional[str] = None, new_name: Optional[str] = None,
                   interactive: bool = False):
        """编辑模型配置（支持参数和交互两种模式）"""
        if name not in self.config:
            print(f"❌ 模型 '{name}' 不存在")
            return

        # 如果有参数且非强制交互，直接更新
        if (base_url or token or new_name) and not interactive:
            # 处理重命名
            if new_name and new_name != name:
                # 使用 rename_model 处理重命名
                if not self.rename_model(name, new_name):
                    return
                # 重命名成功后，更新 name 为新名称
                name = new_name

            # 处理其他字段更新
            if base_url or token:
                self.update_model(name, base_url, token)
            return

        # 进入交互编辑
        self.interactive_edit_model(name)

    def setup_alias(self):
        """自动配置 claude-switch 别名"""
        if self.system not in ["Linux", "Darwin"]:
            print("❌ 此功能仅支持 Linux/macOS 系统")
            return False

        shell_config = self._get_shell_config()
        if not shell_config:
            print("❌ 无法检测到 shell 配置文件")
            return False

        # 获取脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        wrapper_script = os.path.join(script_dir, "switch_model.sh")

        # 检查 wrapper 脚本是否存在
        if not os.path.exists(wrapper_script):
            print(f"❌ 找不到 wrapper 脚本: {wrapper_script}")
            return False

        # 生成别名命令
        alias_line = f"alias claude-switch='source {wrapper_script}'"

        # 检查别名是否已经存在
        try:
            with open(shell_config, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'alias claude-switch=' in content:
                    print(f"✅ 别名已存在于 {shell_config}")
                    print(f"   当前配置: {alias_line}")
                    print(f"\n💡 请运行以下命令使别名生效：")
                    print(f"   source {shell_config}")
                    return True
        except Exception as e:
            print(f"❌ 读取配置文件失败: {e}")
            return False

        # 添加别名
        try:
            with open(shell_config, 'a', encoding='utf-8') as f:
                f.write(f'\n# Claude Switch - 模型切换工具别名\n')
                f.write(f'{alias_line}\n')

            print(f"✅ 别名已添加到 {shell_config}")
            print(f"   配置内容: {alias_line}")
            print(f"\n💡 请运行以下命令使别名立即生效：")
            print(f"   source {shell_config}")
            print(f"\n🎯 之后就可以使用以下命令：")
            print(f"   claude-switch              # 交互模式")
            print(f"   claude-switch <模型名>     # 切换模型")
            print(f"   claude-switch current      # 查看当前模型")
            return True

        except Exception as e:
            print(f"❌ 添加别名失败: {e}")
            return False

    def _save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
            sys.exit(1)

    def _apply_model_changes(self, name: str, changes: dict) -> bool:
        """应用模型配置变更"""
        try:
            # 在修改配置之前先检查是否是当前模型
            current = self.get_current_model()
            is_current_model = (name == current)

            for key, value in changes.items():
                self.config[name][key] = value
                if key == "ANTHROPIC_BASE_URL":
                    print(f"✅ URL已更新")
                elif key == "ANTHROPIC_AUTH_TOKEN":
                    print(f"✅ TOKEN已更新")

            self._save_config()
            print(f"✅ 配置已保存")

            # 检查是否更新了当前使用的模型，自动重载
            if is_current_model:
                print(f"\n💡 检测到更新了当前使用的模型，正在自动重载...")
                # 更新shell配置文件和当前进程环境变量
                self.set_env_variables(self.config[name], silent=True)
                if self.system in ["Linux", "Darwin"]:
                    try:
                        # 更新当前进程的环境变量
                        for key, value in self.config[name].items():
                            os.environ[key] = value
                        print(f"✅ 环境变量已更新")
                    except Exception as e:
                        print(f"⚠️ 警告：{e}")

            return True
        except Exception as e:
            print(f"❌ 保存失败: {e}")
            return False

    def test_apis_concurrent(self, models: List[str] = None, show_progress: bool = True) -> Dict[str, Tuple[bool, Optional[float], Optional[str]]]:
        """并发测试多个API（带速率限制，避免触发API限流）"""
        if models is None:
            models = list(self.config.keys())

        results = {}
        completed = 0
        total = len(models)

        if show_progress:
            print_progress_bar(0, total, prefix="🔍 测试进度")

        # 并发测试
        max_workers = min(10, len(models))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_model = {
                executor.submit(self.test_api, model): model
                for model in models
            }

            # 收集结果
            for future in as_completed(future_to_model):
                model = future_to_model[future]
                try:
                    status, resp_time, error_msg = future.result()
                    results[model] = (status, resp_time, error_msg)
                except Exception as e:
                    results[model] = (False, None, f"异常: {str(e)}")

                completed += 1
                if show_progress:
                    print_progress_bar(completed, total, prefix="🔍 测试进度")

                # 添加小延迟，避免触发API限流（最后一个不需要延迟）
                if completed < total:
                    time.sleep(0.2)

        return results


def parse_timeout_arg() -> Optional[int]:
    """从命令行参数中解析超时时间"""
    for i, arg in enumerate(sys.argv):
        if arg in ["--timeout", "-t"]:
            if i + 1 < len(sys.argv):
                try:
                    return int(sys.argv[i + 1])
                except ValueError:
                    print(f"⚠️  无效的超时时间: {sys.argv[i + 1]}")
    return None


def main():
    # 解析全局超时参数
    timeout = parse_timeout_arg()
    manager = EnvManager(timeout=timeout)

    # 没有参数时启动交互模式
    if len(sys.argv) < 2:
        manager.interactive_mode()
        sys.exit(0)

    command = sys.argv[1]

    # 查看当前模型状态
    if command in ["status", "st"]:
        current = manager.get_current_model()
        if current:
            print(f"📍 当前模型: {current}")
            print("=" * 60)

            # 显示配置信息
            if current in manager.config:
                config = manager.config[current]
                print(f"API 地址: {config.get('ANTHROPIC_BASE_URL', 'N/A')}")
                token = config.get('ANTHROPIC_AUTH_TOKEN', '')
                print(f"API Token: {mask_sensitive_info(token, 10)}")

            # 测试当前模型状态
            print()
            status, resp_time, error_msg = manager.test_api(current)
            if status:
                print(f"连接状态: ✅ 可用 (响应时间: {resp_time:.2f}s)")
            else:
                print(f"连接状态: ❌ 不可用")
                if error_msg:
                    print(f"错误信息: {error_msg}")
                print(f"\n💡 正在检测其他可用模型...")
                manager.list_models(show_status=True)
        else:
            print("⚠️  当前未设置模型\n")
            print("可用模型:")
            manager.list_models(show_status=True)
        sys.exit(0)

    # 列出所有模型（带状态检测）
    if command in ["list", "ls"]:
        manager.list_models(show_status=True)
        sys.exit(0)

    # 添加模型
    if command in ["add"]:
        if len(sys.argv) < 4:
            print("💡 用法: claude-switch add <模型名> <URL> [TOKEN]")
            sys.exit(1)
        name = sys.argv[2]
        base_url = sys.argv[3]
        token = sys.argv[4] if len(sys.argv) > 4 else input("请输入 TOKEN: ").strip()
        manager.add_model(name, base_url, token)
        sys.exit(0)

    # 删除模型
    if command in ["remove", "rm"]:
        # 如果没有指定模型名，进入交互式选择
        if len(sys.argv) < 3:
            name = manager.interactive_select_model("删除")
            if name is None:
                sys.exit(0)
            manager.remove_model(name)
            sys.exit(0)
        manager.remove_model(sys.argv[2])
        sys.exit(0)

    # 更新模型配置
    if command in ["update", "up"]:
        # 如果没有指定模型名，进入交互式选择
        if len(sys.argv) < 3:
            name = manager.interactive_select_model("编辑")
            if name is None:
                sys.exit(0)
            # 选择完模型后，直接进入交互式编辑
            manager.interactive_edit_model(name)
            sys.exit(0)

        name = sys.argv[2]
        base_url = None
        token = None
        new_name = None
        interactive = False

        # 解析参数
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] in ["-i", "--interactive"]:
                interactive = True
                i += 1
            elif sys.argv[i] in ["--name", "-name"]:
                new_name = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
                i += 2
            elif sys.argv[i] in ["--url", "-url"]:
                base_url = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
                i += 2
            elif sys.argv[i] in ["--token", "-token"]:
                token = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
                i += 2
            else:
                i += 1

        manager.edit_model(name, base_url, token, new_name, interactive)
        sys.exit(0)

    # 显示配置信息（脱敏）
    if command in ["show"]:
        print("📋 配置信息 (Token 已脱敏)\n")
        for model_name, config in manager.config.items():
            marker = " ⭐" if model_name == manager.get_current_model() else ""
            print(f"{model_name}{marker}")
            print(f"  URL:   {config.get('ANTHROPIC_BASE_URL', 'N/A')}")
            token = config.get('ANTHROPIC_AUTH_TOKEN', '')
            print(f"  TOKEN: {mask_sensitive_info(token, 10)}")
            print()
        sys.exit(0)

    # 配置别名
    if command in ["setup"]:
        manager.setup_alias()
        sys.exit(0)

    # 查看配置文件路径
    if command in ["config"]:
        print(f"📁 配置文件路径:")
        print(f"   {manager.config_path}")
        print(f"\n📂 配置目录:")
        print(f"   {manager.config_dir}")
        sys.exit(0)

    # 帮助信息
    if command in ["help"]:
        print("🎯 Claude 模型切换工具\n")
        print("=" * 60)

        print("\n📌 基础操作")
        print("  claude-switch              # 进入交互模式（推荐）")
        print("  claude-switch <模型名>     # 快速切换到指定模型")
        print("  claude-switch status       # 查看当前使用的模型")
        print("  claude-switch list         # 列出所有模型和状态")

        print("\n⚙️  配置管理")
        print("  claude-switch add <名称> <URL> [TOKEN]")
        print("      添加新模型配置")
        print()
        print("  claude-switch update [名称] [选项]")
        print("      更新模型配置（可改所有字段）")
        print("      --name <新名称>    重命名模型")
        print("      --url <URL>        修改API地址")
        print("      --token <TOKEN>    修改API令牌")
        print("      示例:")
        print("        claude-switch update                       # 交互式选择模型后编辑")
        print("        claude-switch update my-model              # 交互式更新指定模型")
        print("        claude-switch update my-model --name new   # 重命名")
        print("        claude-switch update my-model --url https://api.com")
        print()
        print("  claude-switch remove [名称]")
        print("      删除模型配置（不指定名称时交互式选择）")
        print()
        print("  claude-switch show")
        print("      查看所有配置（Token已脱敏）")

        print("\n🔧 工具命令")
        print("  claude-switch setup        # 配置 claude-switch 别名")
        print("  claude-switch config       # 查看配置文件路径")
        print("  claude-switch help         # 显示此帮助信息")

        print("\n⚡ 快捷别名")
        print("  list → ls       status → st      update → up")
        print("  remove → rm")

        print("\n💡 使用提示")
        print("  1. 首次使用运行: claude-switch setup")
        print("  2. 重新加载配置: source ~/.bashrc  (或 ~/.zshrc)")
        print("  3. update 命令功能最全，支持修改所有字段")
        print("  4. 无参数启动进入交互模式，可查看API状态和响应速度")
        print("\n" + "=" * 60)
        sys.exit(0)

    # 默认：切换模型
    manager.switch_model(command)


if __name__ == "__main__":
    main()
