import json
import sys
import subprocess
import os
import platform
import re
from pathlib import Path
from typing import Dict, Optional


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

    def list_models(self):
        """列出所有可用模型"""
        print("📋 可用模型列表：")
        for i, model in enumerate(self.config.keys(), 1):
            print(f"  {i}. {model}")

    def switch_model(self, model_name: str):
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


def main():
    manager = EnvManager()

    # 没有参数时显示帮助信息
    if len(sys.argv) < 2:
        print("💡 用法: python set_model.py <模型名>")
        print()
        manager.list_models()
        sys.exit(0)

    model_name = sys.argv[1]

    # 特殊命令：列出所有模型
    if model_name in ["list", "ls", "--list", "-l"]:
        manager.list_models()
        sys.exit(0)

    # 切换模型
    manager.switch_model(model_name)


if __name__ == "__main__":
    main()