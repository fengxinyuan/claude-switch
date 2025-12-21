import json
import sys
import subprocess
import os
import platform
import re
import time
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
    DEFAULT_TIMEOUT = 5

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

    def test_api(self, model_name: str, timeout: int = None, use_warmup: bool = True) -> Tuple[bool, Optional[float]]:
        """测试API连接（优化版本，支持热身请求）

        Args:
            model_name: 模型名称
            timeout: 超时时间（秒）
            use_warmup: 是否使用热身请求（提高测速准确性）

        返回: (是否可用, 响应时间)
        """
        if model_name not in self.config:
            return False, None

        config = self.config[model_name]
        base_url = config.get("ANTHROPIC_BASE_URL", "")
        token = config.get("ANTHROPIC_AUTH_TOKEN", "")

        if not base_url or not token:
            return False, None

        # 使用实例的超时时间或传入的超时时间
        actual_timeout = timeout or self.timeout

        # 热身请求（绕过首包惩罚，复用连接池）
        if use_warmup:
            try:
                self._make_test_request(base_url, token, actual_timeout)
            except:
                pass  # 热身请求失败不影响后续测试

        # 实际测速请求
        try:
            start_time = time.time()
            self._make_test_request(base_url, token, actual_timeout)
            response_time = time.time() - start_time
            return True, response_time

        except requests.exceptions.Timeout:
            return False, None
        except requests.exceptions.ConnectionError:
            return False, None
        except Exception:
            return False, None

    def _make_test_request(self, base_url: str, token: str, timeout: int):
        """发送测试请求的内部方法"""
        test_url = f"{base_url.rstrip('/')}/v1/messages"
        response = requests.post(
            test_url,
            headers={
                "x-api-key": token,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "1"}],
                "stream": True
            },
            timeout=timeout,
            verify=False,
            stream=True
        )
        response.close()

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

            print(f"\n{'序号':<4} {'模型名':<15} {'状态':<8} {'响应时间':<10} {'标记':<10}")
            print("-" * 60)

            for i, model in enumerate(self.config.keys(), 1):
                status, resp_time = results.get(model, (False, None))
                status_icon = "✅" if status else "❌"
                time_str = f"{resp_time:.2f}s" if resp_time else "N/A"
                marker = "⭐ 当前" if model == current else ""
                print(f"{i:<4} {model:<15} {status_icon:<8} {time_str:<10} {marker:<10}")

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

        print(f"\n{'序号':<4} {'模型名':<15} {'状态':<8} {'响应时间':<10} {'标记':<10}")
        print("-" * 60)

        for i, model in enumerate(models, 1):
            status, resp_time = results.get(model, (False, None))
            status_icon = "✅" if status else "❌"
            time_str = f"{resp_time:.2f}s" if resp_time else "N/A"

            # 标记当前使用的模型（更醒目）
            marker = "⭐ 当前启用" if model == current and current != "未知" else ""
            print(f"{i:<4} {model:<15} {status_icon:<8} {time_str:<10} {marker:<10}")

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

    def test_apis_concurrent(self, models: List[str] = None, show_progress: bool = True) -> Dict[str, Tuple[bool, Optional[float]]]:
        """并发测试多个API"""
        if models is None:
            models = list(self.config.keys())

        results = {}
        completed = 0
        total = len(models)

        if show_progress:
            print_progress_bar(0, total, prefix="🔍 测试进度")

        with ThreadPoolExecutor(max_workers=10) as executor:
            # 提交所有任务
            future_to_model = {
                executor.submit(self.test_api, model): model
                for model in models
            }

            # 收集结果
            for future in as_completed(future_to_model):
                model = future_to_model[future]
                try:
                    status, resp_time = future.result()
                    results[model] = (status, resp_time)
                except Exception as e:
                    results[model] = (False, None)

                completed += 1
                if show_progress:
                    print_progress_bar(completed, total, prefix="🔍 测试进度")

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

    # 显示当前模型状态（包含地址和 API key）
    if command in ["status", "st", "--status", "-s"]:
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
            status, resp_time = manager.test_api(current)
            if status:
                print(f"连接状态: ✅ 可用 (响应时间: {resp_time:.2f}s)")
            else:
                print(f"连接状态: ❌ 不可用")
                print(f"\n💡 正在检测其他可用模型...")
                manager.list_models(show_status=True)
        else:
            print("⚠️  当前未设置模型\n")
            print("可用模型:")
            manager.list_models(show_status=True)
        sys.exit(0)

    # 列出所有模型（带状态检测）
    if command in ["list", "ls", "--list", "-l"]:
        manager.list_models(show_status=True)
        sys.exit(0)

    # 交互模式
    if command in ["interactive", "i", "--interactive", "-i"]:
        manager.interactive_mode()
        sys.exit(0)

    # 添加模型
    if command in ["add", "--add", "-a"]:
        if len(sys.argv) < 4:
            print("💡 用法: python set_model.py add <模型名> <BASE_URL> [TOKEN]")
            sys.exit(1)
        name = sys.argv[2]
        base_url = sys.argv[3]
        token = sys.argv[4] if len(sys.argv) > 4 else input("请输入 TOKEN: ").strip()
        manager.add_model(name, base_url, token)
        sys.exit(0)

    # 更新模型
    if command in ["update", "up", "--update", "-u"]:
        if len(sys.argv) < 3:
            print("💡 用法: python set_model.py update <模型名> [--url <URL>] [--token <TOKEN>]")
            print("示例: python set_model.py update 哈吉米 --url https://new-url.com")
            sys.exit(1)

        name = sys.argv[2]
        base_url = None
        token = None

        # 解析参数
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] in ["--url", "-url"]:
                base_url = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
                i += 2
            elif sys.argv[i] in ["--token", "-token"]:
                token = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
                i += 2
            else:
                i += 1

        manager.update_model(name, base_url, token)
        sys.exit(0)

    # 删除模型
    if command in ["remove", "rm", "--remove", "-r"]:
        if len(sys.argv) < 3:
            print("💡 用法: python set_model.py remove <模型名>")
            sys.exit(1)
        manager.remove_model(sys.argv[2])
        sys.exit(0)

    # 显示配置信息（脱敏）
    if command in ["show", "info", "--show"]:
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
    if command in ["setup-alias", "setup", "--setup-alias"]:
        manager.setup_alias()
        sys.exit(0)

    # 查看配置文件路径
    if command in ["config-path", "path", "--config-path"]:
        print(f"📁 配置文件路径:")
        print(f"   {manager.config_path}")
        print(f"\n📂 配置目录:")
        print(f"   {manager.config_dir}")
        sys.exit(0)

    # 帮助信息
    if command in ["help", "--help", "-h"]:
        print("🎯 Claude 模型切换工具")
        print("\n常用命令:")
        print("  python set_model.py                    # 交互模式（推荐）")
        print("  python set_model.py <模型名>           # 快速切换模型")
        print("  python set_model.py status             # 查看当前模型状态（含地址和Token）")
        print("  python set_model.py list               # 查看所有模型状态")
        print("\n管理命令:")
        print("  python set_model.py add <名称> <URL> [TOKEN]     # 添加模型")
        print("  python set_model.py update <名称> --url <URL>    # 更新URL")
        print("  python set_model.py update <名称> --token <TOKEN> # 更新TOKEN")
        print("  python set_model.py remove <模型名>              # 删除模型")
        print("  python set_model.py show               # 显示配置信息（脱敏）")
        print("\n设置命令:")
        print("  python set_model.py setup-alias        # 自动配置 claude-switch 别名")
        print("  python set_model.py config-path        # 查看配置文件路径")
        print("  python set_model.py interactive        # 显式交互模式")
        print("\n全局参数:")
        print("  --timeout, -t <秒>                     # 设置API测试超时时间（默认5秒）")
        print("\n命令别名:")
        print("  list: ls, -l        status: st, -s")
        print("  add: -a             update: up, -u      remove: rm, -r")
        print("  interactive: i, -i  show: info")
        print("  setup-alias: setup")
        print("\n💡 提示:")
        print("  - 首次使用建议运行 'python set_model.py setup-alias' 配置别名")
        print("  - 配置别名后可直接使用 'claude-switch' 命令，环境变量立即生效")
        print("  - 无参数启动进入交互模式，显示所有API状态和响应速度")
        print("  - status命令显示当前模型的详细信息（地址和Token）")
        print("  - list命令显示所有模型的状态列表")
        print("  - 使用热身请求技术提高测速准确性（自动启用）")
        print("  - 使用 --timeout 参数可以自定义超时时间，如: python set_model.py status -t 10")
        sys.exit(0)

    # 默认：切换模型
    manager.switch_model(command)


if __name__ == "__main__":
    main()
