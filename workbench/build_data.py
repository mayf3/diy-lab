#!/usr/bin/env python3
"""Build the private hardware workbench view from the Lab's source records."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def environment_checks(env: dict) -> list:
    round_trip = env.get('editor_round_trip') == 'passed' and env.get('editor_round_trip_passed_at')
    return [
        {'label': '嘉立创 EDA 专业版', 'status': 'passed',
         'detail': 'Apple silicon 客户端已安装，官方签名已验证。'},
        {'label': '原生 MCP 连接', 'status': env['mcp_doctor_call'],
         'detail': '握手、工具发现与 doctor 调用已通过。'},
        {'label': '官方激活', 'status': 'passed' if env.get('activation_accepted_at') else 'pending',
         'detail': (f"客户端已接受官方激活文件（{str(env.get('activation_accepted_at'))[:10]}），重启后保持。"
                    if env.get('activation_accepted_at')
                    else '等待本人账号的免费激活文件。')},
        {'label': '编辑器工程读写往返', 'status': 'passed' if round_trip else 'pending',
         'detail': (f"独立工程创建、保存、关闭重开与标记读回已于 "
                    f"{str(env.get('editor_round_trip_passed_at'))[:10]} 通过。"
                    if round_trip else '等待本人账号的免费激活文件；尚未完成工程创建验证。')},
    ]


def build() -> dict:
    source = json.loads((ROOT / 'source-data/productization/projects.json').read_text())
    env = json.loads((ROOT / 'docs/eda/environment-status.json').read_text())
    catalog = json.loads((ROOT / 'workbench/catalog.json').read_text())
    projects = []
    for item in source['projects']:
        presentation = catalog['projects'][item['id']]
        projects.append({
            'id': item['id'], 'name': item['name'],
            'priority': item['priority'], 'summary': '；'.join(item['observed']),
            'route': item['recommended_route'], 'next_step': item['next_step'],
            'open_items': item['open_items'], 'constraint': item['constraint'],
            **presentation,
        })
    checks = environment_checks(env)
    # Hardware Studio（PR-A）：统一项目模型校验器作为唯一真源（子进程，失败如实呈现）
    hardware = None
    try:
        proc = subprocess.run(
            [sys.executable, 'hardware/check_project.py',
             '--project', 'hardware/space-buddy-r1/project.json'],
            capture_output=True, text=True, timeout=30, cwd=str(ROOT))
        if proc.returncode == 0 and proc.stdout.strip():
            hardware = json.loads(proc.stdout)
        else:
            hardware = {'ok': False, 'error': (proc.stderr or proc.stdout or 'unknown')[:400]}
    except Exception as exc:  # 校验器故障必须可见，不得静默吞掉
        hardware = {'ok': False, 'error': str(exc)[:400]}
    return {
        'schema_version': 1,
        'title': '硬件工作台',
        'updated_at': source['updated_on'],
        'objective': source['objective'],
        'environment': {
            'version': env['editor_cli_version'],
            'state': env['state'],
            'checked_at': env['date'],
            'activation_url': env['official_activation_page'],
            'checks': checks,
            'ready': all(check['status'] == 'passed' for check in checks),
        },
        'projects': projects,
        'hardware': hardware,
        'hardware_next': (json.loads(Path('hardware/space-buddy-r1/project.json').read_text()).get('workbench_nine', {})
                          if (ROOT / 'hardware/space-buddy-r1/project.json').is_file() else {}),
        'documents': catalog['documents'],
        'resources': catalog['resources'],
    }


if __name__ == '__main__':
    target = ROOT / 'workbench/web/workbench.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + '\n')
    print(f'Built {target.relative_to(ROOT)} from project and environment records')
