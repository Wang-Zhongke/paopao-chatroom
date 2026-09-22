#!/usr/bin/env python3
"""Install a local skill copy without overwriting an existing installation."""
import argparse
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    target = (args.destination or Path.home() / '.agents/skills/paopao-perspective-skill').expanduser().absolute()
    if target.exists() or target.is_symlink():
        parser.error('目标已存在；请先备份或选择新的目标目录。未修改已有安装。')
    if source == target or source in target.parents:
        parser.error('目标不能位于源 Skill 内部。')
    if not (source / 'SKILL.md').is_file():
        parser.error('未找到 SKILL.md。')
    for item in source.rglob('*'):
        if item.is_symlink():
            parser.error('源目录含符号链接，请先检查并使用轻量包。')
    ignore = shutil.ignore_patterns('.git', '.DS_Store', '.env*', '__pycache__', '*.pyc', '*.bin', '.build', 'video-cache', 'transcripts')
    shutil.copytree(source, target, ignore=ignore)
    print(f'已安装到 {target}')
    print('在宿主选择 paopao-perspective-skill；若未出现，请刷新或重启宿主。')


if __name__ == '__main__':
    main()
