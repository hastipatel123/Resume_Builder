const userId   = localStorage.getItem("user_id");
const userName = localStorage.getItem("user_name");
const userRole = localStorage.getItem("user_role");

if (!userId) window.location.href = "login.html";

document.getElementById("userName").textContent  = userName || "User";
document.getElementById("userAvatar").textContent = (userName || "U").charAt(0).toUpperCase();
document.getElementById("userRole").textContent   = capitalize(userRole || "candidate");

document.getElementById("logoutBtn").addEventListener("click", () => {
    localStorage.removeItem("user_id");
    localStorage.removeItem("user_name");
    localStorage.removeItem("user_role");
    window.location.href = "login.html";
});

let allJobs = [];


// =========================================================
// LOAD JOBS
// =========================================================

async function loadJobs() {
    try {
        const res  = await fetch(`http://127.0.0.1:5000/api/jobs/candidate/${userId}`);
        const data = await res.json();

        if (!res.ok) throw new Error(data.message || "Failed to load jobs");

        allJobs = data.jobs || [];

        if (!data.has_resume) {
            document.getElementById("noResumeWarning").classList.remove("hidden");
        }

        applyFilters();

    } catch (e) {
        console.error(e);
        document.getElementById("jobsGrid").innerHTML = `
            <div class="empty-state" style="grid-column:1/-1">
                <div class="empty-icon">⚠️</div>
                <h3>Could not load jobs</h3>
                <p>${escapeHtml(e.message)}</p>
            </div>`;
    }
}


// =========================================================
// FILTER + SORT + SEARCH
// =========================================================

function applyFilters() {
    const search = document.getElementById("searchInput").value.toLowerCase().trim();
    const sort   = document.getElementById("sortSelect").value;
    const status = document.getElementById("statusFilter").value;

    let filtered = allJobs.filter(job => {
        const matchesSearch =
            !search ||
            job.title.toLowerCase().includes(search) ||
            (job.company || "").toLowerCase().includes(search) ||
            (job.description || "").toLowerCase().includes(search);

        const jobStatus = job.status || "none";
        const matchesStatus = status === "all" || jobStatus === status;

        return matchesSearch && matchesStatus;
    });

    if (sort === "newest") {
        filtered.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    } else if (sort === "score_high") {
        filtered.sort((a, b) => (b.match_score || 0) - (a.match_score || 0));
    } else if (sort === "score_low") {
        filtered.sort((a, b) => (a.match_score || 0) - (b.match_score || 0));
    }

    renderJobs(filtered);
}

document.getElementById("searchInput").addEventListener("input", applyFilters);
document.getElementById("sortSelect").addEventListener("change", applyFilters);
document.getElementById("statusFilter").addEventListener("change", applyFilters);


// =========================================================
// RENDER JOBS GRID
// =========================================================

function renderJobs(jobs) {
    const grid = document.getElementById("jobsGrid");
    const countLabel = document.getElementById("jobsCount");

    countLabel.textContent = `${jobs.length} job${jobs.length !== 1 ? "s" : ""} found`;

    if (!jobs.length) {
        grid.innerHTML = `
            <div class="empty-state" style="grid-column:1/-1">
                <div class="empty-icon">💼</div>
                <h3>No jobs found</h3>
                <p>Try adjusting your search or filters.</p>
            </div>`;
        return;
    }

    grid.innerHTML = jobs.map(job => {
        const hasScore  = job.match_score !== null && job.match_score !== undefined;
        const score     = hasScore ? job.match_score : null;
        const scoreColor = score >= 70 ? "score-high" : score >= 40 ? "score-mid" : "score-low";
        const status    = job.status || "none";

        const scoreBadge = hasScore
            ? `<div class="job-score-badge ${scoreColor}">${score}% Match</div>`
            : `<div class="job-score-badge score-none">No Score</div>`;

        const statusBadge = status !== "none"
            ? `<span class="status-badge status-${status}">${capitalize(status)}</span>`
            : "";

        const skills = (job.matched_skills || []).slice(0, 3);
        const skillTags = skills.map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join("");

        return `
            <div class="job-card" onclick="openModal(${job.job_id})">

                <div class="job-card-top">
                    <div class="job-card-icon">💼</div>
                    ${scoreBadge}
                </div>

                <div class="job-card-body">
                    <h3 class="job-card-title">${escapeHtml(job.title)}</h3>
                    <p class="job-card-company">🏢 ${escapeHtml(job.company || "Company not specified")}</p>
                    <p class="job-card-date">📅 ${formatDate(job.created_at)}</p>

                    ${skillTags ? `<div class="job-card-skills">${skillTags}</div>` : ""}
                </div>

                <div class="job-card-footer">
                    ${statusBadge}
                    <span class="job-view-link">View Details →</span>
                </div>

            </div>`;
    }).join("");
}


// =========================================================
// MODAL
// =========================================================

function openModal(jobId) {
    const job = allJobs.find(j => j.job_id === jobId);
    if (!job) return;

    document.getElementById("modalTitle").textContent   = job.title;
    document.getElementById("modalCompany").textContent = job.company || "Company not specified";
    document.getElementById("modalDate").textContent    = `📅 Posted ${formatDate(job.created_at)}`;

    const hasScore = job.match_score !== null && job.match_score !== undefined;
    const scoreEl  = document.getElementById("modalScore");
    if (hasScore) {
        const cls = job.match_score >= 70 ? "score-high" : job.match_score >= 40 ? "score-mid" : "score-low";
        scoreEl.innerHTML = `<span class="modal-score-badge ${cls}">${job.match_score}% Match</span>`;
    } else {
        scoreEl.textContent = "";
    }

    const status   = job.status || "none";
    const statusEl = document.getElementById("modalStatus");
    statusEl.innerHTML = status !== "none"
        ? `<span class="status-badge status-${status}">${capitalize(status)}</span>`
        : "";

    
    // Configure Apply Now button for the selected job.
    const applyButton = document.getElementById("applyNowBtn");
    const applyMessage = document.getElementById("applyMessage");

    applyMessage.classList.add("hidden");
    applyMessage.classList.remove("success", "error");

    const alreadyApplied = [
        "applied",
        "approved",
        "rejected"
    ].includes(status);

    if (alreadyApplied) {
        applyButton.textContent =
            status === "applied" ? "Applied" : capitalize(status);

        applyButton.disabled = true;
    } else {
        applyButton.textContent = "Apply Now";
        applyButton.disabled = false;
    }

    applyButton.onclick = function () {
        if (userRole !== "candidate") {
            applyMessage.textContent =
                "Only candidates can apply for jobs.";
            applyMessage.classList.add("error");
            applyMessage.classList.remove("hidden");
            return;
        }

        applyForJob(job.job_id);
    };


    document.getElementById("modalDescription").textContent = job.description || "No description provided.";

    // Matched skills
    const skills    = job.matched_skills || [];
    const skillsSec = document.getElementById("modalSkillsSection");
    const skillsEl  = document.getElementById("modalSkills");
    if (skills.length) {
        skillsEl.innerHTML = skills.map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join("");
        skillsSec.classList.remove("hidden");
    } else {
        skillsSec.classList.add("hidden");
    }

    // Matched keywords
    const keywords  = job.matched_keywords || [];
    const kwSec     = document.getElementById("modalKeywordsSection");
    const kwEl      = document.getElementById("modalKeywords");
    if (keywords.length) {
        kwEl.innerHTML = keywords.map(k => `<span class="keyword-tag">${escapeHtml(k)}</span>`).join("");
        kwSec.classList.remove("hidden");
    } else {
        kwSec.classList.add("hidden");
    }

    document.getElementById("jobModal").classList.remove("hidden");
    document.body.style.overflow = "hidden";
}


async function applyForJob(jobId) {
    const button = document.getElementById("applyNowBtn");
    const message = document.getElementById("applyMessage");

    message.classList.add("hidden");
    message.classList.remove("success", "error");

    button.disabled = true;
    button.textContent = "Submitting...";

    try {
        const response = await fetch(
            `http://127.0.0.1:5000/api/jobs/${jobId}/apply`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    user_id: userId
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || "Application failed.");
        }

        // Update the job status without reloading the page.
        const job = allJobs.find(
            item => Number(item.job_id) === Number(jobId)
        );

        if (job) {
            job.status = "applied";
        }

        document.getElementById("modalStatus").innerHTML =
            '<span class="status-badge status-applied">Applied</span>';

        button.textContent = "Applied";
        button.disabled = true;

        message.textContent =
            data.message || "Application submitted successfully.";

        message.classList.add("success");
        message.classList.remove("hidden");

        // Refresh the listing and status filters.
        applyFilters();

    } catch (error) {
        message.textContent = error.message;
        message.classList.add("error");
        message.classList.remove("hidden");

        button.disabled = false;
        button.textContent = "Apply Now";

        console.error("Application error:", error);
    }
}


function closeModal(e) {
    if (e && e.target !== document.getElementById("jobModal")) return;
    document.getElementById("jobModal").classList.add("hidden");
    document.body.style.overflow = "";
}

document.addEventListener("keydown", e => {
    if (e.key === "Escape") closeModal();
});


// =========================================================
// HELPERS
// =========================================================

function escapeHtml(v) {
    if (!v) return "";
    return String(v)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;")
        .replace(/>/g, "&gt;").replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function capitalize(s) {
    return s ? s.charAt(0).toUpperCase() + s.slice(1) : "";
}

function formatDate(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}


loadJobs();