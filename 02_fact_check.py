import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import json
    from pathlib import Path
    import re
    from urllib.parse import urlparse

    import marimo as mo
    import pandas as pd

    return Path, json, mo, pd, re, urlparse


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Fact-checks copy from the main story and the Show Your Work methodology using the source data and CalMatters-built verification data.

    To protect the privacy of instructors who are not named in the story, this repo includes a sample of our reviewed clusters: the 10 highest-paid instructors plus every other instructor named in the story. Checks on individual instructors match the published story. Checks that count or summarize all instructors run on the sample only, so each one also lists the result we got from the full reviewed data.
    """)
    return


@app.cell
def _():
    REAL_CONFIRMATION_FLAG = "real"
    CONTACTED_FLAG = "contacted"
    return CONTACTED_FLAG, REAL_CONFIRMATION_FLAG


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Read source data
    """)
    return


@app.cell
def _(mo, pd):
    COMMUNITY_COLLEGE_DATA_FP = (
        "./data/transparent-california/2024-community-colleges.csv"
    )

    df_cc_pay = pd.read_csv(
        COMMUNITY_COLLEGE_DATA_FP, sep=";", dtype={"id": str, "Year": str}
    ).dropna(axis=1, how="all")

    mo.vstack([mo.md("**CA Community College pay data**:"), df_cc_pay])
    return (df_cc_pay,)


@app.cell
def _(mo, pd):
    CSU_DATA_FP = (
        "./data/transparent-california/CY2024 California State University.xlsx"
    )
    _WHITESPACE_REGEX = r"[ ]+"

    def _clean_object_col_whitespace(df):
        # Strip text columns; numeric columns that came in as object because
        # of whitespace-only cells get those cells zeroed and cast to float.
        for col in df.columns:
            if pd.api.types.is_string_dtype(df[col]):
                df[col] = df[col].str.strip()
            if df[col].dtype == "object":
                df[col] = (
                    df[col]
                    .replace(_WHITESPACE_REGEX, 0, regex=True)
                    .astype(float)
                )
        return df

    def _drop_empty_str_columns(df):
        return df.loc[:, ~(df == "").all()]

    df_csu_pay = pd.read_excel(
        CSU_DATA_FP, dtype={"Unique\nID": str}, skiprows=1
    ).dropna(axis=1, how="all")
    df_csu_pay.columns = [col.replace("\n", " ") for col in df_csu_pay.columns]
    df_csu_pay = _clean_object_col_whitespace(df_csu_pay)
    df_csu_pay = _drop_empty_str_columns(df_csu_pay)
    # Campus lives in Subdivision Name, except for rows where it is blank and
    # the campus is in Department Name instead. This matches the institution
    # recorded on CSU cross-links.
    df_csu_pay["_agency"] = df_csu_pay["Subdivision Name"].mask(
        df_csu_pay["Subdivision Name"] == "", df_csu_pay["Department Name"]
    )

    mo.vstack([mo.md("**California State University pay data**:"), df_csu_pay])
    return (df_csu_pay,)


@app.cell
def _(mo, pd):
    UC_DATA_FP = "./data/transparent-california/UC AWR_website_data_with_Benefits_CY2024.xlsx"

    df_uc_pay = pd.read_excel(UC_DATA_FP, dtype={"Calendar Year": str})

    mo.vstack([mo.md("**University of California pay data**:"), df_uc_pay])
    return (df_uc_pay,)


@app.cell
def _(df_cc_pay, df_csu_pay, df_uc_pay, mo, pd):
    def _full_name(df):
        # Built the same way as cross-link names in 00_cluster_build.py. UC name
        # columns carry stray non-string values (e.g. booleans), hence astype.
        first = df["First Name"].fillna("").astype(str)
        last = df["Last Name"].fillna("").astype(str)
        return (first + " " + last).str.strip()

    payroll_df = pd.concat(
        [
            pd.DataFrame(
                {
                    "system": "CC",
                    "institution": df_cc_pay["Agency"],
                    "name": df_cc_pay["Employee Name"],
                    "title": df_cc_pay["Job Title"],
                    "pay": df_cc_pay["Total Pay"],
                }
            ),
            pd.DataFrame(
                {
                    "system": "CSU",
                    "institution": df_csu_pay["_agency"],
                    "name": _full_name(df_csu_pay),
                    "title": df_csu_pay["Class Title"],
                    "pay": df_csu_pay["Total Pay"],
                }
            ),
            pd.DataFrame(
                {
                    "system": "UC",
                    "institution": df_uc_pay["Location"],
                    "name": _full_name(df_uc_pay),
                    "title": df_uc_pay["Title"],
                    "pay": df_uc_pay["Gross Pay"],
                }
            ),
        ],
        ignore_index=True,
    )
    # Low-cardinality text columns as categories cut this frame's memory
    # roughly 3x (~168 MB -> ~49 MB).
    payroll_df = payroll_df.astype(
        {"system": "category", "institution": "category", "title": "category"}
    )

    mo.vstack([mo.md("## Combined payroll data:"), payroll_df])
    return (payroll_df,)


@app.cell
def _(json):
    REVIEWED_CLUSTERS_FP = (
        "./data/calmatters_review/reviewed-clusters-sample.json"
    )

    with open(REVIEWED_CLUSTERS_FP) as f:
        clusters = json.load(f)
    return (clusters,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Prepare analysis tables
    """)
    return


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

    def canonical_group(cluster):
        return cluster["groups"][0]

    def verification_for(cluster):
        return cluster["verification"][str(canonical_group(cluster)["id"])]

    def institution_name(cluster, key):
        """Institution a verification entry is keyed under.

        Entries for UC/CSU campuses are keyed by cross-link key
        (e.g. "CSU::64044") rather than by institution name.
        """
        institution_by_key = {
            cross_link["key"]: cross_link["institution"]
            for cross_link in canonical_group(cluster).get("crossLinks", [])
        }
        return institution_by_key.get(key, key)

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

    def directory_url(page):
        """Link to a directory page marked found, or None.

        A directory listing only counts when it links to the page; entries
        marked "found" with no usable web address (blank, or a typed note)
        are ignored.
        """
        if not page.get("found"):
            return None
        return evidence_url(page.get("liveUrl")) or evidence_url(
            page.get("archiveUrl")
        )

    def _verified_campuses(verification):
        directory_verified = {
            campus
            for campus, page in verification.get("directoryPages", {}).items()
            if directory_url(page)
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
        # titles are collected rather than collapsed to a single value.
        grouped = {}
        for r in records:
            entry = grouped.setdefault(
                r["campus"], {"pay": 0, "titles": [], "names": []}
            )
            entry["pay"] += r["pay"]
            if r["title"] not in entry["titles"]:
                entry["titles"].append(r["title"])
            if r["name"] not in entry["names"]:
                entry["names"].append(r["name"])
        return grouped

    def _cc_institution_rows(cluster):
        group = canonical_group(cluster)
        verified_campuses = _verified_campuses(verification_for(cluster))
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
        group = canonical_group(cluster)
        return [
            {
                "system": cl["system"],
                "institution": cl["institution"],
                "source_name": cl["name"],
                "title": cl["title"],
                "pay": cl["pay"],
                "verified": True,
            }
            for cl in group.get("crossLinks", [])
            if cl.get("status") == "confirmed"
        ]

    def _institution_rows(cluster):
        group = canonical_group(cluster)
        verification = verification_for(cluster)
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

    instructor_college_df = pd.DataFrame(
        row
        for cluster in clusters_labeled_real
        for row in _institution_rows(cluster)
    )

    mo.vstack(
        [
            mo.md("Records transformed into a tabulated format:"),
            instructor_college_df,
        ]
    )
    return (
        canonical_group,
        directory_url,
        institution_name,
        instructor_college_df,
        verification_for,
    )


@app.cell
def _(instructor_college_df):
    instructor_pay_analysis = (
        instructor_college_df.groupby("canonical_name", as_index=False)
        .agg(campus_count=("institution", "nunique"), pay=("pay", "sum"))
        .sort_values("pay", ascending=False)
    )
    return (instructor_pay_analysis,)


@app.cell
def _(
    canonical_group,
    clusters_labeled_real,
    institution_name,
    pd,
    verification_for,
):
    # One row per course found on a campus schedule. Campus keys are resolved
    # to institution names so cross-linked UC/CSU campuses count once.
    scheduled_courses_df = pd.DataFrame(
        [
            {
                "canonical_name": canonical_group(cluster)["name"],
                "campus": institution_name(cluster, campus),
                "term": course["semester"],
                "course": course["code"],
                "enrolled": course["enrolled"],
            }
            for cluster in clusters_labeled_real
            for campus, courses in verification_for(cluster)
            .get("scheduleCourses", {})
            .items()
            for course in courses
        ]
    )
    # Enrollment was typed in as text; blanks become NaN.
    scheduled_courses_df["enrolled"] = pd.to_numeric(
        scheduled_courses_df["enrolled"], errors="coerce"
    )
    return (scheduled_courses_df,)


@app.cell
def _(instructor_pay_analysis):
    top_paid_instructor = instructor_pay_analysis.loc[
        instructor_pay_analysis["pay"].idxmax(), "canonical_name"
    ]
    return (top_paid_instructor,)


@app.cell
def _(instructor_college_df, payroll_df):
    def verified_total_pay(canonical_name):
        """Instructor's total pay in our analysis, checked against source payroll.

        Source records are matched on system, campus and payroll name, so people
        who share a name at campuses we did not link are left out. The matches
        must cover the same campuses, and the source total must agree with ours to
        within $1 of rounding.
        """
        analysis_rows = instructor_college_df[
            instructor_college_df["canonical_name"] == canonical_name
        ]
        _keys = ["system", "institution", "name"]
        source_records = payroll_df.merge(
            analysis_rows.rename(columns={"source_name": "name"})[
                _keys
            ].drop_duplicates(),
            on=_keys,
        )
        assert (
            analysis_rows["institution"].nunique()
            == source_records["institution"].nunique()
        ), (
            f"Campus count mismatch: {analysis_rows['institution'].nunique()} != {source_records['institution'].nunique()}"
        )

        total_pay = round(analysis_rows["pay"].sum())
        source_total_pay = round(source_records["pay"].sum())
        assert abs(source_total_pay - total_pay) <= 1, (
            f"{source_total_pay} != {total_pay}"
        )
        return total_pay

    return (verified_total_pay,)


@app.cell(hide_code=True)
def _(
    PROFESSOR_VILLARREAL,
    mo,
    villarreal_fall_2026_courses,
    villarreal_fall_2026_missing_enrollment,
    villarreal_fall_2026_students,
):
    mo.md(rf"""
    # Fall 2026 classes

    Text from draft:
    > This fall, she’s [Thien-Huong Ninh Villarreal] teaching 30 classes to about 1,100 students.

    Fact check:
    > This fall, she’s [{PROFESSOR_VILLARREAL}] teaching {len(villarreal_fall_2026_courses)} classes to {villarreal_fall_2026_students:,} students.

    Courses missing an enrollment number: {villarreal_fall_2026_missing_enrollment}
    """)
    return


@app.cell
def _(scheduled_courses_df):
    PROFESSOR_VILLARREAL = "Thien-Huong Villarreal"

    villarreal_fall_2026_courses = scheduled_courses_df[
        (scheduled_courses_df["canonical_name"] == PROFESSOR_VILLARREAL)
        & (scheduled_courses_df["term"] == "Fall 2026")
    ]
    villarreal_fall_2026_students = int(
        villarreal_fall_2026_courses["enrolled"].sum()
    )
    villarreal_fall_2026_missing_enrollment = (
        villarreal_fall_2026_courses["enrolled"].isna().sum()
    )

    villarreal_fall_2026_courses[["campus", "course", "enrolled"]]
    return (
        PROFESSOR_VILLARREAL,
        villarreal_fall_2026_courses,
        villarreal_fall_2026_missing_enrollment,
        villarreal_fall_2026_students,
    )


@app.cell(hide_code=True)
def _(mo, villarreal_total_pay_2024):
    mo.md(rf"""
    # 2024 pay and workload

    Text from draft:
    > In 2024, when she did roughly the same thing, she made nearly $800,000, according to public payroll records.

    Fact check:
    > In 2024, when she did roughly the same thing, she made ${villarreal_total_pay_2024:,}, according to public payroll records.
    """)
    return


@app.cell
def _(PROFESSOR_VILLARREAL, verified_total_pay):
    villarreal_total_pay_2024 = verified_total_pay(PROFESSOR_VILLARREAL)
    return (villarreal_total_pay_2024,)


@app.cell(hide_code=True)
def _(MIN_CAMPUSES, instructors_over_class_threshold, mo, unique_name_count):
    mo.md(rf"""
    # Topline findings

    Text from draft:

    > By analyzing payroll and course data, CalMatters found at least 70 adjuncts, or part-time professors, who taught at five or more community college districts, California State University or University of California campuses at once, including many who taught more than 10 classes in a semester.

    Fact check:

    > By analyzing payroll and course data, CalMatters found {unique_name_count} adjuncts, or part-time professors, who taught at {MIN_CAMPUSES} or more community college districts, California State University or University of California campuses at once, including {len(instructors_over_class_threshold)} who taught more than 10 classes in a semester.

    Full data result (all 72 confirmed instructors, not included in this repo):

    > By analyzing payroll and course data, CalMatters found 72 adjuncts, or part-time professors, who taught at 5 or more community college districts, California State University or University of California campuses at once, including 17 who taught more than 10 classes in a semester.

    Our methodology required multiple stages of verification before we categorized an instructor in this grouping:
    1. Present on payroll at five or more campuses
    2. Outside evidence of instructor-campus relationship: course listing, faculty directory, LinkedIn, CV
    3. Two emails sent to all candidates for the analysis
    4. Each campus was emailed with an offer for further verification or pushback
    """)
    return


@app.cell
def _(instructor_college_df, instructor_pay_analysis):
    MIN_CAMPUSES = 5

    unique_id_count = instructor_college_df["cluster_id"].nunique()
    unique_name_count = instructor_college_df["canonical_name"].nunique()

    assert unique_id_count == unique_name_count, (
        "Mismatch in names and clusters in CalMatters analysis"
    )

    assert (instructor_pay_analysis["campus_count"] >= MIN_CAMPUSES).all(), (
        "Instructor included in final analysis that was paid from fewer than five campuses"
    )
    return MIN_CAMPUSES, unique_name_count


@app.cell
def _(scheduled_courses_df):
    _CLASS_THRESHOLD = 10

    assert all(scheduled_courses_df["term"].str.strip() != "")
    _courses_per_term = scheduled_courses_df.groupby(
        ["canonical_name", "term"]
    ).size()
    instructors_over_class_threshold = _courses_per_term[
        _courses_per_term > _CLASS_THRESHOLD
    ].index.unique("canonical_name")
    instructors_over_class_threshold
    return (instructors_over_class_threshold,)


@app.cell(hide_code=True)
def _(instructors_in_99th_pctl, mo):
    mo.md(rf"""
    # Higher-tier pay clusters

    Text from draft:
    > Some of these professors were among the highest paid employees across California’s 116 community colleges, according to the CalMatters analysis.

    Fact check:
    > {instructors_in_99th_pctl} were among the top 1% of paid employees across California’s 116 community colleges when their consolidated pay records were compared to the remaining payroll database records, according to the CalMatters analysis.

    Full data result (all 72 confirmed instructors, not included in this repo):

    > 28 were among the top 1% of paid employees across California’s 116 community colleges when their consolidated pay records were compared to the remaining payroll database records, according to the CalMatters analysis.
    """)
    return


@app.cell
def _(
    canonical_group,
    clusters_labeled_real,
    df_cc_pay,
    instructor_college_df,
):
    _TOP_PERCENT = 1
    COMMUNITY_COLLEGE_CATEGORY_VALUE = "CC"
    cc_df = instructor_college_df[
        instructor_college_df["system"] == COMMUNITY_COLLEGE_CATEGORY_VALUE
    ]
    # Leave the instructors' own CC records out of the comparison, so their
    # combined pay is ranked only against everyone else on CC payroll. Cluster
    # records are keyed by agency, name and job title, with the title normalized
    # as in 00_cluster_build.py.
    _instructor_record_keys = {
        record["key"]
        for cluster in clusters_labeled_real
        for record in canonical_group(cluster)["records"]
    }
    _normalized_title = (
        df_cc_pay["Job Title"]
        .str.lower()
        .str.replace("-", " ")
        .str.replace(r"[^a-z\s]", "", regex=True)
        .str.split()
        .str.join(" ")
    )
    _record_key = (
        df_cc_pay["Agency"]
        + "||"
        + df_cc_pay["Employee Name"]
        + "||"
        + _normalized_title
    )
    sorted_cc_pay = df_cc_pay.loc[
        ~_record_key.isin(_instructor_record_keys), "Total Pay"
    ].sort_values()

    # Percentile = share of other CC payroll records paid strictly less than
    # the instructor's combined CC pay, as if it were a single record.
    cc_pay_by_instructor = cc_df.groupby("canonical_name")["pay"].sum()
    instructors_in_99th_pctl = (
        sorted_cc_pay.searchsorted(cc_pay_by_instructor)
        / len(sorted_cc_pay)
        * 100
        > 100 - _TOP_PERCENT
    ).sum()
    return cc_df, cc_pay_by_instructor, instructors_in_99th_pctl


@app.cell(hide_code=True)
def _(
    CHANCELLOR_CHRISTIAN_PAY,
    highest_single_cc_name,
    highest_single_cc_pay,
    mo,
    top_cc_earner,
    top_cc_earner_campus_count,
    top_cc_earner_pay,
):
    mo.md(rf"""
    # Highest paid employee

    Text from draft:
    > In fact, no community college employee made more than Ninh Villarreal in 2024, not even Sonya Christian, the chancellor of the state’s community college system.

    Fact check:

    - Sonya Christian made ${CHANCELLOR_CHRISTIAN_PAY:,} in 2024, according to [Transparent California](https://transparentcalifornia.com/salaries/2024/state-of-california/sonya-christian) records from the State of California.
    - The highest paid employee in the community college system was {highest_single_cc_name}. Records show {highest_single_cc_name} made ${highest_single_cc_pay:,} in 2024.
    - Our analysis shows {top_cc_earner} was paid ${top_cc_earner_pay:,} from {top_cc_earner_campus_count} different community college campuses.
    """)
    return


@app.cell
def _(cc_df, cc_pay_by_instructor, df_cc_pay):
    CHANCELLOR_CHRISTIAN_PAY = 436_886

    highest_single_cc_record = df_cc_pay.loc[df_cc_pay["Total Pay"].idxmax()]
    highest_single_cc_name = highest_single_cc_record["Employee Name"]
    highest_single_cc_pay = round(highest_single_cc_record["Total Pay"])

    top_cc_earner = cc_pay_by_instructor.idxmax()
    top_cc_earner_pay = round(cc_pay_by_instructor.max())
    top_cc_earner_campus_count = cc_df.loc[
        cc_df["canonical_name"] == top_cc_earner, "institution"
    ].nunique()

    assert top_cc_earner_pay > highest_single_cc_pay > CHANCELLOR_CHRISTIAN_PAY
    return (
        CHANCELLOR_CHRISTIAN_PAY,
        highest_single_cc_name,
        highest_single_cc_pay,
        top_cc_earner,
        top_cc_earner_campus_count,
        top_cc_earner_pay,
    )


@app.cell(hide_code=True)
def _(PROFESSOR_HEUVEL, heuvel_total_pay_2024, mo):
    mo.md(rf"""
    # Lead subject pay

    Text from draft:
    > In 2024, California schools paid him [Andrew Vanden Heuvel] a total of about $320,000, according to the CalMatters analysis.

    Fact check:
    > In 2024, California schools paid him {PROFESSOR_HEUVEL} a total of about ${heuvel_total_pay_2024:,}, according to the CalMatters analysis.
    """)
    return


@app.cell
def _(verified_total_pay):
    PROFESSOR_HEUVEL = "Andrew Heuvel"

    heuvel_total_pay_2024 = verified_total_pay(PROFESSOR_HEUVEL)
    return PROFESSOR_HEUVEL, heuvel_total_pay_2024


@app.cell(hide_code=True)
def _(
    leonard_campus_count,
    leonard_total_pay_2024,
    mo,
    thomas_campus_count,
    thomas_total_pay_2024,
):
    mo.md(rf"""
    # Secondary subject pay

    I only confirm the pay and campus total.

    Text from draft:
    > [Noah] Thomas made just over $100,000 in 2024 by commuting among five community college campuses in Orange and Los Angeles counties, where he taught in-person studio arts classes.

    Fact check:
    > [Noah] Thomas made ${thomas_total_pay_2024:,} in 2024 by commuting among {thomas_campus_count} community college campuses in Orange and Los Angeles counties, where he taught in-person studio arts classes.

    ___

    Text from draft:
    > Tina Leonard, who teaches American Sign Language, is a perfect example. In 2024, she made just over $84,000 teaching at five community college districts.

    Fact check:
    > Tina Leonard, who teaches American Sign Language, is a perfect example. In 2024, she made ${leonard_total_pay_2024:,} teaching at {leonard_campus_count} community college districts.
    """)
    return


@app.cell
def _(instructor_college_df, verified_total_pay):
    PROFESSOR_THOMAS = "Noah Thomas"

    thomas_total_pay_2024 = verified_total_pay(PROFESSOR_THOMAS)
    thomas_campus_count = len(
        instructor_college_df[
            instructor_college_df["canonical_name"] == PROFESSOR_THOMAS
        ]
    )
    return thomas_campus_count, thomas_total_pay_2024


@app.cell
def _(instructor_college_df, verified_total_pay):
    PROFESSOR_LEONARD = "Tina Leonard"

    leonard_total_pay_2024 = verified_total_pay(PROFESSOR_LEONARD)
    leonard_campus_count = len(
        instructor_college_df[
            instructor_college_df["canonical_name"] == PROFESSOR_LEONARD
        ]
    )
    return leonard_campus_count, leonard_total_pay_2024


@app.cell(hide_code=True)
def _(instructor_400k_earners, mo):
    mo.vstack(
        [
            mo.md(r"""
            # 400k earners

            Text from draft:
            > To make more than $400,000, many of California’s highest earning adjuncts had full-time tenure or tenure-track positions too.

            The full-time or tenure status is outside the scope of the data fact check. I am fact checking the names listed under this section: Bobby Seals, Faramarz Mortezaie, Nicholas Nardi, Timothy Durfield, Walter Meyer.

            Fact check:

            **Instructors earning more than $400,000, according to our analysis**
            """),
            mo.ui.table(instructor_400k_earners),
        ]
    )
    return


@app.cell
def _(instructor_pay_analysis):
    _PAY_THRESHOLD = 400_000

    instructor_400k_earners = instructor_pay_analysis[
        instructor_pay_analysis["pay"] > _PAY_THRESHOLD
    ].reset_index(drop=True)
    return (instructor_400k_earners,)


@app.cell(hide_code=True)
def _(instructor_pay_analysis, instructors_over_exec_pay, median_exec_pay, mo):
    mo.md(rf"""
    # Median CC lead administrator pay

    Text from SYW draft:

    > Ten of the 72 instructors we identified earned more than $343,000, the median salary of a community college president or chancellor in the same year.

    > In total, we found 10 instructors, including Ninh Villarreal, who earned more than $340,000, the median salary of a community college president or chancellor in 2024.

    Fact check:

    > {len(instructors_over_exec_pay)} of the {len(instructor_pay_analysis)} instructors we identified earned more than ${median_exec_pay:,}, the median salary of a community college president or chancellor in the same year.

    Full data result (all 72 confirmed instructors, not included in this repo):

    > 10 of the 72 instructors we identified earned more than $342,585, the median salary of a community college president or chancellor in the same year.
    """)
    return


@app.cell
def _(df_cc_pay, mo):
    # Match titles that *start* with the top executive role, so VPs, assistants,
    # senate/union presidents, and "President's Office" staff fall out
    _CEO_TITLE_REGEX = r"""(?ix)
        ^(?:\d+\s)?                    # payroll code prefix, e.g. "1100 "
        (?:(?:interim|acting|temp|int\.?|int/act|district|college|doctorate,)\s*)?
        (?:superintendent|supt|president|chancellor|chief\ executive\ officer)\b
        (?!'s)                          # not "President's Office" staff
        (?!.*\bvp\b)                    # not "Superintendent/VP" hybrids
    """
    _INTERIM_TITLE_REGEX = r"(?i)\b(?:interim|acting|temp|int)\b"
    # Departing/incoming leaders have no flag in the data, so drop partial-year
    # records by base pay; full-year CEOs start just under $200K, with a gap below
    _FULL_YEAR_BASE_PAY_FLOOR = 180_000

    _job_title = df_cc_pay["Job Title"]
    _ceo_records = df_cc_pay[
        _job_title.str.contains(_CEO_TITLE_REGEX)
        & ~_job_title.str.contains(_INTERIM_TITLE_REGEX)
        & (df_cc_pay["Base Pay"] >= _FULL_YEAR_BASE_PAY_FLOOR)
    ]
    # One leader per agency: in multi-college districts, the chancellor
    cc_ceo_pay = _ceo_records.loc[
        _ceo_records.groupby("Agency")["Total Pay"].idxmax()
    ]
    median_exec_pay = round(cc_ceo_pay["Total Pay"].median())

    mo.vstack(
        [
            mo.md(
                f"Median total pay for the top full-year, non-interim leader at "
                f"each of **{len(cc_ceo_pay)}** agencies: "
                f"**${median_exec_pay:,}**"
            ),
            cc_ceo_pay["Job Title"].value_counts(),
            cc_ceo_pay,
        ]
    )
    return (median_exec_pay,)


@app.cell
def _(PROFESSOR_VILLARREAL, instructor_pay_analysis, median_exec_pay):
    instructors_over_exec_pay = instructor_pay_analysis[
        instructor_pay_analysis["pay"] > median_exec_pay
    ].reset_index(drop=True)
    assert (
        PROFESSOR_VILLARREAL
        in instructors_over_exec_pay["canonical_name"].values
    )

    instructors_over_exec_pay
    return (instructors_over_exec_pay,)


@app.cell(hide_code=True)
def _(
    mo,
    top_earner_2024_campus_count,
    top_earner_2024_courses,
    top_paid_instructor,
):
    mo.md(rf"""
    # Top earner course listings count

    Text from SYW draft:
    > The top earner in our analysis taught at least 44 course sections across nine campuses, according to course 2024 catalog records reviewed by CalMatters.

    Fact check:
    > The top earner in our analysis, {top_paid_instructor}, taught at least {len(top_earner_2024_courses)} course sections across {top_earner_2024_campus_count} campuses, according to 2024 course catalog records reviewed by CalMatters.
    """)
    return


@app.cell
def _(scheduled_courses_df, top_paid_instructor):
    top_earner_2024_courses = scheduled_courses_df[
        (scheduled_courses_df["canonical_name"] == top_paid_instructor)
        & scheduled_courses_df["term"].str.endswith("2024")
    ]
    top_earner_2024_campus_count = top_earner_2024_courses["campus"].nunique()

    # Sections per campus and term
    top_earner_2024_courses.groupby(["campus", "term"]).size().unstack(
        fill_value=0
    )
    return top_earner_2024_campus_count, top_earner_2024_courses


@app.cell(hide_code=True)
def _(
    mo,
    top_earner_campus_count,
    top_earner_name_variations,
    top_paid_instructor,
):
    mo.md(rf"""
    # Top earner name variations

    Text from draft:
    > For example: Thien-Huong Villarreal, the top earner on our list, had five different name variations across 11 different schools.

    Fact check:
    > For example: {top_paid_instructor}, the top earner on our list, had {len(top_earner_name_variations)} different name variations across {top_earner_campus_count} different schools.

    Names are compared in lower case, since UC and CSU payroll print names in all caps.
    """)
    return


@app.cell
def _(instructor_college_df, top_paid_instructor):
    _rows = instructor_college_df[
        instructor_college_df["canonical_name"] == top_paid_instructor
    ]
    top_earner_campus_count = _rows["institution"].nunique()
    # CC rows join multiple payroll names for one campus with "; ".
    top_earner_name_variations = (
        _rows["source_name"].str.split("; ").explode().str.lower().unique()
    )

    _rows[["system", "institution", "source_name"]]
    return top_earner_campus_count, top_earner_name_variations


@app.cell(hide_code=True)
def _(cluster_median_pay, mo):
    mo.md(rf"""
    # Instructor clusters median pay

    Text from SYW draft:
    > Median pay for those instructors was $190,000.

    Fact check:
    > Median pay for those instructors was ${cluster_median_pay:,}.

    Full data result (all 72 confirmed instructors, not included in this repo):

    > Median pay for those instructors was $190,923.
    """)
    return


@app.cell
def _(instructor_pay_analysis):
    cluster_median_pay = round(instructor_pay_analysis["pay"].median())
    return (cluster_median_pay,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Instructor fact check lookup
    """)
    return


@app.cell
def _(canonical_group, clusters_labeled_real, mo):
    instructor_picker = mo.ui.dropdown(
        options={
            canonical_group(cluster)["name"]: cluster
            for cluster in clusters_labeled_real
        },
        searchable=True,
        label="Instructor",
    )
    instructor_picker
    return (instructor_picker,)


@app.cell
def _(
    directory_url,
    institution_name,
    instructor_college_df,
    instructor_picker,
    mo,
    verification_for,
):
    mo.stop(
        instructor_picker.value is None,
        mo.md("Select an instructor to generate a fact check."),
    )

    _cluster = instructor_picker.value
    _verification = verification_for(_cluster)
    _rows = instructor_college_df[
        instructor_college_df["cluster_id"] == _cluster["id"]
    ]

    # CC rows join multiple payroll names for one campus with "; ".
    _source_names = _rows["source_name"].str.split("; ").explode().unique()
    _course_count = sum(
        len(courses)
        for courses in _verification.get("scheduleCourses", {}).values()
    )
    _directory_urls = {
        institution_name(_cluster, campus): directory_url(page)
        for campus, page in _verification.get("directoryPages", {}).items()
    }
    _directory_links = [
        f"[{campus}]({url})" for campus, url in _directory_urls.items() if url
    ]

    _pay_by_campus = _rows.groupby("institution", sort=False)["pay"].sum()
    _campus_list = "\n".join(
        f"- {campus}: ${pay:,.0f}" for campus, pay in _pay_by_campus.items()
    )

    mo.md(
        f"{instructor_picker.selected_key} earned ${_rows['pay'].sum():,.0f} from {_rows['institution'].nunique()} campuses:\n\n"
        f"{_campus_list}\n\n"
        f"The names in the payroll system that mapped to this individual: {', '.join(_source_names)}. We found {_course_count} courses taught by this instructor at the listed campuses. We also found additional evidence at: {', '.join(_directory_links) or 'none'}."
    )
    return


@app.cell
def _(institution_name, instructor_picker, mo, pd, verification_for):
    mo.stop(instructor_picker.value is None)

    _SEASONS = ["Winter", "Spring", "Summer", "Fall"]

    def _term_order(term):
        # Terms look like "Fall 2026"; blank terms sort first.
        season, _, year = term.partition(" ")
        return (year, _SEASONS.index(season)) if year else ("", -1)

    _cluster = instructor_picker.value
    _courses = pd.DataFrame(
        [
            {
                "campus": institution_name(_cluster, campus),
                "term": course["semester"],
            }
            for campus, courses in verification_for(_cluster)
            .get("scheduleCourses", {})
            .items()
            for course in courses
        ],
        columns=["campus", "term"],
    )
    # An ordered categorical keeps both tables in chronological term order.
    _courses["term"] = pd.Categorical(
        _courses["term"],
        categories=sorted(_courses["term"].unique(), key=_term_order),
        ordered=True,
    )

    mo.vstack(
        [
            _courses["term"]
            .value_counts(sort=False)
            .rename("courses_found")
            .reset_index(),
            pd.crosstab(_courses["campus"], _courses["term"]).reset_index(),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
