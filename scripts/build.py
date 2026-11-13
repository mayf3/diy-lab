#!/usr/bin/env python3
"""Build Maker Lab as an offline-friendly static website.

All navigation is relative to the output HTML file, so the same dist/
works under file://, a root domain, or a GitHub Pages repository path.
"""
from __future__ import annotations

import datetime
import hashlib
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

import mistune

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
DIST = ROOT / "dist"
PROJECTS = json.loads((ROOT / "data/projects.json").read_text(encoding="utf-8"))
PROJECT_MAP = {p["slug"]: p for p in PROJECTS}
VIDEOS = json.loads((ROOT / "data/videos.json").read_text(encoding="utf-8"))
GENERATOR_VERSION = "0.1"
BUILD_DATE = datetime.date.today().isoformat()
STATUS = {
    "planning": ("规划中", "planning"),
    "preparing": ("准备中 · 未验证", "preparing"),
    "building": ("制作中", "building"),
    "verified": ("已验证", "verified"),
    "completed-unwritten": ("已完成 · 待整理教程", "unwritten"),
    "archived": ("已归档", "archived"),
}

md = mistune.create_markdown(escape=False, plugins=["table", "strikethrough", "task_lists", "url"])


def q(s: object) -> str:
    return html.escape(str(s), quote=True)


def slug_from_source(path: Path) -> str:
    rel = path.relative_to(CONTENT)
    if rel.name == "index.md":
        return str(rel.parent).replace("\\", "/") if str(rel.parent) != "." else ""
    return str(rel.with_suffix("")).replace("\\", "/")


def output_path(slug: str) -> Path:
    return DIST / slug / "index.html"


def link_for(current_slug: str, target_slug: str) -> str:
    rel = os.path.relpath(output_path(target_slug), output_path(current_slug).parent)
    return rel.replace("\\", "/")


def build_version() -> str:
    """Cache-bust 版本：固定文件名资源（main.js/search-index.js）用已发布提交的短哈希。
    老访客的 immutable 长缓存只能靠 URL 变化迁移，这是 2026-11-10 审查确认的方案。"""
    try:
        import subprocess
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True, cwd=Path(__file__).resolve().parent.parent,
        ).strip()
    except Exception:
        import datetime
        return datetime.datetime.now().strftime("%Y%m%d%H%M")


def url_for(current_slug: str, target_path: str) -> str:
    if target_path.startswith("#"):
        return target_path
    if target_path.startswith(("https://", "http://", "mailto:")):
        return target_path
    page, sep, anchor = target_path.partition("#")
    if page.startswith("/downloads/") or page.startswith("/media/") or page.startswith("/assets/"):
        dest = DIST / page.lstrip("/")
        res = os.path.relpath(dest, output_path(current_slug).parent)
    elif page.startswith("/"):
        dest_slug = page.strip("/")
        res = link_for(current_slug, dest_slug)
    else:
        return target_path
    return res.replace("\\", "/") + (("#" + anchor) if sep else "")


def rewrite_md_links(body: str, current_slug: str) -> str:
    # Authoring convention: all internal links are absolute site paths (e.g. /projects/...).
    return re.sub(
        r"(\]\()(/[^)]+)(\))",
        lambda match: match.group(1) + url_for(current_slug, match.group(2)) + match.group(3),
        body,
    )


def toc_and_anchors(markup: str):
    entries = []
    counter = 0

    def repl(match: re.Match) -> str:
        nonlocal counter
        level = int(match.group(1))
        body = match.group(2)
        txt = re.sub(r"<[^>]+>", "", body)
        txt = html.unescape(txt).strip()
        counter += 1
        anchor = f"section-{counter}"
        if level == 2 and txt:
            entries.append((anchor, txt))
        return f'<h{level} id="{anchor}">{body}</h{level}>'

    markup = re.sub(r"<h([123])>(.*?)</h\1>", repl, markup, flags=re.S)
    return markup, entries


def first_heading(source: str, fallback: str) -> str:
    hit = re.search(r"^#\s+(.+)$", source, re.M)
    return hit.group(1).strip() if hit else fallback


def summary(source: str) -> str:
    # Short plain-text excerpt for search; hide Markdown controls.
    clean = re.sub(r"```.*?```", " ", source, flags=re.S)
    clean = re.sub(r"^\s*[#>|*\-]+\s*", "", clean, flags=re.M)
    clean = re.sub(r"\[[^\]]+\]\([^)]*\)", " ", clean)
    clean = re.sub(r"\s+", " ", clean)
    return clean[:175]


def status_chip(p: dict) -> str:
    label, klass = STATUS.get(p["status"], ("待确认", "planning"))
    return f'<span class="status {klass}">{q(label)}</span>'


def project_card(p: dict, current: str, highlight=False) -> str:
    cls = "project-card is-featured" if highlight else "project-card"
    return f'''<a class="{cls}" href="{q(link_for(current, "projects/"+p["slug"]))}">
        <span class="card-kicker">{q(p["category"])}</span>
        <h3>{q(p["title"])}</h3>
        <p>{q(p["description"])}</p>
        <div class="card-bottom">{status_chip(p)} <span class="card-arrow" aria-hidden="true">↗</span></div>
    </a>'''


def video_cards(current: str) -> str:
    cards = []
    for video in VIDEOS:
        p = PROJECT_MAP[video['project']]
        published = video['status'] == 'published'
        video_url = video.get('video_url', '')
        kind = video.get('kind', 'planned')
        label = video.get('display_label') or ('已发布' if published else '待拍摄')
        target = video.get('source_page') or '/projects/' + p['slug'] + '/'
        detail_link = url_for(current, target)
        cover = video.get('cover', '')
        cover_html = (f'<img src="{q(url_for(current, cover))}" loading="lazy" alt="{q(video["title"])} 封面">' if cover else '<span>▶</span>')
        button = (f'<a href="{q(video_url)}" target="_blank" rel="noopener noreferrer" class="video-watch">观看或下载视频 ↗</a>'
                  if published and video_url else '<span class="video-pending">拍摄 / 整理中</span>')
        player = ''
        video_match = re.search(r'/video/(BV[a-zA-Z0-9]+)', video_url)
        if published and video.get('embed') == 'bilibili' and video_match:
            bv = video_match.group(1)
            # Click-to-load frame to avoid sending data to Bilibili until user asks.
            player = f'<div class="video-embed" data-bvid="{q(bv)}"><button type="button" class="load-video">点此加载 B 站播放器</button></div>'
        elif published and video.get('embed') == 'html5':
            poster = f' poster="{q(url_for(current, cover))}"' if cover else ''
            # Source is validated to an approved GitHub Release URL by check.py.
            player = (f'<div class="video-embed video-embed-html5"><video controls playsinline preload="none"{poster}>'
                      f'<source src="{q(video_url)}" type="video/mp4">此浏览器不支持 MP4 播放，可使用上方下载链接。</video></div>')
        disclosure = f'<p class="video-disclosure">{q(video["disclosure"])}</p>' if video.get('disclosure') else ''
        captions = (f'<a class="video-captions" href="{q(video["caption_url"])}" target="_blank" rel="noopener noreferrer">下载字幕 SRT</a>'
                    if video.get('caption_url') else '')
        cards.append(f'''<div class="video-card"><div class="video-cover">{cover_html}<small>{q(p['category'])}</small></div>
          <div class="video-details"><small>{q(label)}</small><h3>{q(video['title'])}</h3><p>{q(video['description'])}</p>
          {button}<a class="video-project" href="{q(detail_link)}">对应图文关卡 ↗</a> {captions}{disclosure}</div>{player}</div>''')
    return '<div class="video-grid">' + ''.join(cards) + '</div>'


def project_of_slug(slug: str):
    parts = slug.split("/")
    if len(parts) >= 2 and parts[0] == "projects":
        return PROJECT_MAP.get(parts[1])
    return None


def current_step(slug: str, project: dict | None):
    if not project:
        return None
    stem = slug.split("/")[-1]
    for step in project.get("steps", []):
        if step["file"].replace(".md", "") == stem:
            return step
    return None


def breadcrumb(slug: str, project: dict | None) -> str:
    parts = [f'<a href="{q(link_for(slug, ""))}">实验室</a>']
    if slug.startswith("projects"):
        parts.append(f'<a href="{q(link_for(slug, "projects"))}">项目目录</a>')
        if project:
            if slug != "projects/" + project["slug"]:
                parts.append(f'<a href="{q(link_for(slug, "projects/"+project["slug"]))}">{q(project["title"])}</a>')
    elif slug.startswith("guide"):
        parts.append(f'<a href="{q(link_for(slug, "guide"))}">新手指南</a>')
    return '<nav class="breadcrumb" aria-label="面包屑导航">' + '<span> / </span>'.join(parts) + '</nav>'


def nav_link(slug: str, target: str, label: str, extra="") -> str:
    active = ' aria-current="page" class="active"' if slug == target else ""
    if extra:
        label += f' <span class="nav-mini">{q(extra)}</span>'
    return f'<a href="{q(link_for(slug, target))}"{active}>{label}</a>'


def sidebar(slug: str, project: dict | None) -> str:
    links = [
        '<div class="sidebar-cap">探索</div>',
        nav_link(slug, "", "总览"),
        nav_link(slug, "projects", "全部项目"),
        nav_link(slug, "guide", "新手指南"),
        nav_link(slug, "videos", "视频工坊"),
        '<div class="sidebar-cap space-above">重点教程</div>',
    ]
    if project:
        root = "projects/" + project["slug"]
        links.append(nav_link(slug, root, q(project["title"])))
    if project and project.get("steps"):
        if (CONTENT / "projects" / project["slug"] / "human-track.md").exists():
            links.append(nav_link(slug, root + "/human-track", "先跟着做 · 人类版"))
        if (CONTENT / "projects" / project["slug"] / "agent-track.md").exists():
            links.append(nav_link(slug, root + "/agent-track", "交给 AI · Agent 版"))
        phase_before = None
        for st in project["steps"]:
            if st["phase"] != phase_before:
                links.append(f'<div class="phase-label">{q(st["phase"])}</div>')
                phase_before = st["phase"]
            subslug = root + "/" + st["file"].removesuffix(".md")
            links.append(f'<div class="step-nav" data-nav-step="{q(project["slug"]+":"+st["id"])}">' + nav_link(slug, subslug, f'<span class="step-num">{q(st["id"])}</span> {q(st["title"])}') + '</div>')
    else:
        links.append(nav_link(slug, "projects/hachimodock", "HachimoDock <span class='nav-mini'>13 关</span>"))
        links.append(nav_link(slug, "guide/agent-first", "有 AI 帮忙的 DIY"))
        links.append(nav_link(slug, "guide/diy-primitives", "DIY 原语与 Agent 分工"))
        links.append(nav_link(slug, "guide/video-production", "DIY 视频制作与工具"))
        links.append(nav_link(slug, "guide/remotion", "Remotion 视频工作流"))
        links.append(nav_link(slug, "guide/new-project", "创建一个新项目"))
        links.append(nav_link(slug, "guide/media", "拍摄、照片与素材"))
        links.append(nav_link(slug, "guide/legal", "版权与事实声明"))
    return '<aside class="sidebar" id="sidebar" aria-label="站点目录">' + "\n".join(links) + '</aside>'


def project_info(project: dict, current_slug: str) -> str:
    total = len(project.get("steps", []))
    progress = f'''<div class="progress-box" data-progress-project="{q(project["slug"])}" data-progress-total="{total}">
        <div class="progress-head"><span>个人学习进度</span><strong class="progress-count">0/{total}</strong></div>
        <div class="progress-track"><span class="progress-fill"></span></div>
        <small>进度只保存在当前浏览器；不是实物验收报告。</small>
    </div>''' if total else ""
    return f'''<div class="project-meta-card">
        <div class="project-meta-top">{status_chip(project)} <span>{q(project["date"])}</span></div>
        <div class="meta-detail"><span>类型</span><strong>{q(project["category"])}</strong></div>
        <div class="meta-detail"><span>预算</span><strong>{q(project["budget"])}</strong></div>
        {progress}
        <a class="meta-home" href="{q(link_for(current_slug, "projects/"+project["slug"]))}">项目总览 ↗</a>
    </div>'''


def right_rail(toc: list, project: dict | None, slug: str) -> str:
    lines = ["<aside class='right-rail' aria-label='文章目录'>"]
    if toc:
        lines.append("<div class='right-title'>本页内容</div>")
        for anchor, txt in toc[:12]:
            lines.append(f'<a href="#{q(anchor)}">{q(txt)}</a>')
    if project:
        lines.append(project_info(project, slug))
    else:
        lines.append('<div class="right-tip">每个项目都有采购、制作、验证、视频和复盘。状态不等于完成保证。</div>')
    lines.append("</aside>")
    return "".join(lines)


def hero_illustration() -> str:
    return '''<div class="hero-art">
        <figure class="work-card work-main">
            <img src="assets/hero-tent.jpg" alt="圣诞互动帐篷 Blender 参数化模型正视图（G0）">
            <figcaption><span>圣诞魔法帐篷 · G0 参数化模型</span><span class="ev-tag">数字模拟</span></figcaption>
        </figure>
        <figure class="work-card work-side">
            <img src="assets/hero-wokwi.png" alt="Wokwi 点灯电路模拟运行截图（LED 已点亮）">
            <figcaption><span>点灯电路 · 已跑通</span><span class="ev-tag ev-run">模拟运行</span></figcaption>
        </figure>
    </div>'''


def hero(current_slug: str) -> str:
    return f'''<section class="hero"><div class="hero-copy"><span class="eyebrow">AI + MAKING · PERSONAL DIY JOURNAL</span>
        <h1>把灵感，<br><span>亲手做出来。</span></h1>
        <p>从 3D 打印、纸工、布艺到电子互动。每一次制作，都留下新手真正能跟着完成的操作、材料、视频和验收记录。</p>
        <div class="hero-actions"><a class="primary-cta" href="{q(link_for(current_slug, "projects/christmas-magic-tent"))}">查看圣诞帐篷制作进展 <span>↗</span></a>
        <a class="secondary-cta" href="{q(link_for(current_slug, "projects"))}">浏览全部项目</a></div>
        <div class="hero-facts"><span>{len(PROJECTS):02d} <small>个项目档案</small></span><span>{len(PROJECT_MAP['hachimodock']['steps']):02d} <small>篇 HachimoDock 关卡教程</small></span><span>01 <small>个可复制模板</small></span></div>
    </div>{hero_illustration()}</section>'''


def chapter_footer(slug: str, p: dict, step: dict) -> str:
    steps = p["steps"]
    i = steps.index(step)
    root = "projects/" + p["slug"]
    prev_step = steps[i - 1] if i > 0 else None
    next_step = steps[i + 1] if i + 1 < len(steps) else None
    nav = ['<div class="chapter-nav">']
    if prev_step:
        target = root + "/" + prev_step["file"].removesuffix(".md")
        nav.append(f'<a href="{q(link_for(slug,target))}"><small>← 上一关</small><strong>{q(prev_step["title"])}</strong></a>')
    else:
        nav.append('<span></span>')
    if next_step:
        target = root + "/" + next_step["file"].removesuffix(".md")
        nav.append(f'<a class="next" href="{q(link_for(slug,target))}"><small>下一关 →</small><strong>{q(next_step["title"])}</strong></a>')
    else:
        nav.append(f'<a class="next" href="{q(link_for(slug,root))}"><small>返回</small><strong>项目总览</strong></a>')
    nav.append('</div>')
    return "".join(nav)


# 页面勾选语义（遵循 mayf3/primitives design 0.2.0 APPLICATION §1 状态主体）：
# - 来源中已勾选（- [x]）= 作者事实，渲染为只读徽章，任何脚本不得改写；
# - 未勾选（- [ ]）默认也是作者记录（◻ 未完成，只读）；
# - 只有注册为"步骤页"的页面（projects.json steps）里的清单才是访客个人进度，
#   用内容哈希作稳定键，插入/重排不会串项，接入 localStorage。
COLLAPSED_SECTIONS = {
    "projects/christmas-magic-tent": (
        "当前进展", "G1 第一轮商品搜寻", "G2-V1 电子数字模拟", "G2-V2 与 G1a 预算收敛",
        "帐篷采购放行", "先模拟，不购物", "已记录但尚未冻结",
    ),
}


def personal_slugs() -> set:
    return {f"projects/{p['slug']}/{s['file'].removesuffix('.md')}" for p in PROJECTS for s in p.get("steps", [])}


def transform_checklists(markup: str, slug: str) -> str:
    personal = slug in personal_slugs()
    heading = ""
    out = []
    pos = 0
    pattern = re.compile(r'(<h[23][^>]*>.*?</h[23]>)|(<li class="task-list-item">.*?</li>)', re.S)
    for m in pattern.finditer(markup):
        out.append(markup[pos:m.start()])
        seg = m.group(0)
        if seg.startswith('<h2') or seg.startswith('<h3'):
            heading = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', seg))).strip()
            out.append(seg)
        elif '<input' not in seg:
            out.append(seg)
        else:
            li = seg
            text = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', li))).strip()
            inp = re.search(r'<input[^>]*>', li).group(0)
            if 'checked' in inp:
                li = li.replace(inp, '<span class="fact-mark" title="作者记录（只读）">✅ 已完成</span>')
                li = li.replace('task-list-item', 'task-list-item fact-item', 1)
            elif not personal:
                li = li.replace(inp, '<span class="fact-mark pending" title="作者记录（只读）">◻ 未完成</span>')
                li = li.replace('task-list-item', 'task-list-item fact-item', 1)
            else:
                key = hashlib.sha1((slug + '|' + heading + '|' + text).encode('utf-8')).hexdigest()[:12]
                new_inp = re.sub(r'\s+disabled|\s+checked', '', inp)
                new_inp = new_inp[:-2] + f' data-personal-key="{key}">' if new_inp.endswith('/>') else new_inp[:-1] + f' data-personal-key="{key}">'
                li = li.replace(inp, new_inp)
            out.append(li)
        pos = m.end()
    out.append(markup[pos:])
    return ''.join(out)


def collapse_sections(markup: str, slug: str) -> str:
    prefixes = COLLAPSED_SECTIONS.get(slug)
    if not prefixes:
        return markup
    parts = re.split(r'(<h2[^>]*>.*?</h2>)', markup, flags=re.S)
    out = [parts[0]]
    i = 1
    while i < len(parts):
        head = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        text = html.unescape(re.sub(r'<[^>]+>', '', head)).strip()
        if any(p in text for p in prefixes):
            out.append(f'<details class="history-block"><summary>{head}</summary><div class="history-body">')
            out.append(body)
            out.append('</div></details>')
        else:
            out.append(head)
            out.append(body)
        i += 2
    return ''.join(out)


def render_one(source: Path) -> tuple[str, dict]:
    slug = slug_from_source(source)
    body = source.read_text(encoding="utf-8")
    title = first_heading(body, "Maker Lab")
    project = project_of_slug(slug)
    step = current_step(slug, project)
    markup, toc = toc_and_anchors(md(rewrite_md_links(body, slug)))
    markup = transform_checklists(markup, slug)
    markup = collapse_sections(markup, slug)
    is_home = slug == ""
    if is_home:
        main_top = hero(slug)
        article = markup.replace("<h1", "<h1 class=\"sr-only\"", 1)
        extra = '<section class="catalog-section"><div class="section-intro"><span class="eyebrow">PROJECT INDEX</span><h2>项目进行时</h2><p>真实进度透明呈现；选一个作品，打开教程继续做。</p></div><div class="project-grid">' + ''.join(project_card(p,slug, i==0) for i,p in enumerate(PROJECTS)) + '</div></section>'
        extra += '<section class="process-section"><span class="eyebrow">THE MAKER METHOD</span><h2>不是一键生成，而是六个踏实的环节</h2><div class="process-grid">' + ''.join(f'<div><span>0{i+1}</span><b>{q(name)}</b><p>{q(desc)}</p></div>' for i,(name,desc) in enumerate([("构思","目标和需求"),("验证","尺寸、接口与风险"),("采购","型号、预算与来源"),("制作","打印、焊接与装配"),("验收","真实测试和证据"),("分享","视频、文件与复盘")])) + '</div></section>'
        article = main_top + '<div class="home-body">' + article + '</div>' + extra
    elif slug == "projects":
        article = markup + '<div class="project-grid">' + ''.join(project_card(p, slug) for p in PROJECTS) + '</div>'
    elif slug == "videos":
        article = markup.replace('<h2', '<h2', 1)
        article = article.replace('视频目录</h2>', '视频目录</h2>' + video_cards(slug))
    else:
        article = markup
    stepid = project["slug"]+":"+step["id"] if project and step else ""
    stephead = f'''<div class="chapter-stephead"><span class="step-tag">{q(step["phase"])} / {q(step["id"])}</span><span>建议耗时 {q(step["minutes"])}</span></div>''' if step else ""
    complete = f'''<div class="complete-bar" data-chapter="{q(stepid)}"><div><strong>本章操作已通过？</strong><p>完成所有勾选项后可标记本章完成。个人进度只存储在浏览器。</p></div><button class="complete-toggle" disabled type="button">完成本章</button></div>''' if step else ""
    if step:
        article = stephead + article + complete + chapter_footer(slug,project,step)
    is_project_root = project and slug == "projects/"+project["slug"]
    if is_project_root and project.get("steps"):
        article += '<div class="start-banner"><div><span class="eyebrow">STEP-BY-STEP</span><h2>从第一步开始</h2><p>按顺序完成；每一关都有实际操作、验收和故障提示。</p></div><a class="primary-cta" href="' + q(link_for(slug,slug+"/"+project["steps"][0]["file"].removesuffix(".md"))) + '">开始制作 ↗</a></div>'
    sidebar_html = sidebar(slug, project)
    rail = right_rail(toc,project,slug)
    root_prefix = os.path.relpath(DIST, output_path(slug).parent).replace("\\", "/")
    if root_prefix == ".":
        root_prefix = "./"
    else:
        root_prefix += "/"
    stylesheet = q(url_for(slug,"/assets/style.css"))
    visual_css = q(url_for(slug,"/assets/vendor/mayf3-visual/0.1.0/seaside.css"))
    bv = build_version()
    js = q(url_for(slug,"/assets/main.js") + f"?v={bv}")
    search = q(url_for(slug,"/assets/search-index.js") + f"?v={bv}")
    home = q(link_for(slug,""))
    projects = q(link_for(slug,"projects"))
    guide = q(link_for(slug,"guide"))
    cls = "home-page" if is_home else ("project-root" if is_project_root else "content-page")
    html_page = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{q(summary(body))}"><meta name="color-scheme" content="light">
<title>{q(title)} · Maker Lab</title><link rel="stylesheet" href="{visual_css}"><link rel="stylesheet" href="{stylesheet}"><link rel="icon" href="{q(url_for(slug,"/assets/favicon.svg"))}" type="image/svg+xml"></head>
<body class="mf-theme-seaside {cls}" data-root="{q(root_prefix)}" data-project="{q(project["slug"] if project else "")}">
<header class="topbar"><div class="topbar-inner"><button class="menu-toggle" id="menuToggle" type="button" aria-controls="sidebar" aria-expanded="false" aria-label="打开导航">☰</button>
<a class="brand" href="{home}"><span class="brand-symbol">M<span>·</span></span><span class="brand-name">MAKER <b>LAB</b></span><small>AI DIY JOURNAL</small></a>
<nav class="top-nav" aria-label="顶部导航"><a href="{home}">首页</a><a href="{projects}">所有项目</a><a href="{q(link_for(slug,"videos"))}">视频工坊</a><a href="{guide}">新手指南</a></nav>
<button class="search-button" id="searchOpen" type="button" aria-label="搜索教程"><span class="search-lens">⌕</span><span>搜索教程</span><kbd>/</kbd></button></div></header>
<div class="site-layout">{sidebar_html}<main id="mainContent" class="main-content" tabindex="-1">{'' if is_home else breadcrumb(slug,project)}
<article class="doc-content">{article}</article><footer class="footer"><div class="family-nav">Mayf3 三站：<a href="https://learn.mayf3.com/">Learning Lab · 学习</a> · <a href="https://map.mayf3.com/">Podcast Map · 探索</a> · <strong>Maker Lab · 创造（本站）</strong></div><br>Maker Lab · 用真实动手验证每一步。本站为独立学习记录，与上游项目无官方合作关系。<br>始建 2026-11-06 · 最近更新 {BUILD_DATE} · <a href="{q(link_for(slug,"guide/legal"))}">许可与来源</a> · <a href="{q(link_for(slug,"guide/new-project"))}">新增项目</a></footer></main>{rail}</div>
<div id="mobileOverlay" class="mobile-overlay" hidden></div><div class="search-modal" id="searchModal" role="dialog" aria-modal="true" aria-label="搜索教程" hidden><div class="search-panel"><div class="search-top"><input id="searchInput" placeholder="搜索项目、材料、步骤或问题…" aria-label="搜索关键词" autocomplete="off"><button type="button" id="searchClose" aria-label="关闭搜索">✕</button></div><div id="searchResults" class="search-results"><p>输入关键词，搜索全站教程。</p></div><div class="search-help">按 Esc 关闭 · 离线也可以搜索</div></div></div>
<script defer src="{search}"></script><script defer src="{js}"></script></body></html>'''
    metadata = {"title":title,"summary":summary(body),"path": str(output_path(slug).relative_to(DIST)).replace("\\","/"),"slug":slug}
    return html_page,metadata


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    shutil.copytree(ROOT / "assets",DIST / "assets")
    shutil.copytree(ROOT / "public/media",DIST / "media")
    (DIST / "downloads").mkdir()
    for filename in ('bom.csv', 'blockers.csv', 'sources.csv'):
        for src in (ROOT / 'source-data').glob(f'*/{filename}'):
            shutil.copy2(src, DIST / 'downloads' / (src.parent.name + '-' + filename))
    (DIST / ".nojekyll").write_text("", encoding="utf-8")
    pages=[]
    for path in sorted(CONTENT.rglob("*.md")):
        slug=slug_from_source(path)
        result,meta=render_one(path)
        target=output_path(slug)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(result,encoding="utf-8")
        pages.append(meta)
    search_data=[{"title":p["title"],"summary":p["summary"],"path":p["path"]} for p in pages]
    (DIST / "assets/search-index.js").write_text("window.MAKER_SEARCH_INDEX="+json.dumps(search_data,ensure_ascii=False,separators=(',',':'))+";window.MAKER_PROJECT_STEPS="+json.dumps({p['slug']:[s['id'] for s in p.get('steps',[])] for p in PROJECTS},ensure_ascii=False,separators=(',',':'))+";",encoding="utf-8")
    (DIST / "404.html").write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>页面未找到 · Maker Lab</title><p>页面不存在，<a href="https://diy-lab.mayf3.com/">返回首页（大陆镜像）</a> 或 <a href="https://mayf3.github.io/diy-lab/">GitHub Pages 版</a>。</p></html>',encoding="utf-8")
    mirror = Path.home() / "Library" / "Application Support" / "MakerLabSite"
    if mirror.is_dir():
        shutil.rmtree(mirror)
        shutil.copytree(DIST, mirror)
        print(f"Synced local service mirror: {mirror}")
    print(f"Built {len(pages)} pages into {DIST} (builder {GENERATOR_VERSION})")

if __name__=="__main__":
    main()
