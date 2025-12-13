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
from datetime import datetime
import shutil

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

    def __init__(self, config_path: str = "model_config.json"):
        self.config_path = config_path
        self.system = platform.system()
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """加载配置文件"""
        config_file = Path(self.config_path)
        if not config_file.exists():
            print(f"❌ 错误：配置文件 {self.config_path} 不存在")
            sys.exit(1)

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

    def set_linux_env(self, env_vars: Dict[str, str]):
        """设置 Linux/macOS 环境变量"""
        shell_config = self._get_shell_config()
        print(f"🐧 Linux/macOS 系统检测到")
        print(f"📝 配置文件：{shell_config}")

        for key, value in env_vars.items():
            try:
                if self._is_var_in_file(shell_config, key):
                    self._update_var_in_file(shell_config, key, value)
                    print(f"🔄 已更新：{key}={value}")
                else:
                    with open(shell_config, "a", encoding="utf-8") as f:
                        f.write(f'\nexport {key}="{value}"\n')
                    print(f"✅ 已添加：{key}={value}")
            except Exception as e:
                print(f"❌ 错误：无法设置 {key} - {e}")

        print(f"\n⚠️  请运行以下命令使环境变量立即生效：")
        print(f"  source {shell_config}")
        print(f"\n或者重新打开终端窗口")

    def set_env_variables(self, env_vars: Dict[str, str]):
        """根据系统类型设置环境变量"""
        if self.system == "Windows":
            self.set_windows_env(env_vars)
        elif self.system in ["Linux", "Darwin"]:  # Darwin 是 macOS
            self.set_linux_env(env_vars)
        else:
            print(f"❌ 不支持的操作系统: {self.system}")
            sys.exit(1)

    def test_api(self, model_name: str, timeout: int = 10) -> Tuple[bool, Optional[float]]:
        """测试API连接（参考cc-switch实现）
        返回: (是否可用, 响应时间)
        """
        if model_name not in self.config:
            return False, None

        config = self.config[model_name]
        base_url = config.get("ANTHROPIC_BASE_URL", "")
        token = config.get("ANTHROPIC_AUTH_TOKEN", "")

        if not base_url or not token:
            return False, None

        # 方法1: 尝试流式请求（更快更准确）
        try:
            start_time = time.time()
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
                    "messages": [{"role": "user", "content": "hi"}],
                    "stream": True
                },
                timeout=timeout,
                verify=False,
                stream=True
            )

            response_time = time.time() - start_time
            if response.status_code == 200:
                response.close()
                return True, response_time
        except:
            pass

        # 方法2: 回退到非流式请求
        try:
            start_time = time.time()
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
                    "messages": [{"role": "user", "content": "hi"}]
                },
                timeout=timeout,
                verify=False
            )

            response_time = time.time() - start_time
            # 只要收到响应就认为API在线
            return True, response_time

        except requests.exceptions.Timeout:
            return False, None
        except requests.exceptions.ConnectionError:
            return False, None
        except Exception:
            return False, None

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

    def list_models(self, show_status: bool = False):
        """列出所有可用模型"""
        print("📋 可用模型列表：")

        if show_status:
            # 使用并发测试
            results = self.test_apis_concurrent(show_progress=True)

            print(f"\n{'序号':<4} {'模型名':<15} {'状态':<8} {'响应时间':<10}")
            print("-" * 45)

            for i, model in enumerate(self.config.keys(), 1):
                status, resp_time = results.get(model, (False, None))
                status_icon = "✅" if status else "❌"
                time_str = f"{resp_time:.2f}s" if resp_time else "N/A"
                print(f"{i:<4} {model:<15} {status_icon:<8} {time_str:<10}")
        else:
            for i, model in enumerate(self.config.keys(), 1):
                print(f"  {i}. {model}")

    def switch_model(self, model_name: str, auto_reload: bool = True):
        """切换到指定模型"""
        if model_name not in self.config:
            print(f"❌ 错误：模型 '{model_name}' 未配置")
            print(f"\n可用模型：{', '.join(self.config.keys())}")
            sys.exit(1)

        print(f"🔄 正在切换至模型：{model_name}")
        print("=" * 50)
        self.set_env_variables(self.config[model_name])
        print("=" * 50)
        print(f"✅ 模型切换完成！")

        # 自动重载环境变量
        if auto_reload and self.system in ["Linux", "Darwin"]:
            shell_config = self._get_shell_config()
            print(f"\n🔄 正在重载环境变量...")
            try:
                # 更新当前进程的环境变量
                for key, value in self.config[model_name].items():
                    os.environ[key] = value
                print(f"✅ 环境变量已在当前会话中生效")
            except Exception as e:
                print(f"⚠️  警告：自动重载失败 - {e}")

    def interactive_mode(self):
        """交互式选择模型"""
        while True:
            print("\n" + "=" * 70)
            print("🎯 Claude 模型切换工具 - 交互模式")
            print("=" * 70)

            # 显示当前模型
            current = self.get_current_model()
            if current:
                print(f"📍 当前模型: {current}")
            else:
                print(f"📍 当前模型: 未设置")

            print()
            # 使用并发测试
            models = list(self.config.keys())
            results = self.test_apis_concurrent(models, show_progress=True)

            print(f"\n{'序号':<4} {'模型名':<15} {'状态':<8} {'响应时间':<10}")
            print("-" * 45)

            for i, model in enumerate(models, 1):
                status, resp_time = results.get(model, (False, None))
                status_icon = "✅" if status else "❌"
                time_str = f"{resp_time:.2f}s" if resp_time else "N/A"

                # 标记当前使用的模型
                marker = " ← 当前" if model == current else ""
                print(f"{i:<4} {model:<15} {status_icon:<8} {time_str:<10}{marker}")

            print("\n" + "-" * 70)
            print("输入序号切换模型，或输入 'q' 退出")

            try:
                choice = input("\n请选择: ").strip()

                if choice.lower() == 'q':
                    print("👋 退出")
                    break

                if not choice.isdigit():
                    print("❌ 请输入有效的序号")
                    continue

                index = int(choice) - 1
                if 0 <= index < len(models):
                    self.switch_model(models[index])
                    input("\n按回车继续...")
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

    def _save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
            sys.exit(1)

    def backup_config(self, backup_dir: str = "backups") -> str:
        """备份配置文件"""
        try:
            # 创建备份目录
            Path(backup_dir).mkdir(exist_ok=True)

            # 生成备份文件名（带时间戳）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{backup_dir}/model_config_{timestamp}.json"

            # 复制配置文件
            shutil.copy2(self.config_path, backup_file)
            return backup_file
        except Exception as e:
            print(f"❌ 备份配置失败: {e}")
            return ""

    def restore_config(self, backup_file: str):
        """从备份恢复配置"""
        try:
            if not os.path.exists(backup_file):
                print(f"❌ 备份文件不存在: {backup_file}")
                return False

            shutil.copy2(backup_file, self.config_path)
            self.config = self._load_config()
            print(f"✅ 配置已从备份恢复: {backup_file}")
            return True
        except Exception as e:
            print(f"❌ 恢复配置失败: {e}")
            return False

    def test_apis_concurrent(self, models: List[str] = None, show_progress: bool = True) -> Dict[str, Tuple[bool, Optional[float]]]:
        """并发测试多个API"""
        if models is None:
            models = list(self.config.keys())

        results = {}
        completed = 0
        total = len(models)

        if show_progress:
            print_progress_bar(0, total, prefix="🔍 测试进度")

        with ThreadPoolExecutor(max_workers=5) as executor:
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


def main():
    manager = EnvManager()

    # 没有参数时启动交互模式
    if len(sys.argv) < 2:
        manager.interactive_mode()
        sys.exit(0)

    command = sys.argv[1]

    # 列出所有模型
    if command in ["list", "ls", "--list", "-l"]:
        manager.list_models()
        sys.exit(0)

    # 列出所有模型并显示状态
    if command in ["status", "st", "--status", "-s"]:
        manager.list_models(show_status=True)
        sys.exit(0)

    # 显示当前模型（优化版：如果不可用自动显示所有模型状态）
    if command in ["current", "cur", "--current", "-c"]:
        current = manager.get_current_model()
        if current:
            print(f"📍 当前模型: {current}")
            print(f"\n🔍 正在检测状态...")
            # 测试当前模型状态
            status, resp_time = manager.test_api(current)
            if status:
                print(f"✅ 状态: 可用")
                print(f"⚡ 响应时间: {resp_time:.2f}s")
            else:
                print(f"❌ 状态: 不可用")
                print(f"\n💡 正在检测其他可用模型...")
                print("=" * 45)
                manager.list_models(show_status=True)
        else:
            print("📍 当前模型: 未设置")
            print(f"\n💡 显示所有可用模型:")
            print("=" * 70)
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

    # 备份配置
    if command in ["backup", "bak", "--backup", "-b"]:
        backup_file = manager.backup_config()
        if backup_file:
            print(f"✅ 配置已备份至: {backup_file}")
        sys.exit(0)

    # 恢复配置
    if command in ["restore", "res", "--restore"]:
        if len(sys.argv) < 3:
            print("💡 用法: python set_model.py restore <备份文件路径>")
            print("提示: 备份文件位于 backups/ 目录")
            sys.exit(1)
        manager.restore_config(sys.argv[2])
        sys.exit(0)

    # 显示配置信息（脱敏）
    if command in ["show", "info", "--show", "-i"]:
        print("📋 当前配置信息：\n")
        for model_name, config in manager.config.items():
            print(f"模型: {model_name}")
            print(f"  BASE_URL: {config.get('ANTHROPIC_BASE_URL', 'N/A')}")
            token = config.get('ANTHROPIC_AUTH_TOKEN', '')
            print(f"  TOKEN: {mask_sensitive_info(token, 10)}")
            print()
        sys.exit(0)

    # 帮助信息
    if command in ["help", "--help", "-h"]:
        print("🎯 Claude 模型切换工具")
        print("\n常用命令:")
        print("  python set_model.py                    # 交互模式（推荐）")
        print("  python set_model.py <模型名>           # 快速切换模型")
        print("  python set_model.py current            # 查看当前模型状态")
        print("  python set_model.py status             # 查看所有模型状态")
        print("\n管理命令:")
        print("  python set_model.py add <名称> <URL> [TOKEN]     # 添加模型")
        print("  python set_model.py update <名称> --url <URL>    # 更新URL")
        print("  python set_model.py update <名称> --token <TOKEN> # 更新TOKEN")
        print("  python set_model.py remove <模型名>              # 删除模型")
        print("  python set_model.py show               # 显示配置信息（脱敏）")
        print("  python set_model.py backup             # 备份配置文件")
        print("  python set_model.py restore <文件>     # 从备份恢复配置")
        print("\n其他命令:")
        print("  python set_model.py list               # 列出所有模型（不测试）")
        print("  python set_model.py interactive        # 交互模式")
        print("\n命令别名:")
        print("  list: ls, -l        status: st, -s      current: cur, -c")
        print("  add: -a             update: up, -u      remove: rm, -r")
        print("  interactive: i, -i  backup: bak, -b     restore: res")
        print("  show: info")
        print("\n💡 提示:")
        print("  - current命令会自动检测当前模型，如果不可用会显示所有模型状态")
        print("  - 交互模式会实时显示所有API的状态和响应速度")
        print("  - status命令使用并发测试，快速获取所有API状态")
        sys.exit(0)

    # 默认：切换模型
    manager.switch_model(command)


if __name__ == "__main__":
    main()
