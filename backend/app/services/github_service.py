import re
from typing import Dict, Any, List, Optional
import httpx
from app.config import settings

def extract_username(url_or_username: str) -> Optional[str]:
    """Extracts username from either full URL or direct username."""
    if not url_or_username:
        return None
    cleaned = url_or_username.strip()
    # Check if URL
    match = re.search(r'github\.com/([a-zA-Z0-9_-]+)', cleaned)
    if match:
        return match.group(1)
    # Check if raw username
    cleaned = cleaned.lstrip("@").strip("/")
    if re.match(r'^[a-zA-Z0-9_-]+$', cleaned):
        return cleaned
    return None

async def fetch_github_profile_data(username_or_url: str) -> Dict[str, Any]:
    """
    Fetches public GitHub profile and repositories for a student.
    Identifies AI/ML projects and provides structured evidence.
    """
    username = extract_username(username_or_url)
    if not username:
        return {"error": "Invalid GitHub username or URL format", "ai_ml_projects": []}
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ScholarSwarm-Agent/1.0"
    }
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"
        
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # 1. Fetch user info
            user_res = await client.get(f"https://api.github.com/users/{username}", headers=headers)
            if user_res.status_code == 404:
                return {"error": f"GitHub user '{username}' not found", "ai_ml_projects": []}
            elif user_res.status_code == 403:
                return {"error": "GitHub API rate limit exceeded or access forbidden", "ai_ml_projects": []}
            elif user_res.status_code != 200:
                return {"error": f"GitHub API error: status {user_res.status_code}", "ai_ml_projects": []}
                
            user_data = user_res.json()
            
            # 2. Fetch public repos
            repos_res = await client.get(
                f"https://api.github.com/users/{username}/repos?sort=updated&per_page=15",
                headers=headers
            )
            repos_data = repos_res.json() if repos_res.status_code == 200 else []
            
            ai_keywords = {"ai", "ml", "machine-learning", "deep-learning", "nlp", "vision", "pytorch", "tensorflow", "transformer", "llm", "swarm", "neural"}
            
            ai_projects = []
            all_projects = []
            for repo in repos_data:
                name = repo.get("name", "")
                desc = repo.get("description") or ""
                lang = repo.get("language") or ""
                stars = repo.get("stargazers_count", 0)
                topics = repo.get("topics", [])
                
                # Check if AI/ML related
                text_to_check = f"{name} {desc} {' '.join(topics)}".lower()
                is_ai = any(kw in text_to_check for kw in ai_keywords) or (lang.lower() == "jupyter notebook")
                
                proj_info = {
                    "title": name,
                    "description": desc,
                    "technologies": [lang] if lang else [],
                    "repo_url": repo.get("html_url"),
                    "stars": stars,
                    "is_ai_ml": is_ai,
                    "evidence_source": "github"
                }
                all_projects.append(proj_info)
                if is_ai:
                    ai_projects.append(proj_info)
                    
            return {
                "username": username,
                "name": user_data.get("name") or username,
                "bio": user_data.get("bio"),
                "public_repos_count": user_data.get("public_repos", 0),
                "ai_ml_projects": ai_projects,
                "all_projects": all_projects,
                "has_ai_experience": len(ai_projects) > 0,
                "profile_url": f"https://github.com/{username}"
            }
        except httpx.RequestError as e:
            return {"error": f"Network error contacting GitHub API: {str(e)}", "ai_ml_projects": []}
