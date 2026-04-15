"""Blog routes with markdown support."""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import markdown
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/blog", tags=["blog"])

# Blog configuration
BLOG_POSTS_DIR = Path("app/blog_posts")
POSTS_PER_PAGE = 10

class BlogPost:
    """Represents a blog post parsed from markdown."""
    
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.slug = filepath.stem
        self.parse_content()
    
    def parse_content(self):
        """Parse markdown file and extract metadata."""
        if not self.filepath.exists():
            raise FileNotFoundError(f"Blog post not found: {self.filepath}")
        
        content = self.filepath.read_text(encoding='utf-8')
        
        # Parse frontmatter (YAML-like metadata at the top)
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter = parts[1].strip()
                markdown_content = parts[2].strip()
            else:
                frontmatter = ""
                markdown_content = content
        else:
            frontmatter = ""
            markdown_content = content
        
        # Parse metadata from frontmatter
        self.metadata = {}
        for line in frontmatter.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip().strip('"\'')
                
                if key == 'tags':
                    self.metadata[key] = [tag.strip() for tag in value.split(',')]
                elif key == 'date':
                    try:
                        self.metadata[key] = datetime.strptime(value, '%Y-%m-%d')
                    except ValueError:
                        self.metadata[key] = datetime.now()
                else:
                    self.metadata[key] = value
        
        # Convert markdown to HTML
        md = markdown.Markdown(extensions=['codehilite', 'tables', 'toc'])
        self.content = md.convert(markdown_content)
        
        # Extract excerpt (first paragraph or first 150 chars)
        excerpt_match = re.search(r'<p>(.*?)</p>', self.content)
        if excerpt_match:
            excerpt = excerpt_match.group(1)
            if len(excerpt) > 150:
                excerpt = excerpt[:150] + "..."
        else:
            plain_text = re.sub(r'<[^>]+>', '', self.content)
            excerpt = plain_text[:150] + "..." if len(plain_text) > 150 else plain_text
        
        self.excerpt = excerpt
        
        # Calculate read time (average 200 words per minute)
        word_count = len(re.findall(r'\w+', re.sub(r'<[^>]+>', '', self.content)))
        self.read_time = max(1, round(word_count / 200))
    
    @property
    def title(self) -> str:
        return self.metadata.get('title', self.slug.replace('-', ' ').title())
    
    @property
    def author(self) -> str:
        return self.metadata.get('author', 'JobLook Team')
    
    @property
    def author_title(self) -> str:
        return self.metadata.get('author_title', '')
    
    @property
    def author_avatar(self) -> str:
        return self.metadata.get('author_avatar', '')
    
    @property
    def date(self) -> datetime:
        return self.metadata.get('date', datetime.now())
    
    @property
    def category(self) -> str:
        return self.metadata.get('category', 'General')
    
    @property
    def tags(self) -> list[str]:
        return self.metadata.get('tags', [])
    
    @property
    def featured_image(self) -> str:
        return self.metadata.get('featured_image', '')
    
    @property
    def published(self) -> bool:
        return self.metadata.get('published', 'true').lower() == 'true'

def get_all_posts() -> list[BlogPost]:
    """Get all published blog posts sorted by date (newest first)."""
    if not BLOG_POSTS_DIR.exists():
        return []
    
    posts = []
    for filepath in BLOG_POSTS_DIR.glob("*.md"):
        try:
            post = BlogPost(filepath)
            if post.published:
                posts.append(post)
        except Exception:
            # Skip invalid posts
            continue
    
    return sorted(posts, key=lambda p: p.date, reverse=True)

def get_post_by_slug(slug: str) -> BlogPost | None:
    """Get a specific post by its slug."""
    filepath = BLOG_POSTS_DIR / f"{slug}.md"
    try:
        post = BlogPost(filepath)
        return post if post.published else None
    except FileNotFoundError:
        return None

@router.get("/", response_class=HTMLResponse)
def blog_index(request: Request, page: int = 1, category: str = None, tag: str = None):
    """Blog homepage with post listing."""
    all_posts = get_all_posts()
    
    # Filter by category or tag if specified
    if category:
        all_posts = [p for p in all_posts if p.category.lower() == category.lower()]
    if tag:
        all_posts = [p for p in all_posts if tag.lower() in [t.lower() for t in p.tags]]
    
    # Pagination
    total_posts = len(all_posts)
    start_idx = (page - 1) * POSTS_PER_PAGE
    end_idx = start_idx + POSTS_PER_PAGE
    posts = all_posts[start_idx:end_idx]
    
    # Calculate pagination info
    total_pages = (total_posts + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE
    has_prev = page > 1
    has_next = page < total_pages
    prev_page = page - 1 if has_prev else None
    next_page = page + 1 if has_next else None
    
    return templates.TemplateResponse(
        request, "blog.html",
        {
            "posts": posts,
            "current_page": page,
            "total_pages": total_pages,
            "prev_page": prev_page,
            "next_page": next_page,
            "category_filter": category,
            "tag_filter": tag,
        }
    )

@router.get("/{slug}", response_class=HTMLResponse)
def blog_post(request: Request, slug: str):
    """Individual blog post page."""
    post = get_post_by_slug(slug)
    if not post:
        raise HTTPException(status_code=404, detail="Blog post not found")
    
    # Get related posts (same category, excluding current post)
    all_posts = get_all_posts()
    related_posts = [
        p for p in all_posts 
        if p.category == post.category and p.slug != post.slug
    ][:3]  # Limit to 3 related posts
    
    return templates.TemplateResponse(
        request, "blog_post.html",
        {
            "post": post,
            "related_posts": related_posts,
        }
    )