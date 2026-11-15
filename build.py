
from pathlib import Path
import os
import re
import subprocess
import sys


# =========================
# build.py 的几个关键设计
  #1. 自动跳过空行和 # 注释。
  #2. 自动去重，不区分域名大小写。
  #3. 保留 +. 前缀，不会把它改成普通域名。
  #4. 遇到格式错误的规则直接终止构建。
  #5. 转换失败不会覆盖之前生成的正式 MRS 文件。
  #6. 输出到 dist/gfw.mrs，等待 GitHub Actions 发布。
# =========================

ROOT = Path(__file__).resolve().parent

INPUT_FILE = ROOT / "aicoin.txt"
OUTPUT_FILE = ROOT / "dist" / "gfw.mrs"

MIHOMO = os.environ.get("MIHOMO_BIN", "mihomo")


# =========================
# 规则检查与去重
# =========================

DOMAIN_PATTERN = re.compile(
    r"^(?:\+\.)?"
    r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$",
    re.IGNORECASE
)


def load_rules():
    if not INPUT_FILE.is_file():
        raise FileNotFoundError(
            f"找不到规则源文件：{INPUT_FILE}"
        )

    rules = []
    seen = set()

    for line_number, raw_line in enumerate(
        INPUT_FILE.read_text(encoding="utf-8-sig").splitlines(),
        start=1
    ):
        rule = raw_line.strip()

        # 跳过空行和注释
        if not rule or rule.startswith("#"):
            continue

        rule = rule.lower()

        # 检查域名格式
        if not DOMAIN_PATTERN.fullmatch(rule):
            raise ValueError(
                f"第 {line_number} 行规则格式错误：{raw_line}"
            )

        # 去重
        if rule not in seen:
            seen.add(rule)
            rules.append(rule)

    if not rules:
        raise ValueError("规则文件为空，没有可转换的域名规则")

    return sorted(rules)


# =========================
# 生成去重后的临时 TXT
# =========================

def prepare_input(rules):
    temp_file = ROOT / "dist" / "rules.txt"
    temp_file.parent.mkdir(parents=True, exist_ok=True)

    temp_file.write_text(
        "\n".join(rules) + "\n",
        encoding="utf-8"
    )

    return temp_file


# =========================
# 转换 MRS
# =========================

def convert_to_mrs(input_file):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    temp_output = OUTPUT_FILE.with_name("gfw.tmp.mrs")

    if temp_output.exists():
        temp_output.unlink()

    command = [
        MIHOMO,
        "convert-ruleset",
        "domain",
        "text",
        str(input_file),
        str(temp_output)
    ]

    print("开始转换 MRS...")
    print("执行命令：", " ".join(command))

    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if result.stdout:
        print(result.stdout)

    if result.returncode != 0:
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        raise RuntimeError("Mihomo MRS 转换失败")

    # 检查生成文件
    if not temp_output.is_file():
        raise RuntimeError("MRS 文件没有生成")

    if temp_output.stat().st_size == 0:
        raise RuntimeError("MRS 文件大小为 0")

    # 只有检查通过后才替换正式输出
    os.replace(temp_output, OUTPUT_FILE)

    print(f"MRS 生成成功：{OUTPUT_FILE}")
    print(f"文件大小：{OUTPUT_FILE.stat().st_size} bytes")


# =========================
# 主程序
# =========================

def main():
    print("=" * 50)
    print("开始构建自定义 MRS 规则集")
    print("=" * 50)

    rules = load_rules()

    print(f"读取规则数量：{len(rules)}")

    for rule in rules:
        print("规则：", rule)

    input_file = prepare_input(rules)

    convert_to_mrs(input_file)

    print("=" * 50)
    print("构建完成！")
    print(f"规则数量：{len(rules)}")
    print(f"输出文件：{OUTPUT_FILE}")
    print("=" * 50)


if __name__ == "__main__":
    main()
