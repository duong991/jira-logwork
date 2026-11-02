import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import requests
import yaml
from mcp.server.fastmcp import FastMCP


def _valid_jira_time(value: str) -> bool:
    return bool(re.fullmatch(r"(\d+w\s*)?(\d+d\s*)?(\d+h\s*)?(\d+m\s*)?", value.strip()) and value.strip())

CONFIG_PATH = Path(__file__).parent / "config.yaml"

SIDES = ("BE", "FE", "BE-FE")
FRONTEND_SERVICES = ()

AI_AUTHORSHIP = re.compile(r"\bclaude\b|\banthropic\b|co-authored-by|generated (with|by) (ai|an ai|claude)", re.IGNORECASE)

mcp = FastMCP("jira-work-logger", instructions=(
    "Use this server to scan git repos for daily work and create/update Jira tickets. "
    "Typical flow: 1) call scan_daily_work to see what was done, "
    "2) call create_jira_ticket for each logical piece of work. "
    "Ticket title convention: [BE] service-name: description, or [FE] for frontend work (create_jira_ticket adds it). "
    "Failed calls return an error whose first line is 'jira-work-logger · <category> · retryable|not retryable', "
    "followed by Problem and Fix lines; follow the Fix line and only retry when it says retryable."
))


class ToolError(Exception):
    def __init__(self, category: str, retryable: bool, problem: str, fix: str):
        super().__init__(problem)
        self.category = category
        self.retryable = retryable
        self.problem = problem
        self.fix = fix

    def __str__(self):
        return "\n".join([
            f"jira-work-logger · {self.category} · {'retryable' if self.retryable else 'not retryable'}",
            f"Problem: {self.problem}",
            f"Fix: {self.fix}",
        ])


def load_config():
    try:
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as e:
        raise ToolError("config", False, f"could not read {CONFIG_PATH} ({type(e).__name__}).", "tell the user the jira-work-logger config is missing or broken.")


_server_type_cache = {}


def _is_jira_server(config):
    jira_cfg = config.get("jira", {})
    if jira_cfg.get("server_type"):
        return str(jira_cfg["server_type"]).lower() == "server"
    url = jira_cfg.get("url", "").rstrip("/")
    if not url:
        return False
    if url in _server_type_cache:
        return _server_type_cache[url]
    if "atlassian.net" in url:
        _server_type_cache[url] = False
        return False
    try:
        r = requests.get(f"{url}/rest/api/2/serverInfo", timeout=5)
        if r.status_code == 200 and r.json().get("deploymentType") == "Server":
            _server_type_cache[url] = True
            return True
    except Exception:
        pass
    _server_type_cache[url] = False
    return False


def jira_headers(config):
    import base64
    jira_cfg = config.get("jira", {})
    pat = jira_cfg.get("personal_access_token")
    if pat:
        auth_header = f"Bearer {pat.strip()}"
    elif jira_cfg.get("auth_type") == "bearer":
        auth_header = f"Bearer {jira_cfg.get('api_token', '').strip()}"
    else:
        user = jira_cfg.get("username") or jira_cfg.get("email") or ""
        secret = jira_cfg.get("password") or jira_cfg.get("api_token") or ""
        if not user and secret and _is_jira_server(config):
            auth_header = f"Bearer {secret.strip()}"
        else:
            creds = f"{user}:{secret}"
            auth_header = f"Basic {base64.b64encode(creds.encode()).decode()}"

    return {
        "Authorization": auth_header,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _jira_url(config, path):
    api_ver = "latest" if _is_jira_server(config) else "3"
    return f"{config['jira']['url'].rstrip('/')}/rest/api/{api_ver}{path}"


def _jira(config, method, path, action, ok=(200, 201, 204), **kwargs):
    try:
        resp = requests.request(method, _jira_url(config, path), headers=jira_headers(config), timeout=30, **kwargs)
    except requests.RequestException as e:
        raise ToolError("network", True, f"could not reach Jira to {action} ({type(e).__name__}).", "retry once; if it fails again, tell the user Jira looks unreachable.")
    if resp.status_code not in ok:
        raise _jira_failure(resp, action)
    return resp


def _jira_detail(resp):
    try:
        body = resp.json()
        parts = list(body.get("errorMessages", [])) + [f"{k}: {v}" for k, v in body.get("errors", {}).items()]
        detail = "; ".join(parts)
    except ValueError:
        detail = resp.text
    return (detail or "no details").strip()[:300]


def _jira_failure(resp, action):
    status = resp.status_code
    detail = _jira_detail(resp)
    if status == 401:
        return ToolError("auth", False, f"Jira rejected the API token while trying to {action} (401).",
                         "do not retry. Ask the user to create a new API token at id.atlassian.com and put it in config.yaml next to server.py.")
    if status == 403:
        return ToolError("permission", False, f"this account may not {action} (403): {detail}", "do not retry; tell the user which permission is missing.")
    if status == 404:
        return ToolError("not_found", False, f"Jira found nothing to {action} (404): {detail}", "check the ticket key or project, then call again with the right one.")
    if status == 429 or status >= 500:
        return ToolError("transient", True, f"Jira failed to {action} ({status}): {detail}", "wait a few seconds and retry once.")
    return ToolError("validation", False, f"Jira refused to {action} ({status}): {detail}", "fix the fields Jira names, then call again.")


def _reject_ai_authorship(*texts):
    for text in texts:
        match = AI_AUTHORSHIP.search(text or "")
        if match:
            raise ToolError("validation", False, f"Jira text must not mention Claude/AI authorship; found \"{match.group(0)}\".",
                            "remove it from the title and description, then call again.")


def _get_my_account_info(config):
    data = _jira(config, "GET", "/myself", "look up your account").json()
    if "accountId" in data:
        return {"accountId": data["accountId"]}
    if "name" in data:
        return {"name": data["name"]}
    if "key" in data:
        return {"name": data["key"]}
    raise ToolError("auth", False, "could not determine Jira user identifier from /myself.", "check Jira user permissions.")


def _repo_name(repo_path):
    result = subprocess.run(["git", "remote", "get-url", "origin"], cwd=repo_path, capture_output=True, text=True, timeout=10)
    url = result.stdout.strip() if result.returncode == 0 else ""
    return url, (re.sub(r"\.git$", "", url.rstrip("/").split("/")[-1]) if url else os.path.basename(repo_path))


def _work_repos(config):
    git = config["git"]
    candidates = []
    for root in git.get("repo_roots", []):
        root = os.path.expanduser(root)
        if os.path.isdir(root):
            candidates += [e.path for e in sorted(os.scandir(root), key=lambda e: e.name) if os.path.isdir(os.path.join(e.path, ".git"))]
    missing = []
    for repo in git.get("repos", []) or []:
        repo = os.path.expanduser(repo)
        if os.path.isdir(repo):
            candidates.append(repo)
        else:
            missing.append(repo)
    orgs = git.get("remote_orgs", [])
    repos = []
    for path in dict.fromkeys(candidates):
        try:
            url, name = _repo_name(path)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            missing.append(path)
            continue
        if orgs and not any(re.search(rf"[:/]{re.escape(org)}/", url) for org in orgs):
            continue
        repos.append((path, name))
    return repos, missing


def _get_commits(repo_path, author_email, date_str):
    """Get commits for a specific date from a repo."""
    since = f"{date_str}T00:00:00"
    until_date = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)
    until = until_date.strftime("%Y-%m-%dT00:00:00")

    if isinstance(author_email, str):
        emails = [author_email]
    else:
        emails = list(author_email)

    author_flags = [f"--author={e}" for e in emails]

    result = subprocess.run(
        ["git", "log"] + author_flags + [
            f"--since={since}", f"--until={until}",
            "--all", "--pretty=format:%H|||%s|||%ai", "--no-merges"
        ],
        cwd=repo_path, capture_output=True, text=True, timeout=20
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip().splitlines()[0] if result.stderr.strip() else f"git exited {result.returncode}")

    commits = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|||")
        if len(parts) == 3:
            commits.append({
                "hash": parts[0],
                "message": parts[1],
                "date": parts[2],
            })
    return commits


def _get_diff_stats(repo_path, commit_hash):
    """Get diff stats for a commit."""
    try:
        result = subprocess.run(
            ["git", "diff", "--stat", f"{commit_hash}~1", commit_hash],
            cwd=repo_path, capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


@mcp.tool()
def scan_daily_work(date: str = "") -> str:
    """List the user's own git commits (all branches, merges excluded) on one day across their work repos.

    Work repos are every git clone directly under the configured repo_roots whose origin is in
    a configured GitHub org, so personal repos never show up. Worktrees share their clone's history and
    are not scanned twice; a commit seen in two clones, or rewritten with the same message and author date, is
    listed once, under the repo name from the origin URL.
    Commits made on GitHub itself (web edits, squash merges) are not local; use `gh search commits` for those.

    Args:
        date: Day to scan, YYYY-MM-DD. Defaults to today (local time).

    Returns:
        Commits and diff stats grouped by repo, followed by any repos that could not be scanned.
    """
    config = load_config()
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise ToolError("validation", False, f"date '{date}' is not YYYY-MM-DD.", "call again with a date like 2026-10-08.")

    author_emails = config["git"].get("author_emails") or [config["git"].get("author_email", "")]
    repos, missing = _work_repos(config)
    if not repos:
        raise ToolError("config", False, "no work repos found under the configured repo_roots/repos.",
                        "tell the user to check the git section of config.yaml next to server.py.")

    seen = set()
    results = []
    failed = []
    for repo_path, service_name in repos:
        try:
            commits = []
            for c in _get_commits(repo_path, author_emails, date):
                same = (service_name, c["message"], c["date"])
                if c["hash"] in seen or same in seen:
                    continue
                seen.update([c["hash"], same])
                commits.append(c)
        except (subprocess.TimeoutExpired, FileNotFoundError, RuntimeError) as e:
            failed.append(f"{service_name} ({repo_path}): {e}")
            continue
        if not commits:
            continue
        diff_stats = [_get_diff_stats(repo_path, c["hash"]) for c in commits]
        existing = next((r for r in results if r["service"] == service_name), None)
        if existing:
            existing["commits"] += commits
            existing["diff_stats"] += diff_stats
        else:
            results.append({"service": service_name, "repo_path": repo_path, "commits": commits, "diff_stats": diff_stats})

    authors_label = ", ".join(author_emails) if isinstance(author_emails, list) else author_emails
    output = [f"## Work summary for {date} ({len(repos)} repos scanned, authors: {authors_label})\n"]
    if not results:
        output.append("No commits found.\n")
    for r in results:
        output.append(f"### {r['service']} ({len(r['commits'])} commits)")
        for i, c in enumerate(r["commits"]):
            output.append(f"- {c['message']}")
            if r["diff_stats"][i]:
                output.append(f"  ```\n  {r['diff_stats'][i]}\n  ```")
        output.append("")
    if failed or missing:
        output.append("### Not scanned (results may be incomplete)")
        output += [f"- could not scan {f}" for f in failed]
        output += [f"- configured repo not found: {m}" for m in missing]

    return "\n".join(output)


@mcp.tool()
def create_jira_ticket(
    service_name: str,
    title: str,
    summary: str,
    time_estimate: str = "3h",
    time_spent: str = "",
    task_type: str = "development",
    side: str = "",
    sprint_id: int = 0,
    due_date: str = "",
) -> str:
    """Create a Jira ticket in the configured project (jira.project_key), assigned to the user, for work done on a service.

    The title is written as "[SIDE] service-name: title", e.g. "[BE] orders-service: ..." or "[FE] admin-web: ...".
    Pass only the description as title; the prefix and service name are added here.
    Title and summary must not mention Claude or AI authorship; such calls are refused.

    Args:
        service_name: Name of the service (e.g., 'orders-service').
        title: Short description of the work done.
        summary: What was done and why, in plain text.
        time_estimate: Time estimate in Jira format — e.g., '3h', '6h', '1d 4h', '3d'.
        time_spent: Time to log as spent — e.g., '2h', '1d' (optional).
        task_type: Task type, one of defaults.task_type_options when a task_type_field is configured. Defaults to 'development'.
        side: 'BE', 'FE' or 'BE-FE'. Leave empty to use FE for repos listed in defaults.frontend_services and BE otherwise.
        sprint_id: Optional sprint ID (defaults to active sprint SAFEKIDS Sprint 19 / 48756).
        due_date: Optional due date in YYYY-MM-DD format (defaults to end of current month).

    Returns:
        Created ticket key and URL. Errors start with 'jira-work-logger · <category> · retryable|not retryable'.
    """
    if not _valid_jira_time(time_estimate):
        raise ToolError("validation", False, f"time_estimate '{time_estimate}' is not a Jira duration.", "call again with e.g. '3h', '1d 4h' or '3d'.")
    if time_spent and not _valid_jira_time(time_spent):
        raise ToolError("validation", False, f"time_spent '{time_spent}' is not a Jira duration.", "call again with e.g. '2h' or '1d'.")

    _reject_ai_authorship(service_name, title, summary)

    config = load_config()
    defaults = config.get("defaults", {})
    task_field = defaults.get("task_type_field")
    task_type_map = {str(k).lower(): str(v) for k, v in (defaults.get("task_type_options") or {}).items()}
    if task_field and task_type.lower() not in task_type_map:
        raise ToolError("validation", False, f"task_type '{task_type}' is not allowed.", f"call again with one of {', '.join(task_type_map)}.")
    service = service_name.strip().lower()
    frontend = {s.lower() for s in config.get("defaults", {}).get("frontend_services", FRONTEND_SERVICES)}
    side = side.strip().upper() or ("FE" if service in frontend else "BE")
    if side not in SIDES:
        raise ToolError("validation", False, f"side '{side}' is not allowed.", f"call again with one of {', '.join(SIDES)}, or leave it empty.")
    prefix = re.match(rf"\s*\[[A-Z-]+\]\s*(?:{re.escape(service)}\s*:)?\s*", title, re.IGNORECASE)
    description = (title[prefix.end():] if prefix else title).strip()
    if not description:
        raise ToolError("validation", False, "title is empty after removing the prefix.", "call again with a short description of the work as title.")

    account_info = _get_my_account_info(config)

    full_title = f"[{side}] {service}: {description}"

    if _is_jira_server(config):
        desc_payload = summary
    else:
        desc_payload = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": summary}]
                }
            ]
        }

    now = datetime.now()
    if not due_date:
        next_month = now.replace(day=28) + timedelta(days=4)
        last_day = next_month - timedelta(days=next_month.day)
        due_date = last_day.strftime("%Y-%m-%d")

    payload = {
        "fields": {
            "project": {"key": config["jira"]["project_key"]},
            "summary": full_title,
            "description": desc_payload,
            "issuetype": {"name": config["defaults"]["issue_type"]},
            "assignee": account_info,
            "duedate": due_date,
            "timetracking": {
                "originalEstimate": time_estimate,
            },
        }
    }

    # Cấu hình bắt buộc VNPT theo chuẩn dự án NCPTWORK (như ảnh hướng dẫn):
    # 1. Công đoạn: Nghiên cứu, phát triển, nâng cấp (id: 13000)
    # 2. Mã SPDA: ATTT -> Chung/CPCATTTT (id: 13100, child: 13270)
    cf_config = config.get("defaults", {}).get("custom_fields", {})
    if "cong_doan" in cf_config:
        payload["fields"][cf_config["cong_doan"]["field_id"]] = {"id": str(cf_config["cong_doan"]["option_id"])}
    else:
        payload["fields"]["customfield_13000"] = {"id": "13000"}

    if "ma_spda" in cf_config:
        payload["fields"][cf_config["ma_spda"]["field_id"]] = {
            "id": str(cf_config["ma_spda"]["parent_id"]),
            "child": {"id": str(cf_config["ma_spda"]["child_id"])},
        }
    else:
        payload["fields"]["customfield_13100"] = {"id": "13100", "child": {"id": "13270"}}

    if task_field:
        payload["fields"][task_field] = {"id": task_type_map[task_type.lower()]}

    resp = _jira(config, "POST", "/issue", "create the ticket", ok=(201, 400), json=payload)

    if resp.status_code == 400:
        try:
            field_errors = resp.json().get("errors", {})
        except ValueError:
            field_errors = {}
        unsettable = [
            f for f, msg in field_errors.items()
            if "not on the appropriate screen" in msg or "cannot be set" in msg
        ]
        if not unsettable:
            raise _jira_failure(resp, "create the ticket")
        for f in unsettable:
            payload["fields"].pop(f, None)
        resp = _jira(config, "POST", "/issue", "create the ticket", ok=(201,), json=payload)

    data = resp.json()
    key = data["key"]
    url = f"{config['jira']['url'].rstrip('/')}/browse/{key}"

    # Tự động gán vào Sprint nếu có chỉ định hoặc sprint đang chạy
    target_sprint = sprint_id or 48756
    if target_sprint:
        try:
            agile_url = f"{config['jira']['url'].rstrip('/')}/rest/agile/1.0/sprint/{target_sprint}/issue"
            requests.post(agile_url, headers=jira_headers(config), json={"issues": [key]}, timeout=15)
        except Exception:
            pass

    if time_spent:
        try:
            _jira(config, "POST", f"/issue/{key}/worklog", "log work", ok=(201,), json={"timeSpent": time_spent})
        except ToolError as e:
            e.problem = f"created {key} ({url}) but could not log work: {e.problem}"
            e.fix = f"do not create the ticket again. {e.fix} Use update_jira_ticket on {key} for the time."
            raise

    return f"Created ticket: {key}\nTitle: {full_title}\nEstimate: {time_estimate}\nSpent: {time_spent or '—'}\nType: {task_type}\nSprint: {target_sprint}\nURL: {url}"


@mcp.tool()
def update_jira_ticket(
    ticket_key: str,
    summary: str = "",
    description: str = "",
    time_estimate: str = "",
    time_spent: str = "",
) -> str:
    """Update an existing Jira ticket's title, description or estimate, and/or log time spent on it.

    The description replaces the old one completely. Text must not mention Claude or AI authorship.

    Args:
        ticket_key: The Jira ticket key (e.g., 'PROJ-123').
        summary: New title/summary (optional).
        description: New description (optional).
        time_estimate: New time estimate in Jira format — e.g., '3h', '1d 4h', '3d' (optional).
        time_spent: Time to log as spent — e.g., '2h', '1d' (optional).

    Returns:
        Confirmation of the update. Errors start with 'jira-work-logger · <category> · retryable|not retryable'.
    """
    if not re.fullmatch(r"[A-Z][A-Z0-9]+-\d+", ticket_key.strip()):
        raise ToolError("validation", False, f"'{ticket_key}' is not a ticket key.", "call again with a key like PROJ-123.")
    _reject_ai_authorship(summary, description)
    config = load_config()
    fields = {}

    if summary:
        fields["summary"] = summary

    if description:
        if _is_jira_server(config):
            fields["description"] = description
        else:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}]
                    }
                ]
            }

    if time_estimate:
        if not _valid_jira_time(time_estimate):
            raise ToolError("validation", False, f"time_estimate '{time_estimate}' is not a Jira duration.", "call again with e.g. '3h', '1d 4h' or '3d'.")
        fields["timetracking"] = {"originalEstimate": time_estimate}

    if time_spent and not _valid_jira_time(time_spent):
        raise ToolError("validation", False, f"time_spent '{time_spent}' is not a Jira duration.", "call again with e.g. '2h' or '1d'.")

    if fields:
        _jira(config, "PUT", f"/issue/{ticket_key}", f"update {ticket_key}", ok=(200, 204), json={"fields": fields})

    if time_spent:
        try:
            _jira(config, "POST", f"/issue/{ticket_key}/worklog", f"log work on {ticket_key}", ok=(201,), json={"timeSpent": time_spent})
        except ToolError as e:
            if fields:
                e.problem = f"updated {ticket_key} but could not log work: {e.problem}"
                e.fix = f"do not repeat the field update. {e.fix} Call again with only time_spent."
            raise

    url = f"{config['jira']['url'].rstrip('/')}/browse/{ticket_key}"
    return f"Updated ticket: {ticket_key}\nURL: {url}"


@mcp.tool()
def get_my_tickets(status: str = "In Progress") -> str:
    """List up to 20 Jira tickets assigned to the user with one status, most recently updated first.

    Args:
        status: Exact Jira status name, e.g. 'To Do', 'In Progress', 'In Review', 'Done'. Defaults to 'In Progress'.

    Returns:
        Matching tickets with estimate and time spent. Errors start with 'jira-work-logger · <category> · retryable|not retryable'.
    """
    config = load_config()
    jql = f"assignee = currentUser() AND status = \"{status}\" ORDER BY updated DESC"

    search_path = "/search" if _is_jira_server(config) else "/search/jql"
    resp = _jira(config, "GET", search_path, f"list '{status}' tickets", ok=(200,),
                 params={"jql": jql, "maxResults": 20, "fields": "summary,status,timetracking"})

    issues = resp.json().get("issues", [])
    if not issues:
        return f"No tickets found with status '{status}'."

    output = [f"## My tickets ({status})\n"]
    for issue in issues:
        key = issue["key"]
        summary = issue["fields"]["summary"]
        tracking = issue["fields"].get("timetracking", {})
        estimate = tracking.get("originalEstimate", "—")
        spent = tracking.get("timeSpent", "—")
        output.append(f"- **{key}**: {summary} (estimate: {estimate}, spent: {spent})")

    return "\n".join(output)


@mcp.tool()
def get_my_sprints(state: str = "active") -> str:
    """List Jira sprints containing tickets assigned to the user.

    Args:
        state: Sprint state: 'active', 'closed', or 'all'. Defaults to 'active'.

    Returns:
        Summary of sprints and assigned tickets. Errors start with 'jira-work-logger · <category> · retryable|not retryable'.
    """
    config = load_config()
    state_lower = state.strip().lower()
    if state_lower == "active":
        jql = "assignee = currentUser() AND sprint in openSprints()"
    elif state_lower == "closed":
        jql = "assignee = currentUser() AND sprint in closedSprints() ORDER BY updated DESC"
    else:
        jql = "assignee = currentUser() AND sprint is not EMPTY ORDER BY updated DESC"

    search_path = "/search" if _is_jira_server(config) else "/search/jql"
    resp = _jira(config, "GET", search_path, "list sprints", ok=(200,),
                 params={"jql": jql, "maxResults": 100, "fields": "summary,status,customfield_10105"})

    issues = resp.json().get("issues", [])
    if not issues:
        return f"No sprints found with state '{state}'."

    sprints = {}
    for issue in issues:
        raw_sprints = issue["fields"].get("customfield_10105") or []
        for s_str in raw_sprints:
            m_id = re.search(r"id=(\d+)", s_str)
            m_name = re.search(r"name=([^,]+)", s_str)
            m_state = re.search(r"state=([^,]+)", s_str)
            m_start = re.search(r"startDate=([^,]+)", s_str)
            m_end = re.search(r"endDate=([^,]+)", s_str)
            if m_id and m_name:
                sid = m_id.group(1)
                st = (m_state.group(1) if m_state else "UNKNOWN").upper()
                if state_lower == "active" and st != "ACTIVE":
                    continue
                if state_lower == "closed" and st != "CLOSED":
                    continue
                if sid not in sprints:
                    sprints[sid] = {
                        "name": m_name.group(1),
                        "state": st,
                        "startDate": m_start.group(1) if m_start else "",
                        "endDate": m_end.group(1) if m_end else "",
                        "issues": []
                    }
                sprints[sid]["issues"].append(issue)

    output = [f"## Sprints ({state})\n"]
    for sid, s in sprints.items():
        output.append(f"### {s['name']} (ID: {sid}, State: {s['state']})")
        if s["startDate"] or s["endDate"]:
            output.append(f"Period: {s['startDate'][:10]} -> {s['endDate'][:10]}")
        output.append(f"Total tickets: {len(s['issues'])}")
        for iss in s["issues"][:10]:
            k = iss["key"]
            st = iss["fields"]["status"]["name"]
            sm = iss["fields"]["summary"]
            output.append(f"- **{k}** [{st}]: {sm}")
        if len(s["issues"]) > 10:
            output.append(f"- ... và {len(s['issues']) - 10} ticket khác")
        output.append("")

    return "\n".join(output)


@mcp.tool()
def log_work(
    ticket_key: str,
    time_spent: str,
    date: str = "",
    comment: str = "",
) -> str:
    """Log work time on a Jira ticket. It automatically syncs to Tempo Timesheets.

    Args:
        ticket_key: Jira ticket key (e.g., 'NCPTWORK-4381').
        time_spent: Time spent in Jira duration format (e.g. '2h', '4h', '1d', '30m', '1d 4h').
        date: Work date in YYYY-MM-DD format. Defaults to today.
        comment: Description of the work done.

    Returns:
        Confirmation of the logged worklog.
    """
    if not re.fullmatch(r"[A-Z][A-Z0-9]+-\d+", ticket_key.strip()):
        raise ToolError("validation", False, f"'{ticket_key}' is not a ticket key.", "call again with a key like NCPTWORK-4381.")
    if not _valid_jira_time(time_spent):
        raise ToolError("validation", False, f"time_spent '{time_spent}' is not a valid duration.", "call again with e.g. '2h', '4h', '1d'.")

    _reject_ai_authorship(comment)
    config = load_config()

    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise ToolError("validation", False, f"date '{date}' is not YYYY-MM-DD.", "call again with a date like 2026-11-02.")

    started = f"{date}T09:00:00.000+0700"
    payload = {
        "timeSpent": time_spent,
        "started": started,
    }
    if comment:
        payload["comment"] = comment

    resp = _jira(config, "POST", f"/issue/{ticket_key}/worklog", f"log work on {ticket_key}", ok=(201,), json=payload)
    data = resp.json()
    worklog_id = data.get("id", "created")

    timesheet_url = f"{config['jira']['url'].rstrip('/')}/secure/Tempo.jspa#/my-work/timesheet"
    return f"Đã log thành công {time_spent} vào ticket {ticket_key} (ngày {date}).\n- Ghi chú: {comment or '(không có)'}\n- Worklog ID: {worklog_id}\n- Bảng Tempo: {timesheet_url}"


@mcp.tool()
def get_tempo_worklogs(from_date: str = "", to_date: str = "") -> str:
    """View logged work entries from Tempo Timesheets for a given period.

    Args:
        from_date: Start date YYYY-MM-DD. Defaults to first day of current month.
        to_date: End date YYYY-MM-DD. Defaults to last day of current month.

    Returns:
        Summary of logged hours and worklog entries from Tempo.
    """
    config = load_config()
    now = datetime.now()
    if not from_date:
        from_date = now.strftime("%Y-%m-01")
    if not to_date:
        from_date_dt = datetime.strptime(from_date, "%Y-%m-%d")
        next_month = from_date_dt.replace(day=28) + timedelta(days=4)
        last_day = next_month - timedelta(days=next_month.day)
        to_date = last_day.strftime("%Y-%m-%d")

    user_info = _jira(config, "GET", "/myself", "look up user profile").json()
    worker_key = user_info.get("key") or user_info.get("name")

    headers = jira_headers(config)
    tempo_url = f"{config['jira']['url'].rstrip('/')}/rest/tempo-timesheets/4/worklogs/search"
    search_payload = {
        "from": from_date,
        "to": to_date,
        "worker": [worker_key]
    }

    try:
        resp = requests.post(tempo_url, headers=headers, json=search_payload, timeout=30)
    except requests.RequestException as e:
        raise ToolError("network", True, f"could not reach Tempo API: {e}", "retry once.")

    if resp.status_code != 200:
        raise ToolError("validation", False, f"Tempo returned {resp.status_code}: {resp.text[:200]}", "check Tempo access permissions.")

    worklogs = resp.json()
    if not worklogs:
        return f"Không có worklog nào được ghi nhận trong Tempo từ {from_date} đến {to_date}."

    total_seconds = sum(w.get("timeSpentSeconds", 0) for w in worklogs)
    total_hours = total_seconds / 3600

    output = [
        f"## Tempo Timesheet Worklogs ({from_date} -> {to_date})",
        f"- **Tổng số giờ đã log:** {total_hours:.1f}h ({total_seconds // 3600}h {(total_seconds % 3600) // 60}m)",
        f"- **Số lượt ghi log:** {len(worklogs)}\n",
        "### Chi tiết các ngày:"
    ]

    worklogs.sort(key=lambda w: w.get("started", ""))
    for w in worklogs:
        dt = w.get("started", "")[:10]
        issue = w.get("issue", {})
        key = issue.get("key", "N/A")
        summary = issue.get("summary", "")
        time_spent = w.get("timeSpent", f"{w.get('timeSpentSeconds', 0)//3600}h")
        comment = (w.get("comment") or "").strip()
        comment_str = f" - {comment}" if comment else ""
        output.append(f"- **{dt}** | **{key}** ({time_spent}): {summary}{comment_str}")

    return "\n".join(output)


if __name__ == "__main__":
    mcp.run()
