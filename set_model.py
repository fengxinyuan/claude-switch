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
import hashlib
import base64
import getpass

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 尝试导入加密库
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


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


class ConfigEncryption:
    """配置文件加密管理器"""

    SALT_FILE = ".config_salt"
    ENCRYPTED_SUFFIX = ".enc"

    def __init__(self, config_dir: str = "."):
        self.config_dir = Path(config_dir)
        self.salt_path = self.config_dir / self.SALT_FILE

    def _get_or_create_salt(self) -> bytes:
        """获取或创建盐值"""
        if self.salt_path.exists():
            with open(self.salt_path, "rb") as f:
                return f.read()
        else:
            salt = os.urandom(16)
            with open(self.salt_path, "wb") as f:
                f.write(salt)
            return salt

    def _derive_key(self, password: str) -> bytes:
        """从密码派生密钥"""
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("加密功能需要安装 cryptography 库: pip install cryptography")

        salt = self._get_or_create_salt()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def encrypt_config(self, config_path: str, password: str) -> str:
        """加密配置文件"""
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("加密功能需要安装 cryptography 库: pip install cryptography")

        key = self._derive_key(password)
        fernet = Fernet(key)

        with open(config_path, "rb") as f:
            data = f.read()

        encrypted_data = fernet.encrypt(data)
        encrypted_path = config_path + self.ENCRYPTED_SUFFIX

        with open(encrypted_path, "wb") as f:
            f.write(encrypted_data)

        return encrypted_path

    def decrypt_config(self, encrypted_path: str, password: str) -> dict:
        """解密配置文件"""
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("加密功能需要安装 cryptography 库: pip install cryptography")

        key = self._derive_key(password)
        fernet = Fernet(key)

        with open(encrypted_path, "rb") as f:
            encrypted_data = f.read()

        try:
            decrypted_data = fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            raise ValueError(f"解密失败，密码可能不正确: {e}")

    def is_encrypted(self, config_path: str) -> bool:
        """检查配置文件是否已加密"""
        return config_path.endswith(self.ENCRYPTED_SUFFIX) or \
               os.path.exists(config_path + self.ENCRYPTED_SUFFIX)


class UsageStats:
    """API 使用统计管理器"""

    STATS_FILE = "usage_stats.json"

    def __init__(self, stats_dir: str = "."):
        self.stats_dir = Path(stats_dir)
        self.stats_path = self.stats_dir / self.STATS_FILE
        self.stats = self._load_stats()

    def _load_stats(self) -> dict:
        """加载统计数据"""
        if self.stats_path.exists():
            try:
                with open(self.stats_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return self._init_stats()
        return self._init_stats()

    def _init_stats(self) -> dict:
        """初始化统计数据"""
        return {
            "total_switches": 0,
            "models": {},
            "daily_usage": {},
            "last_switch": None
        }

    def _save_stats(self):
        """保存统计数据"""
        try:
            with open(self.stats_path, "w", encoding="utf-8") as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  保存统计数据失败: {e}")

    def record_switch(self, model_name: str):
        """记录一次模型切换"""
        today = datetime.now().strftime("%Y-%m-%d")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 更新总切换次数
        self.stats["total_switches"] += 1

        # 更新模型统计
        if model_name not in self.stats["models"]:
            self.stats["models"][model_name] = {
                "switch_count": 0,
                "first_used": now,
                "last_used": now
            }
        self.stats["models"][model_name]["switch_count"] += 1
        self.stats["models"][model_name]["last_used"] = now

        # 更新每日统计
        if today not in self.stats["daily_usage"]:
            self.stats["daily_usage"][today] = {}
        if model_name not in self.stats["daily_usage"][today]:
            self.stats["daily_usage"][today][model_name] = 0
        self.stats["daily_usage"][today][model_name] += 1

        # 更新最后切换时间
        self.stats["last_switch"] = {
            "model": model_name,
            "time": now
        }

        self._save_stats()

    def get_summary(self) -> dict:
        """获取统计摘要"""
        return {
            "total_switches": self.stats["total_switches"],
            "total_models": len(self.stats["models"]),
            "last_switch": self.stats.get("last_switch"),
            "most_used": self._get_most_used_model()
        }

    def _get_most_used_model(self) -> Optional[Tuple[str, int]]:
        """获取使用最多的模型"""
        if not self.stats["models"]:
            return None
        most_used = max(
            self.stats["models"].items(),
            key=lambda x: x[1]["switch_count"]
        )
        return (most_used[0], most_used[1]["switch_count"])

    def get_model_stats(self, model_name: str) -> Optional[dict]:
        """获取特定模型的统计"""
        return self.stats["models"].get(model_name)

    def get_recent_days(self, days: int = 7) -> dict:
        """获取最近几天的统计"""
        result = {}
        today = datetime.now()
        for i in range(days):
            date = (today - __import__('datetime').timedelta(days=i)).strftime("%Y-%m-%d")
            if date in self.stats["daily_usage"]:
                result[date] = self.stats["daily_usage"][date]
            else:
                result[date] = {}
        return result

    def print_stats(self):
        """打印统计信息"""
        print("📊 API 使用统计")
        print("=" * 50)

        summary = self.get_summary()
        print(f"总切换次数: {summary['total_switches']}")
        print(f"使用的模型数: {summary['total_models']}")

        if summary['last_switch']:
            print(f"最后切换: {summary['last_switch']['model']} ({summary['last_switch']['time']})")

        if summary['most_used']:
            print(f"最常用模型: {summary['most_used'][0]} ({summary['most_used'][1]} 次)")

        print("\n📈 各模型使用详情:")
        print("-" * 50)
        print(f"{'模型名':<15} {'切换次数':<10} {'最后使用':<20}")
        print("-" * 50)

        for model_name, stats in sorted(
            self.stats["models"].items(),
            key=lambda x: x[1]["switch_count"],
            reverse=True
        ):
            print(f"{model_name:<15} {stats['switch_count']:<10} {stats['last_used']:<20}")

        # 显示最近7天的使用情况
        print("\n📅 最近 7 天使用情况:")
        print("-" * 50)
        recent = self.get_recent_days(7)
        for date in sorted(recent.keys(), reverse=True):
            usage = recent[date]
            if usage:
                total = sum(usage.values())
                models_str = ", ".join([f"{k}:{v}" for k, v in usage.items()])
                print(f"{date}: {total} 次 ({models_str})")
            else:
                print(f"{date}: 0 次")

    def reset_stats(self):
        """重置统计数据"""
        self.stats = self._init_stats()
        self._save_stats()
        print("✅ 统计数据已重置")


class HealthMonitor:
    """API 健康监控器"""

    HEALTH_FILE = ".health_state.json"

    def __init__(self, manager: 'EnvManager'):
        self.manager = manager
        self.health_path = Path(self.HEALTH_FILE)
        self.health_state = self._load_health_state()

    def _load_health_state(self) -> dict:
        """加载健康状态"""
        if self.health_path.exists():
            try:
                with open(self.health_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_health_state(self):
        """保存健康状态"""
        try:
            with open(self.health_path, "w", encoding="utf-8") as f:
                json.dump(self.health_state, f, indent=2, ensure_ascii=False)
        except:
            pass

    def check_and_switch(self, auto_switch: bool = True) -> Tuple[str, bool]:
        """检查当前API健康状态，如果不可用则自动切换
        返回: (当前/切换后的模型名, 是否进行了切换)
        """
        current = self.manager.get_current_model()
        if not current or current == "未知":
            print("⚠️  当前没有设置模型")
            return None, False

        # 测试当前API
        status, resp_time = self.manager.test_api(current)

        if status:
            # 当前API正常
            self.health_state[current] = {
                "status": "healthy",
                "last_check": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "response_time": resp_time
            }
            self._save_health_state()
            return current, False

        # 当前API不可用
        print(f"⚠️  当前模型 '{current}' 不可用")
        self.health_state[current] = {
            "status": "unhealthy",
            "last_check": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "response_time": None
        }

        if not auto_switch:
            self._save_health_state()
            return current, False

        # 查找可用的替代API
        print("🔍 正在查找可用的替代API...")
        results = self.manager.test_apis_concurrent(show_progress=True)

        # 按响应时间排序，选择最快的可用API
        available = [
            (model, resp_time)
            for model, (status, resp_time) in results.items()
            if status and model != current
        ]

        if not available:
            print("❌ 没有找到可用的替代API")
            self._save_health_state()
            return current, False

        # 选择响应最快的
        available.sort(key=lambda x: x[1])
        best_model, best_time = available[0]

        print(f"\n✅ 找到最佳替代: {best_model} (响应时间: {best_time:.2f}s)")
        print(f"🔄 正在自动切换...")

        self.manager.switch_model(best_model, record_stats=True)

        self.health_state[best_model] = {
            "status": "healthy",
            "last_check": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "response_time": best_time
        }
        self._save_health_state()

        return best_model, True

    def get_health_report(self) -> dict:
        """获取健康报告"""
        report = {
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "models": {}
        }

        # 测试所有API
        results = self.manager.test_apis_concurrent(show_progress=True)

        for model, (status, resp_time) in results.items():
            report["models"][model] = {
                "status": "healthy" if status else "unhealthy",
                "response_time": resp_time,
                "previous_state": self.health_state.get(model, {}).get("status", "unknown")
            }

        return report

    def print_health_report(self):
        """打印健康报告"""
        print("🏥 API 健康状态报告")
        print("=" * 60)

        report = self.get_health_report()
        print(f"检测时间: {report['last_update']}")
        print()

        healthy_count = 0
        unhealthy_count = 0

        print(f"{'模型名':<15} {'状态':<10} {'响应时间':<12} {'上次状态':<10}")
        print("-" * 60)

        for model, data in report["models"].items():
            status_icon = "✅ 健康" if data["status"] == "healthy" else "❌ 不可用"
            time_str = f"{data['response_time']:.2f}s" if data['response_time'] else "N/A"
            prev_status = data["previous_state"]

            if data["status"] == "healthy":
                healthy_count += 1
            else:
                unhealthy_count += 1

            print(f"{model:<15} {status_icon:<10} {time_str:<12} {prev_status:<10}")

        print("-" * 60)
        print(f"总计: {healthy_count} 个健康, {unhealthy_count} 个不可用")


class DeepLinkHandler:
    """深度链接处理器 - 用于分享和导入配置"""

    PROTOCOL = "claude-switch://"

    @staticmethod
    def generate_share_link(provider_name: str, config: dict, include_token: bool = False) -> str:
        """生成分享链接

        Args:
            provider_name: Provider 名称
            config: Provider 配置
            include_token: 是否包含完整 Token

        Returns:
            分享链接字符串
        """
        data = {
            "name": provider_name,
            "base_url": config.get("ANTHROPIC_BASE_URL", "")
        }

        if include_token:
            data["token"] = config.get("ANTHROPIC_AUTH_TOKEN", "")

        # Base64 编码
        json_str = json.dumps(data, ensure_ascii=False)
        encoded = base64.urlsafe_b64encode(json_str.encode()).decode()

        return f"{DeepLinkHandler.PROTOCOL}import?data={encoded}"

    @staticmethod
    def parse_share_link(link: str) -> dict:
        """解析分享链接

        Args:
            link: 分享链接

        Returns:
            解析后的配置字典

        Raises:
            ValueError: 链接格式错误
        """
        if not link.startswith(DeepLinkHandler.PROTOCOL):
            raise ValueError(f"无效的链接格式，应以 {DeepLinkHandler.PROTOCOL} 开头")

        try:
            # 提取 data 参数
            if "?data=" not in link:
                raise ValueError("链接缺少 data 参数")

            data_param = link.split("?data=")[1].split("&")[0]

            # Base64 解码
            decoded = base64.urlsafe_b64decode(data_param).decode()
            config_data = json.loads(decoded)

            # 验证必需字段
            if "name" not in config_data or "base_url" not in config_data:
                raise ValueError("链接数据不完整，缺少必需字段")

            return config_data

        except (IndexError, json.JSONDecodeError, Exception) as e:
            raise ValueError(f"链接解析失败: {e}")


class EnvManager:
    """环境变量管理器"""

    # 默认超时时间（秒）
    DEFAULT_TIMEOUT = 5

    def __init__(self, config_path: str = "model_config.json", timeout: int = None):
        self.config_path = config_path
        self.system = platform.system()
        self.timeout = timeout or self.DEFAULT_TIMEOUT
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

    def list_models(self, show_status: bool = False):
        """列出所有可用模型"""
        current = self.get_current_model()

        print("📋 可用模型列表：")
        if current and current != "未知":
            print(f"📍 当前启用的模型: {current}\n")

        if show_status:
            # 使用并发测试
            results = self.test_apis_concurrent(show_progress=True)

            print(f"\n{'序号':<4} {'模型名':<15} {'状态':<8} {'响应时间':<10} {'标记':<10}")
            print("-" * 60)

            for i, model in enumerate(self.config.keys(), 1):
                status, resp_time = results.get(model, (False, None))
                status_icon = "✅" if status else "❌"
                time_str = f"{resp_time:.2f}s" if resp_time else "N/A"
                marker = "⭐ 当前启用" if model == current else ""
                print(f"{i:<4} {model:<15} {status_icon:<8} {time_str:<10} {marker:<10}")
        else:
            for i, model in enumerate(self.config.keys(), 1):
                marker = " ⭐ 当前启用" if model == current and current != "未知" else ""
                print(f"  {i}. {model}{marker}")

    def switch_model(self, model_name: str, auto_reload: bool = True, record_stats: bool = True):
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

        # 记录使用统计
        if record_stats:
            try:
                stats = UsageStats()
                stats.record_switch(model_name)
            except Exception:
                pass  # 统计失败不影响主功能

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
        print("\n" + "=" * 70)
        print("🎯 Claude 模型切换工具 - 交互模式")
        print("=" * 70)

        # 显示当前模型
        current = self.get_current_model()
        if current and current != "未知":
            print(f"📍 当前启用的模型: {current}")
        else:
            print(f"📍 当前启用的模型: 未设置")

        print()
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

    def export_config(self, export_path: str, include_tokens: bool = False) -> bool:
        """导出配置文件
        Args:
            export_path: 导出路径
            include_tokens: 是否包含完整的 Token（默认脱敏）
        """
        try:
            export_data = {
                "version": "1.0",
                "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "models": {}
            }

            for name, config in self.config.items():
                export_data["models"][name] = {
                    "ANTHROPIC_BASE_URL": config.get("ANTHROPIC_BASE_URL", ""),
                    "ANTHROPIC_AUTH_TOKEN": config.get("ANTHROPIC_AUTH_TOKEN", "") if include_tokens else ""
                }

            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"❌ 导出配置失败: {e}")
            return False

    def import_config(self, import_path: str, merge: bool = False) -> bool:
        """导入配置文件
        Args:
            import_path: 导入路径
            merge: 是否合并（True则合并，False则覆盖）
        """
        try:
            if not os.path.exists(import_path):
                print(f"❌ 导入文件不存在: {import_path}")
                return False

            with open(import_path, "r", encoding="utf-8") as f:
                import_data = json.load(f)

            # 兼容新旧格式
            if "models" in import_data:
                models = import_data["models"]
            else:
                models = import_data

            imported_count = 0
            skipped_count = 0

            for name, config in models.items():
                # 检查是否有有效的 URL
                if not config.get("ANTHROPIC_BASE_URL"):
                    print(f"⚠️  跳过 '{name}'：没有 BASE_URL")
                    skipped_count += 1
                    continue

                if merge and name in self.config:
                    # 合并模式：只更新非空字段
                    if config.get("ANTHROPIC_BASE_URL"):
                        self.config[name]["ANTHROPIC_BASE_URL"] = config["ANTHROPIC_BASE_URL"]
                    if config.get("ANTHROPIC_AUTH_TOKEN"):
                        self.config[name]["ANTHROPIC_AUTH_TOKEN"] = config["ANTHROPIC_AUTH_TOKEN"]
                    print(f"🔄 已更新: {name}")
                else:
                    # 覆盖模式或新模型
                    self.config[name] = {
                        "ANTHROPIC_BASE_URL": config.get("ANTHROPIC_BASE_URL", ""),
                        "ANTHROPIC_AUTH_TOKEN": config.get("ANTHROPIC_AUTH_TOKEN", "")
                    }
                    print(f"✅ 已导入: {name}")
                imported_count += 1

            self._save_config()
            print(f"\n📊 导入完成: {imported_count} 个成功, {skipped_count} 个跳过")
            return True

        except json.JSONDecodeError as e:
            print(f"❌ 文件格式错误: {e}")
            return False
        except Exception as e:
            print(f"❌ 导入配置失败: {e}")
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
            print(f"📍 当前启用的模型: {current}")
            print(f"\n🔍 正在检测状态...")
            # 测试当前模型状态
            status, resp_time = manager.test_api(current)
            if status:
                print(f"✅ 状态: 可用")
                print(f"⚡ 响应时间: {resp_time:.2f}s")
            else:
                print(f"❌ 状态: 不可用")
                print(f"\n💡 正在检测其他可用模型...")
                print("=" * 60)
                manager.list_models(show_status=True)
        else:
            print("📍 当前启用的模型: 未设置")
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
    if command in ["show", "info", "--show"]:
        print("📋 当前配置信息：\n")
        for model_name, config in manager.config.items():
            print(f"模型: {model_name}")
            print(f"  BASE_URL: {config.get('ANTHROPIC_BASE_URL', 'N/A')}")
            token = config.get('ANTHROPIC_AUTH_TOKEN', '')
            print(f"  TOKEN: {mask_sensitive_info(token, 10)}")
            print()
        sys.exit(0)

    # 使用统计
    if command in ["stats", "--stats"]:
        stats = UsageStats()
        stats.print_stats()
        sys.exit(0)

    # 重置统计
    if command in ["reset-stats", "--reset-stats"]:
        print("⚠️  确认重置所有使用统计？(y/n): ", end="")
        if input().strip().lower() == 'y':
            stats = UsageStats()
            stats.reset_stats()
        else:
            print("❌ 取消重置")
        sys.exit(0)

    # 健康检查
    if command in ["health", "--health"]:
        monitor = HealthMonitor(manager)
        monitor.print_health_report()
        sys.exit(0)

    # 自动切换（检查并切换到可用API）
    if command in ["auto", "--auto", "auto-switch"]:
        monitor = HealthMonitor(manager)
        model, switched = monitor.check_and_switch(auto_switch=True)
        if switched:
            print(f"\n✅ 已自动切换到: {model}")
        elif model:
            print(f"✅ 当前模型 '{model}' 运行正常，无需切换")
        sys.exit(0)

    # 导出配置
    if command in ["export", "--export"]:
        if len(sys.argv) < 3:
            print("💡 用法: python set_model.py export <导出文件路径> [--with-tokens]")
            print("示例: python set_model.py export my_config.json")
            print("      python set_model.py export my_config.json --with-tokens")
            sys.exit(1)

        export_path = sys.argv[2]
        include_tokens = "--with-tokens" in sys.argv

        if manager.export_config(export_path, include_tokens):
            print(f"✅ 配置已导出至: {export_path}")
            if not include_tokens:
                print("💡 提示: Token 已脱敏，如需包含完整 Token，请添加 --with-tokens 参数")
        sys.exit(0)

    # 导入配置
    if command in ["import", "--import"]:
        if len(sys.argv) < 3:
            print("💡 用法: python set_model.py import <导入文件路径|分享链接> [--merge]")
            print("示例: python set_model.py import my_config.json")
            print("      python set_model.py import my_config.json --merge")
            print("      python set_model.py import 'claude-switch://import?data=...'")
            sys.exit(1)

        import_path = sys.argv[2]
        merge = "--merge" in sys.argv

        # 判断是否为深度链接
        if import_path.startswith("claude-switch://"):
            try:
                config_data = DeepLinkHandler.parse_share_link(import_path)
                print(f"📥 正在导入配置: {config_data['name']}")
                print(f"   BASE_URL: {config_data['base_url']}")

                # 如果链接中包含 token
                if "token" in config_data and config_data["token"]:
                    token = config_data["token"]
                    print(f"   TOKEN: {mask_sensitive_info(token, 10)}")
                else:
                    # 提示用户输入 token
                    print(f"   TOKEN: 未包含（需要手动输入）")
                    token = input("\n请输入 TOKEN: ").strip()
                    if not token:
                        print("❌ Token 不能为空")
                        sys.exit(1)

                # 添加到配置
                manager.add_model(config_data["name"], config_data["base_url"], token)
                print(f"\n✅ 配置导入成功！")

            except ValueError as e:
                print(f"❌ 导入失败: {e}")
                sys.exit(1)
        else:
            # 传统的文件导入
            if merge:
                print("📋 合并模式: 将与现有配置合并")
            else:
                print("📋 覆盖模式: 将添加新配置")

            manager.import_config(import_path, merge)
        sys.exit(0)

    # 分享配置（生成深度链接）
    if command in ["share", "--share"]:
        if len(sys.argv) < 3:
            print("💡 用法: python set_model.py share <模型名> [--with-token]")
            print("示例: python set_model.py share Gemai")
            print("      python set_model.py share Gemai --with-token")
            sys.exit(1)

        model_name = sys.argv[2]
        include_token = "--with-token" in sys.argv

        if model_name not in manager.config:
            print(f"❌ 模型 '{model_name}' 不存在")
            print(f"\n可用模型：{', '.join(manager.config.keys())}")
            sys.exit(1)

        config = manager.config[model_name]
        share_link = DeepLinkHandler.generate_share_link(model_name, config, include_token)

        print(f"📤 分享链接已生成：\n")
        print(f"{share_link}\n")
        print("💡 使用方式：")
        print("  1. 复制上面的链接发送给其他人")
        print("  2. 对方运行: python set_model.py import '<链接>'")
        print("  3. 自动添加配置到他们的工具中")

        if include_token:
            print("\n⚠️  安全提示: 链接包含完整 Token，请谨慎分享！")
        else:
            print("\n💡 提示: Token 未包含，对方需要手动输入")

        sys.exit(0)

    # 配置别名
    if command in ["setup-alias", "setup", "--setup-alias"]:
        manager.setup_alias()
        sys.exit(0)

    # 加密配置文件
    if command in ["encrypt", "--encrypt"]:
        if not CRYPTO_AVAILABLE:
            print("❌ 加密功能需要安装 cryptography 库")
            print("💡 请运行: pip install cryptography")
            sys.exit(1)

        encryption = ConfigEncryption()
        if encryption.is_encrypted(manager.config_path):
            print("⚠️  配置文件已加密")
            sys.exit(0)

        password = getpass.getpass("请设置加密密码: ")
        password_confirm = getpass.getpass("请确认密码: ")

        if password != password_confirm:
            print("❌ 两次输入的密码不一致")
            sys.exit(1)

        try:
            encrypted_path = encryption.encrypt_config(manager.config_path, password)
            # 删除原始配置文件
            os.remove(manager.config_path)
            print(f"✅ 配置已加密: {encrypted_path}")
            print("⚠️  原始配置文件已删除，请牢记密码！")
        except Exception as e:
            print(f"❌ 加密失败: {e}")
        sys.exit(0)

    # 解密配置文件
    if command in ["decrypt", "--decrypt"]:
        if not CRYPTO_AVAILABLE:
            print("❌ 解密功能需要安装 cryptography 库")
            print("💡 请运行: pip install cryptography")
            sys.exit(1)

        encryption = ConfigEncryption()
        encrypted_path = manager.config_path + encryption.ENCRYPTED_SUFFIX

        if not os.path.exists(encrypted_path):
            print("⚠️  没有找到加密的配置文件")
            sys.exit(0)

        password = getpass.getpass("请输入解密密码: ")

        try:
            config = encryption.decrypt_config(encrypted_path, password)
            # 保存解密后的配置
            with open(manager.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            # 删除加密文件
            os.remove(encrypted_path)
            print(f"✅ 配置已解密: {manager.config_path}")
        except Exception as e:
            print(f"❌ 解密失败: {e}")
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
        print("\n导入导出命令:")
        print("  python set_model.py export <文件> [--with-tokens]  # 导出配置")
        print("  python set_model.py import <文件> [--merge]        # 导入配置")
        print("  python set_model.py share <模型名> [--with-token]  # 生成分享链接")
        print("  python set_model.py import '<链接>'                # 从链接导入")
        print("\n统计命令:")
        print("  python set_model.py stats              # 查看使用统计")
        print("  python set_model.py reset-stats        # 重置统计数据")
        print("\n健康监控命令:")
        print("  python set_model.py health             # 查看所有API健康状态")
        print("  python set_model.py auto               # 自动检查并切换到可用API")
        print("\n安全命令:")
        print("  python set_model.py encrypt            # 加密配置文件（需要cryptography库）")
        print("  python set_model.py decrypt            # 解密配置文件")
        print("\n设置命令:")
        print("  python set_model.py setup-alias        # 自动配置 claude-switch 别名")
        print("\n其他命令:")
        print("  python set_model.py list               # 列出所有模型（不测试）")
        print("  python set_model.py interactive        # 交互模式")
        print("\n全局参数:")
        print("  --timeout, -t <秒>                     # 设置API测试超时时间（默认5秒）")
        print("\n命令别名:")
        print("  list: ls, -l        status: st, -s      current: cur, -c")
        print("  add: -a             update: up, -u      remove: rm, -r")
        print("  interactive: i, -i  backup: bak, -b     restore: res")
        print("  show: info          auto: auto-switch   setup-alias: setup")
        print("\n💡 提示:")
        print("  - 首次使用建议运行 'python set_model.py setup-alias' 配置别名")
        print("  - 配置别名后可直接使用 'claude-switch' 命令，环境变量立即生效")
        print("  - current命令会自动检测当前模型，如果不可用会显示所有模型状态")
        print("  - 交互模式会实时显示所有API的状态和响应速度")
        print("  - status命令使用并发测试，快速获取所有API状态")
        print("  - 使用热身请求技术提高测速准确性（自动启用）")
        print("  - share命令可生成一键分享链接，方便配置分享")
        print("  - 加密功能使用 PBKDF2 + Fernet 算法，安全可靠")
        print("  - stats命令显示详细的使用统计和最近7天的使用情况")
        print("  - 使用 --timeout 参数可以自定义超时时间，如: python set_model.py status -t 10")
        print("  - auto命令会自动检测当前API，不可用时切换到最快的可用API")
        print("  - export/import命令支持配置的跨设备迁移和分享")
        sys.exit(0)

    # 默认：切换模型
    manager.switch_model(command)


if __name__ == "__main__":
    main()
