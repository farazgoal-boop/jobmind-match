"""Lead hunting platform registry for JobMind Match."""
from __future__ import annotations

from typing import Any

# ── Data seeds ────────────────────────────────────────────────────

_GITHUB_QUERIES: list[str] = [
    "freelance developer email hire",
    "hire me developer email contact",
    "open to work email developer",
    "available for hire email developer",
    "freelance designer email hire",
    "freelance marketer email contact",
    "indie maker email contact",
    "solopreneur email hire",
    "python developer freelance email",
    "react developer freelance email",
    "fullstack developer freelance email",
    "web developer hire email contact",
    "mobile developer freelance email",
    "wordpress developer email hire",
    "shopify developer email contact",
    "django developer freelance email",
    "node developer freelance email",
    "flutter developer freelance email",
    "data scientist freelance email",
    "machine learning engineer email",
    "devops engineer freelance email",
    "blockchain developer email hire",
    "graphic designer email whatsapp hire",
    "UI UX designer email contact hire",
    "content creator email whatsapp",
    "digital marketer email whatsapp hire",
    "SEO expert email hire contact",
    "video editor email hire whatsapp",
    "copywriter email whatsapp hire",
    "virtual assistant email hire",
    "typescript developer freelance email",
    "golang developer freelance email",
    "rust developer freelance email",
    "laravel developer freelance email",
    "vue developer freelance email",
    "angular developer freelance email",
    "aws engineer freelance email",
    "kubernetes engineer freelance email",
    "product manager freelance email",
    "technical writer freelance email",
]

_DEVTO_TAGS: list[str] = [
    "forhire",
    "freelance",
    "hiring",
    "opentowork",
    "career",
    "developer",
    "webdev",
    "python",
    "javascript",
    "react",
    "node",
    "fullstack",
    "backend",
    "frontend",
    "devops",
    "design",
    "ux",
    "marketing",
    "productivity",
    "startup",
]

_REDDIT_SUBS: list[str] = [
    "forhire",
    "freelance",
    "slavelabour",
    "hiring",
    "WorkOnline",
    "jobbit",
    "Jobs4Bitcoins",
    "remotejs",
    "remotedaily",
    "digitalnomad",
    "VirtualAssistant",
    "Upwork",
    "freelancer",
    "designjobs",
    "webdesign",
    "webdev",
    "programming",
    "learnprogramming",
    "cscareerquestions",
    "ITCareerQuestions",
    "techjobs",
    "startups",
    "Entrepreneur",
    "smallbusiness",
    "marketing",
    "socialmedia",
    "SEO",
    "content_marketing",
    "copywriting",
    "VideoEditing",
    "graphic_design",
    "logodesign",
    "UI_Design",
    "UXDesign",
    "web_design",
    "Wordpress",
    "shopify",
    "python",
    "javascript",
    "reactjs",
    "node",
    "django",
    "flutter",
    "androiddev",
    "iosprogramming",
    "gamedev",
]

_SITE_DOMAINS: list[tuple[str, str]] = [
    ("upwork.com", "Upwork"),
    ("fiverr.com", "Fiverr"),
    ("freelancer.com", "Freelancer.com"),
    ("guru.com", "Guru"),
    ("peopleperhour.com", "PeoplePerHour"),
    ("toptal.com", "Toptal"),
    ("99designs.com", "99designs"),
    ("designcrowd.com", "DesignCrowd"),
    ("bark.com", "Bark"),
    ("taskrabbit.com", "TaskRabbit"),
    ("flexjobs.com", "FlexJobs"),
    ("remote.co", "Remote.co"),
    ("weworkremotely.com", "We Work Remotely"),
    ("remotive.com", "Remotive"),
    ("wellfound.com", "Wellfound"),
    ("gun.io", "Gun.io"),
    ("lemon.io", "Lemon.io"),
    ("arc.dev", "Arc.dev"),
    ("codementor.io", "Codementor"),
    ("clutch.co", "Clutch"),
    ("sortlist.com", "Sortlist"),
    ("thumbtack.com", "Thumbtack"),
    ("houzz.com", "Houzz"),
    ("behance.net", "Behance"),
    ("dribbble.com", "Dribbble"),
    ("contra.com", "Contra"),
    ("workingnotworking.com", "Working Not Working"),
    ("usemoonlight.com", "Moonlight"),
    ("cloudpeeps.com", "CloudPeeps"),
    ("simplyhired.com", "SimplyHired"),
]

_RSS_FEEDS: list[tuple[str, str]] = [
    ("Remotive Jobs", "https://remotive.com/remote-jobs/feed"),
    ("WeWorkRemotely", "https://weworkremotely.com/remote-jobs.rss"),
    ("Arbeitnow Jobs", "https://arbeitnow.com/api/job-board-feed"),
    ("Remote OK", "https://remoteok.com/remote-jobs.rss"),
    ("Jobspresso", "https://jobspresso.co/feed/"),
    ("Authentic Jobs", "https://www.authenticjobs.com/rss/"),
    ("Dribbble Jobs", "https://dribbble.com/jobs.rss"),
    ("Startup Jobs", "https://startup.jobs/feed"),
    ("Himalayas Remote", "https://himalayas.app/jobs/rss"),
    ("Daily Remote", "https://dailyremote.com/feed/"),
    ("NoDesk Remote", "https://nodesk.co/remote-jobs/feed/"),
    ("HN Who Is Hiring", "https://hnrss.org/whoishiring"),
    ("HN Freelancer", "https://hnrss.org/newest?q=freelancer"),
    ("HN Hiring", "https://hnrss.org/newest?q=hiring"),
    ("HN Remote", "https://hnrss.org/newest?q=remote"),
    ("HN Contract", "https://hnrss.org/newest?q=contract"),
    ("Stack Overflow Blog", "https://stackoverflow.blog/feed/"),
    ("Smashing Magazine", "https://www.smashingmagazine.com/feed/"),
    ("Product Hunt", "https://www.producthunt.com/feed"),
    ("AngelList Talent", "https://angel.co/jobs/feed"),
    ("FlexJobs Blog", "https://www.flexjobs.com/blog/feed/"),
    ("Remote.co Jobs", "https://remote.co/remote-jobs/feed/"),
    ("Working Nomads", "https://www.workingnomads.com/jobs.rss"),
    ("JustRemote", "https://justremote.co/remote-jobs.rss"),
    ("Remote Leaf", "https://remoteleaf.com/feed/"),
    ("Euro Remote Jobs", "https://euroremotejobs.com/feed/"),
    ("Remote Python", "https://www.remotepython.com/feed/"),
    ("We Love Product", "https://weloveproduct.co/feed/"),
    ("Landing Jobs", "https://landing.jobs/feed"),
    ("Cryptocurrency Jobs", "https://cryptocurrencyjobs.co/feed/"),
    ("Blockchain Jobs", "https://blockchainjoblist.com/feed/"),
    ("AI Jobs Board", "https://ai-jobs.net/feed/"),
    ("Data Jobs", "https://datajobs.com/feed/"),
    ("DevOps Jobs", "https://devopsjobs.net/feed/"),
    ("React Jobs", "https://reactjobs.io/feed/"),
    ("Vue Jobs", "https://vuejobs.com/feed/"),
    ("Golang Jobs", "https://golangjob.com/feed/"),
    ("Rust Jobs", "https://rustjobs.dev/feed/"),
    ("Python Jobs", "https://pythonjob.xyz/feed/"),
    ("JavaScript Jobs", "https://javascriptjob.xyz/feed/"),
    ("Design Jobs Board", "https://www.designjobsboard.com/feed/"),
    ("Creative Bloq Jobs", "https://www.creativebloq.com/feeds/all"),
    ("Behance Jobs RSS", "https://www.behance.net/joblist/rss"),
    ("Freelancer RSS", "https://www.freelancer.com/rss.xml"),
    ("Upwork Blog", "https://www.upwork.com/blog/feed/"),
    ("Fiverr Blog", "https://blog.fiverr.com/feed/"),
    ("ProBlogger Jobs", "https://problogger.com/jobs/feed/"),
    ("Media Bistro", "https://www.mediabistro.com/feeds/jobs/"),
    ("Journalism Jobs", "https://www.journalismjobs.com/rss/"),
    ("Content Writing Jobs", "https://contentwritingjobs.com/feed/"),
    ("Copywriter Jobs", "https://copywriterjobs.com/feed/"),
    ("Marketing Hire", "https://marketinghire.com/feed/"),
    ("SEO Jobs", "https://www.seojobs.com/feed/"),
    ("Growth Hackers Jobs", "https://growthhackers.com/jobs/feed/"),
    ("Product Hunt Makers", "https://www.producthunt.com/feed?category=makers"),
    ("Indie Hackers RSS", "https://www.indiehackers.com/feed"),
    ("Dev.to RSS", "https://dev.to/feed/tag/forhire"),
    ("Dev.to Freelance", "https://dev.to/feed/tag/freelance"),
    ("Dev.to Hiring", "https://dev.to/feed/tag/hiring"),
    ("Reddit forhire RSS", "https://www.reddit.com/r/forhire/new/.rss"),
    ("Reddit freelance RSS", "https://www.reddit.com/r/freelance/new/.rss"),
    ("Reddit slavelabour RSS", "https://www.reddit.com/r/slavelabour/new/.rss"),
    ("Reddit hiring RSS", "https://www.reddit.com/r/hiring/new/.rss"),
    ("Reddit WorkOnline RSS", "https://www.reddit.com/r/WorkOnline/new/.rss"),
    ("Reddit remotejs RSS", "https://www.reddit.com/r/remotejs/new/.rss"),
    ("Reddit designjobs RSS", "https://www.reddit.com/r/designjobs/new/.rss"),
    ("Reddit webdev RSS", "https://www.reddit.com/r/webdev/new/.rss"),
    ("Reddit VirtualAssistant RSS", "https://www.reddit.com/r/VirtualAssistant/new/.rss"),
    ("Remotive Dev Jobs", "https://remotive.com/remote-jobs/software-dev/feed"),
    ("Remotive Design Jobs", "https://remotive.com/remote-jobs/design/feed"),
    ("Remotive Marketing Jobs", "https://remotive.com/remote-jobs/marketing/feed"),
    ("WWR Programming", "https://weworkremotely.com/categories/remote-programming-jobs.rss"),
    ("WWR Design", "https://weworkremotely.com/categories/remote-design-jobs.rss"),
    ("WWR DevOps", "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss"),
    ("WWR Customer Support", "https://weworkremotely.com/categories/remote-customer-support-jobs.rss"),
]

_CORE_PLATFORMS: list[dict[str, Any]] = [
    {
        "id": "core_github_readme",
        "name": "📄 GitHub READMEs",
        "type": "github_readme",
        "chip": "github",
        "batches": 3,
    },
    {
        "id": "core_github_issues",
        "name": "🐛 GitHub Issues",
        "type": "github_issues",
        "chip": "github",
        "batches": 3,
    },
    {
        "id": "core_hackernews",
        "name": "🔶 Hacker News",
        "type": "hackernews",
        "chip": "misc",
        "batches": 3,
    },
    {
        "id": "core_indiehackers",
        "name": "🏴 Indie Hackers",
        "type": "indiehackers",
        "chip": "indiehackers",
        "batches": 2,
    },
    {
        "id": "core_remotive",
        "name": "🌍 Remotive Jobs",
        "type": "remotive",
        "chip": "misc",
        "batches": 2,
    },
    {
        "id": "core_weworkremotely",
        "name": "🏠 We Work Remotely",
        "type": "weworkremotely",
        "chip": "misc",
        "batches": 2,
    },
    {
        "id": "core_arbeitnow",
        "name": "🇩🇪 Arbeitnow",
        "type": "arbeitnow",
        "chip": "misc",
        "batches": 2,
    },
]


def _batches_for(index: int, base: int = 1) -> int:
    return ((index % 3) + base)


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value.lower()).strip("_")


def _build_github_platforms() -> list[dict[str, Any]]:
    platforms: list[dict[str, Any]] = []
    for idx, query in enumerate(_GITHUB_QUERIES[:40]):
        platforms.append(
            {
                "id": f"github_q{idx:02d}",
                "name": f"💻 GitHub: {query[:48]}",
                "type": "github",
                "chip": "github",
                "batches": _batches_for(idx, 1),
                "query_index": idx,
                "query": query,
            }
        )
    return platforms


def _build_devto_platforms() -> list[dict[str, Any]]:
    platforms: list[dict[str, Any]] = []
    for idx, tag in enumerate(_DEVTO_TAGS[:20]):
        platforms.append(
            {
                "id": f"devto_{_slug(tag)}",
                "name": f"👨‍💻 Dev.to #{tag}",
                "type": "devto",
                "chip": "devto",
                "batches": _batches_for(idx, 1),
                "tag": tag,
            }
        )
    return platforms


def _build_reddit_platforms() -> list[dict[str, Any]]:
    platforms: list[dict[str, Any]] = []
    for idx, sub in enumerate(_REDDIT_SUBS[:45]):
        platforms.append(
            {
                "id": f"reddit_{_slug(sub)}",
                "name": f"📖 r/{sub}",
                "type": "reddit",
                "chip": "reddit",
                "batches": _batches_for(idx, 1),
                "subreddit": sub,
                "feed_url": f"https://www.reddit.com/r/{sub}/new/.rss",
            }
        )
    return platforms


def _build_rss_platforms() -> list[dict[str, Any]]:
    platforms: list[dict[str, Any]] = []
    for idx, (label, url) in enumerate(_RSS_FEEDS[:70]):
        platforms.append(
            {
                "id": f"rss_{idx:02d}_{_slug(label)[:24]}",
                "name": f"📡 {label}",
                "type": "rss",
                "chip": "misc",
                "batches": _batches_for(idx, 1),
                "feed_url": url,
            }
        )
    return platforms


def _build_site_platforms() -> list[dict[str, Any]]:
    platforms: list[dict[str, Any]] = []
    for idx, (domain, label) in enumerate(_SITE_DOMAINS[:30]):
        platforms.append(
            {
                "id": f"site_{_slug(domain.replace('.', '_'))}",
                "name": f"🌐 {label}",
                "type": "site",
                "chip": "misc",
                "batches": _batches_for(idx, 1),
                "site": domain,
            }
        )
    return platforms


def _build_all_platforms() -> list[dict[str, Any]]:
    return [
        *_CORE_PLATFORMS,
        *_build_github_platforms(),
        *_build_devto_platforms(),
        *_build_reddit_platforms(),
        *_build_rss_platforms(),
        *_build_site_platforms(),
    ]


PLATFORMS: list[dict[str, Any]] = _build_all_platforms()

PLATFORM_MAP: dict[str, dict[str, Any]] = {p["id"]: p for p in PLATFORMS}

CHIP_GROUPS: dict[str, list[str]] = {}
for _platform in PLATFORMS:
    _chip = _platform["chip"]
    CHIP_GROUPS.setdefault(_chip, []).append(_platform["id"])


# UI chip labels → backend platform chip groups
_CHIP_ALIASES: dict[str, str] = {
    "google": "misc",
    "twitter": "misc",
    "medium": "misc",
    "stackoverflow": "misc",
    "producthunt": "misc",
    "behance": "misc",
    "telegram": "misc",
    "facebook": "misc",
    "youtube": "misc",
}


def _expand_chips(enabled_chips: list[str]) -> set[str]:
    chips = {c.strip().lower() for c in enabled_chips if c and c.strip()}
    expanded = set(chips)
    for chip in chips:
        alias = _CHIP_ALIASES.get(chip)
        if alias:
            expanded.add(alias)
    return expanded


def get_hunt_plan(enabled_chips: list[str], include_misc: bool = False) -> list[dict[str, Any]]:
    """Return scrape plan entries filtered by enabled platform chips."""
    expanded = _expand_chips(enabled_chips)
    plan: list[dict[str, Any]] = []

    for platform in PLATFORMS:
        chip = platform["chip"]
        include = chip in expanded
        if "misc" in expanded and chip == "misc":
            include = True
        if "wahunt" in expanded and platform.get("type") == "github_issues":
            include = True
        if include_misc and chip == "misc":
            include = True
        if not include:
            continue
        plan.append(
            {
                "source": platform["id"],
                "label": platform["name"],
                "batches": platform["batches"],
                "chip": chip,
            }
        )
    return plan


def platform_summary() -> dict[str, Any]:
    """Counts by type and chip for diagnostics."""
    by_type: dict[str, int] = {}
    by_chip: dict[str, int] = {}
    for platform in PLATFORMS:
        by_type[platform["type"]] = by_type.get(platform["type"], 0) + 1
        by_chip[platform["chip"]] = by_chip.get(platform["chip"], 0) + 1
    return {
        "total": len(PLATFORMS),
        "by_type": by_type,
        "by_chip": by_chip,
    }


if __name__ == "__main__":
    summary = platform_summary()
    print(f"Total platforms: {summary['total']}")
    for kind, count in sorted(summary["by_type"].items()):
        print(f"  {kind}: {count}")
    print("Chips:")
    for chip, count in sorted(summary["by_chip"].items()):
        print(f"  {chip}: {count} ({len(CHIP_GROUPS.get(chip, []))} ids)")
