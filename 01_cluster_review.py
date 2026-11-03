import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import altair as alt
    import hashlib
    import json
    from pathlib import Path
    import re
    from urllib.parse import urlparse

    import marimo as mo
    import pandas as pd

    return Path, hashlib, json, mo, pd, re, urlparse


@app.cell
def _():
    REAL_CONFIRMATION_FLAG = "real"
    CONTACTED_FLAG = "contacted"
    return CONTACTED_FLAG, REAL_CONFIRMATION_FLAG


@app.cell
def _(json):
    REVIEWED_CLUSTERS_FP = (
        "./data/calmatters_review/reviewed-clusters-sample.json"
    )

    with open(REVIEWED_CLUSTERS_FP) as f:
        clusters = json.load(f)
    return (clusters,)


@app.cell
def _(REAL_CONFIRMATION_FLAG, clusters, mo):
    clusters_labeled_real = [
        cluster
        for cluster in clusters
        if cluster["verdict"] == REAL_CONFIRMATION_FLAG
    ]
    assert len(clusters_labeled_real) > 0
    mo.md(
        f"This sample includes {len(clusters_labeled_real)} of the 72 instructors we confirmed were paid by five or more campuses in 2024."
    )
    return (clusters_labeled_real,)


@app.cell(hide_code=True)
def _(CONTACTED_FLAG, Path, clusters_labeled_real, mo, pd, re, urlparse):
    _URL = re.compile(r"https?://\S+", re.IGNORECASE)
    _EVIDENCE_FILE = re.compile(r"data/calmatters_review/evidence/\S+")

    def evidence_url(value):
        """First usable web address or saved evidence file in a field, or None.

        Reviewers sometimes typed a note into a URL field ("sociology",
        "CONFIRMED VIA EMAIL"), put a note before the link ("Psychology:
        https://..."), or saved a Chrome PDF-viewer address wrapping the real one
        ("chrome-extension://.../https://..."). This pulls out the actual link;
        notes, other local file paths and bare "https://" fragments return None.

        Evidence saved in this repo is referenced by its path under
        data/calmatters_review/evidence/ and counts only if the file exists.
        """
        for candidate in _URL.findall(value or ""):
            parsed = urlparse(candidate)
            if parsed.netloc and "." in parsed.netloc:
                return candidate
        for candidate in _EVIDENCE_FILE.findall(value or ""):
            if Path(candidate).is_file():
                return candidate
        return None

    def _canonical_group(cluster):
        return cluster["groups"][0]

    def _verification_for(cluster):
        return cluster["verification"][str(_canonical_group(cluster)["id"])]

    def _verified_campuses(verification):
        # A directory listing only counts when it links to the page; entries
        # marked "found" with no usable web address (blank, or a typed note)
        # are ignored.
        directory_verified = {
            campus
            for campus, info in verification.get("directoryPages", {}).items()
            if info.get("found")
            and (
                evidence_url(info.get("liveUrl"))
                or evidence_url(info.get("archiveUrl"))
            )
        }
        schedule_verified = {
            campus
            for campus, courses in verification.get(
                "scheduleCourses", {}
            ).items()
            if courses
        }
        return directory_verified | schedule_verified

    def _campus_records(records):
        # A campus can carry more than one distinct title for the same person
        # (e.g. an overload/adjunct title alongside their main appointment), so
        # titles are collected rather than collapsed to a single value. Name
        # spellings are collected the same way.
        grouped = {}
        for r in records:
            entry = grouped.setdefault(
                r["campus"], {"pay": 0, "titles": [], "names": []}
            )
            entry["pay"] += r["pay"]
            if r["title"] not in entry["titles"]:
                entry["titles"].append(r["title"])
            if r["name"].strip() not in entry["names"]:
                entry["names"].append(r["name"].strip())
        return grouped

    def _cc_institution_rows(cluster):
        group = _canonical_group(cluster)
        verified_campuses = _verified_campuses(_verification_for(cluster))
        return [
            {
                "system": "CC",
                "institution": campus,
                "source_name": "; ".join(info["names"]),
                "title": "; ".join(info["titles"]),
                "pay": info["pay"],
                "verified": campus in verified_campuses,
            }
            for campus, info in _campus_records(group["records"]).items()
        ]

    def _cross_system_institution_rows(cluster):
        # A confirmed cross-system link is itself the verification - directory
        # pages and course schedules are only ever checked for CC campuses.
        group = _canonical_group(cluster)
        return [
            {
                "system": cl["system"],
                "institution": cl["institution"],
                "source_name": cl["name"].strip(),
                "title": cl["title"],
                "pay": cl["pay"],
                "verified": True,
            }
            for cl in group.get("crossLinks", [])
            if cl.get("status") == "confirmed"
        ]

    def _institution_rows(cluster):
        group = _canonical_group(cluster)
        verification = _verification_for(cluster)
        common = {
            "cluster_id": cluster["id"],
            "canonical_name": group["name"],
            # Some verification records predate the contact-tracking field
            # entirely; treat missing contact_status as not-yet-contacted.
            "contacted": verification.get("contact_status") == CONTACTED_FLAG,
        }
        rows = _cc_institution_rows(cluster) + _cross_system_institution_rows(
            cluster
        )
        return [{**common, **row} for row in rows]

    institutions_df = pd.DataFrame(
        row
        for cluster in clusters_labeled_real
        for row in _institution_rows(cluster)
    )

    mo.vstack(
        [
            mo.md("Records transformed into a tabulated format:"),
            institutions_df,
        ]
    )
    return evidence_url, institutions_df


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Confirmation backcheck
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Inspect titles
    """)
    return


@app.cell
def _(institutions_df, pd):
    # CC rows join a campus's multiple titles with "; ", so split them back out.
    pd.Series(
        sorted(institutions_df["title"].str.split("; ").explode().unique())
    )
    return


@app.cell(hide_code=True)
def _(contact_completed, mo):
    mo.md(rf"""
    ## Contact field

    We planned on reaching out at least two times to every identified instructor. Do our records show we did that?

    {contact_completed}
    """)
    return


@app.cell
def _(verification_df):
    contact_completed = bool(verification_df["contacted"].all())

    assert contact_completed
    return (contact_completed,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Expected number of outside verifications
    """)
    return


@app.cell
def _(institutions_df):
    verification_df = institutions_df.groupby(
        ["cluster_id", "canonical_name"], as_index=False
    ).agg(
        total_pay=("pay", "sum"),
        institution_count=("institution", "count"),
        verified_count=("verified", "sum"),
        systems=("system", lambda s: ", ".join(sorted(set(s)))),
        contacted=("contacted", "first"),
    )
    verification_df["needs_attention"] = (
        verification_df["verified_count"]
        < verification_df["institution_count"]
    )
    assert not any(verification_df["needs_attention"])
    verification_df
    return (verification_df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Faculty directory entries with a note instead of a link

    Reviewers sometimes typed a note into a directory entry's `liveUrl` or
    `archiveUrl` field (e.g. "sociology", "CONFIRMED VIA EMAIL", "See
    spreadsheet"), or checked the entry as found but left both fields blank.
    `evidence_url` finds no web address in these, so they don't count as
    verification. `schedule_listed` shows whether a course listing verifies the
    campus anyway. Any note may point to where the evidence is.
    """)
    return


@app.cell
def _(clusters_labeled_real, evidence_url, pd):
    def _text_only_directory_rows(cluster):
        group = cluster["groups"][0]
        verification = cluster["verification"][str(group["id"])]
        directory = verification.get("directoryPages", {})
        schedule = verification.get("scheduleCourses", {})
        for campus in sorted({r["campus"] for r in group["records"]}):
            entry = directory.get(campus, {})
            fields = [
                entry.get("liveUrl") or "",
                entry.get("archiveUrl") or "",
            ]
            if entry.get("found") and not any(evidence_url(f) for f in fields):
                yield {
                    "cluster_id": cluster["id"],
                    "canonical_name": group["name"],
                    "campus": campus,
                    "liveUrl": fields[0],
                    "archiveUrl": fields[1],
                    "schedule_listed": bool(schedule.get(campus)),
                }

    text_only_directory_df = pd.DataFrame(
        (
            row
            for cluster in clusters_labeled_real
            for row in _text_only_directory_rows(cluster)
        ),
        columns=[
            "cluster_id",
            "canonical_name",
            "campus",
            "liveUrl",
            "archiveUrl",
            "schedule_listed",
        ],
    )

    assert all(text_only_directory_df["schedule_listed"])
    text_only_directory_df
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Course listings with a note instead of a link

    The same thing happens in course schedule entries: a reviewer typed a note
    into a course's `link` field (e.g. "See course lookup notebook", "TK")
    instead of a web address, or left it blank. `_verified_campuses` counts any
    course listing as verification whether or not it links anywhere, so these
    campuses pass. These are all the courses without a usable link;
    `directory_linked` shows whether a linked directory entry verifies the
    campus anyway. Any note may point to where the evidence is.

    In this sample, every such course was confirmed by scraping a college's
    course schedule. Each one must match a section in
    `data/course-schedules/sections.csv`, and every raw schedule file those
    sections were read from must be in the repo, unchanged since we saved it.
    """)
    return


@app.cell
def _(Path, clusters_labeled_real, evidence_url, hashlib, pd):
    def _text_only_course_rows(cluster):
        group = cluster["groups"][0]
        verification = cluster["verification"][str(group["id"])]
        directory = verification.get("directoryPages", {})
        schedule = verification.get("scheduleCourses", {})
        for campus in sorted({r["campus"] for r in group["records"]}):
            entry = directory.get(campus, {})
            directory_linked = bool(
                entry.get("found")
                and (
                    evidence_url(entry.get("liveUrl"))
                    or evidence_url(entry.get("archiveUrl"))
                )
            )
            for course in schedule.get(campus, []):
                link = course.get("link") or ""
                if not evidence_url(link):
                    yield {
                        "cluster_id": cluster["id"],
                        "canonical_name": group["name"],
                        "campus": campus,
                        "course": course["code"],
                        "semester": course.get("semester", ""),
                        "link": link,
                        "directory_linked": directory_linked,
                    }

    text_only_course_df = pd.DataFrame(
        row
        for cluster in clusters_labeled_real
        for row in _text_only_course_rows(cluster)
    )

    _schedules_dir = Path("data/course-schedules")
    scraped_sections_df = pd.read_csv(
        _schedules_dir / "sections.csv", dtype={"course_number": str}
    )

    # Reviewers didn't always log a course's full title ("ASTR 1"), so courses
    # match on subject and number.
    _keys = ["instructor", "campus", "course", "term"]
    _unlinked_counts = (
        text_only_course_df.rename(
            columns={"canonical_name": "instructor", "semester": "term"}
        )
        .assign(
            course=lambda df: df["course"].str.split().str[:2].str.join(" ")
        )
        .value_counts(_keys)
    )
    _scraped_counts = scraped_sections_df.assign(
        course=scraped_sections_df["subject"]
        + " "
        + scraped_sections_df["course_number"]
    ).value_counts(_keys)

    assert _unlinked_counts.sort_index().equals(
        _scraped_counts.sort_index()
    ), "Courses without a link don't match the scraped sections"

    _manifest = pd.read_csv(_schedules_dir / "raw" / "manifest.csv")
    _cited = set(scraped_sections_df["raw_files"].str.split(";").explode())
    assert _cited <= set(_manifest["path"]), _cited - set(_manifest["path"])
    for _path, _sha256 in zip(_manifest["path"], _manifest["sha256"]):
        _raw = (_schedules_dir / "raw" / _path).read_bytes()
        assert hashlib.sha256(_raw).hexdigest() == _sha256, _path

    text_only_course_df
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Course listings without a semester

    Courses logged without a semester can't be placed in one, so the fact check
    skips them when counting classes per term. These are all such courses.
    """)
    return


@app.cell
def _(clusters_labeled_real, pd):
    courses_missing_semester_df = pd.DataFrame(
        {
            "cluster_id": cluster["id"],
            "canonical_name": cluster["groups"][0]["name"],
            "campus": campus,
            "course": course["code"],
        }
        for cluster in clusters_labeled_real
        for campus, courses in cluster["verification"][
            str(cluster["groups"][0]["id"])
        ]
        .get("scheduleCourses", {})
        .items()
        for course in courses
        if not course.get("semester", "").strip()
    )

    assert courses_missing_semester_df.empty, courses_missing_semester_df
    courses_missing_semester_df
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Name variations
    """)
    return


@app.cell
def _(institutions_df):
    # The same person can appear as "Sean Bowman" at one campus and "Sean P.
    # Bowman" at another. CC rows join a campus's spellings with "; ", so split
    # them back out before counting.
    def _normalize(names):
        return names.str.split().str.join(" ").str.lower().nunique()

    name_variations_df = (
        institutions_df.assign(
            source_name=institutions_df["source_name"].str.split("; ")
        )
        .explode("source_name")
        .groupby(["cluster_id", "canonical_name"], as_index=False)
        .agg(
            n_variations=("source_name", "nunique"),
            n_variations_normalized=("source_name", _normalize),
            variations=("source_name", lambda s: sorted(set(s))),
        )
        .sort_values("n_variations", ascending=False, ignore_index=True)
    )
    name_variations_df
    return (name_variations_df,)


@app.cell(hide_code=True)
def _(mo, name_variations_df):
    top_variation_entry = name_variations_df.iloc[0]

    mo.md(f"""
    **{top_variation_entry["canonical_name"]}** (cluster {top_variation_entry["cluster_id"]}) has the most name
    variations: **{top_variation_entry["n_variations"]}** distinct spellings across CC records and confirmed
    cross-system links:

    {", ".join(f"`{v}`" for v in top_variation_entry["variations"])}
    """)
    return


if __name__ == "__main__":
    app.run()
