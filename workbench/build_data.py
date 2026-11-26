#!/usr/bin/env python3
"""Build the private hardware workbench view from the Lab's source records."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
            'checks': [
                {'label': '嘉立创 EDA 专业版', 'status': 'passed',
                 'detail': 'Apple silicon 客户端已安装，官方签名已验证。'},
                {'label': '原生 MCP 连接', 'status': env['mcp_doctor_call'],
                 'detail': '握手、工具发现与 doctor 调用已通过。'},
                {'label': '编辑器工程操作', 'status': 'pending',
                 'detail': '等待本人账号的免费激活文件；尚未完成工程创建验证。'},
            ],
            'skills': [
                {'id': 'lceda-pro-automation', 'name': '嘉立创 EDA 自动化',
                 'detail': '操作原理图、PCB、检查与导出；已接入 Codex 和 Claude Code。'},
                {'id': 'pcb-product-delivery', 'name': 'PCB 产品交付',
                 'detail': '负责器件、工厂装配、固件、外壳及整机验收。'},
            ],
        },
        'projects': projects,
        'documents': catalog['documents'],
        'resources': catalog['resources'],
    }


if __name__ == '__main__':
    target = ROOT / 'workbench/web/workbench.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + '\n')
    print(f'Built {target.relative_to(ROOT)} from project and environment records')
