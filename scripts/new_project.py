#!/usr/bin/env python3
"""Create a new project from reusable templates and register it in the site index."""
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(argv):
    if len(argv) != 3:
        print('用法: python3 scripts/new_project.py your-project-slug "项目中文名称"')
        return 2
    slug, title = argv[1], argv[2].strip()
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',slug) or not title:
        print('项目 slug 只能是英文小写、数字与连字符，名称不能为空。')
        return 2
    manifest=ROOT/'data/projects.json'
    projects=json.loads(manifest.read_text(encoding='utf-8'))
    if any(p['slug']==slug for p in projects):
        print('项目已存在:',slug)
        return 2
    project_root=ROOT/'content/projects'/slug
    source_root=ROOT/'source-data'/slug
    media_root=ROOT/'public/media'/slug
    if project_root.exists() or source_root.exists() or media_root.exists():
        print('目录已存在，停止以防覆盖:',slug)
        return 2
    project_root.mkdir(parents=True)
    source_root.mkdir(parents=True)
    media_root.mkdir(parents=True)
    templates=ROOT/'templates/project'
    for source, destination in [('index.md','index.md'),('01-workflow.md','01-workflow.md'),('video-plan.md','video-plan.md')]:
        body=(templates/source).read_text(encoding='utf-8').replace('{{TITLE}}',title).replace('{{SLUG}}',slug)
        (project_root/destination).write_text(body,encoding='utf-8')
    shutil.copy2(templates/'bom.csv',source_root/'bom.csv')
    workflow_template=(templates/'workflow.json').read_text(encoding='utf-8')
    (source_root/'workflow.json').write_text(
        workflow_template.replace('{{SLUG}}', slug).replace('{{TITLE}}', title),
        encoding='utf-8'
    )
    (media_root/'.gitkeep').write_text('',encoding='utf-8')
    projects.append({
      'slug':slug, 'title':title, 'subtitle':'待补充项目目标',
      'status':'planning', 'category':'待分类',
      'description':'项目初始化：仍需确定目标、采购、结构、验收与拍摄计划。',
      'date':'待更新', 'budget':'待估算',
      'steps':[{'id':'01','file':'01-workflow.md','title':'准备和采购前验证','minutes':'待估算','phase':'准备'}]
    })
    manifest.write_text(json.dumps(projects,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    videos=ROOT/'data/videos.json'
    current=json.loads(videos.read_text(encoding='utf-8'))
    current.append({'project':slug,'title':title+'：制作全过程','status':'planned',
                    'description':'拍摄计划已创建，尚未拍摄或发布。', 'video_url':'', 'embed':''})
    videos.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Generate both readers from the same source data, never copy stale prose.
    from render_diy_ir import run as render_views
    if render_views():
        print('DIY 工作流检查失败，请修复 workflow.json')
        return 1
    print(f'已创建: {project_root.relative_to(ROOT)}')
    print(f'购物清单: {source_root.relative_to(ROOT)}/bom.csv')
    print('下一步: 编辑教程和 BOM，然后执行 python3 scripts/check.py && python3 scripts/build.py')
    return 0

if __name__=='__main__':
    sys.exit(main(sys.argv))
