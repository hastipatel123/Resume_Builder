
const userId = localStorage.getItem("user_id");
const userName = localStorage.getItem("user_name");
const userRole = localStorage.getItem("user_role");

if (!userId || userRole !== "recruiter") {
    window.location.href = "login.html";
}

// Display user information
document.getElementById("userName").textContent = userName || "Recruiter";
document.getElementById("userAvatar").textContent =
    (userName || "R").charAt(0).toUpperCase();

// Logout
document.getElementById("logoutBtn").addEventListener("click", () => {
    localStorage.removeItem("user_id");
    localStorage.removeItem("user_name");
    localStorage.removeItem("user_role");
    window.location.href = "login.html";
});

// Smooth scroll for Post a Job
document.getElementById("navPostJob").addEventListener("click", (e) => {
    e.preventDefault();
    document.getElementById("post-job").scrollIntoView({
        behavior: "smooth"
    });
});

let allCandidates = [];
let currentJobId = null;
let currentFilter = "all";

// =========================================================
// INITIALIZE DASHBOARD
// =========================================================

async function init() {
    await loadStats();
    await loadMyJobs();
}

// =========================================================
// LOAD DASHBOARD STATS
// =========================================================

async function loadStats() {
    try {
        const res = await fetch(
            `http://127.0.0.1:5000/api/recruiter/dashboard/${userId}`
        );

        const data = await res.json();

        if (!res.ok) {
            console.error(data.message || "Unable to load statistics");
            return;
        }

        document.getElementById("statJobs").textContent =
            data.jobs_posted ?? 0;

        document.getElementById("statApplicants").textContent =
            data.total_applicants ?? 0;

        document.getElementById("statApproved").textContent =
            data.approved_count ?? 0;

        document.getElementById("statRejected").textContent =
            data.rejected_count ?? 0;

    } catch (error) {
        console.error("Dashboard stats error:", error);
    }
}

// =========================================================
// LOAD RECRUITER JOBS
// =========================================================

async function loadMyJobs() {
    const container = document.getElementById("jobsList");

    try {
        const res = await fetch(
            `http://127.0.0.1:5000/api/recruiter/${userId}/jobs`
        );

        const jobs = await res.json();

        if (!res.ok) {
            container.innerHTML = `
                <div class="empty-state">
                    <h3>Unable to load jobs</h3>
                    <p>${escapeHtml(jobs.message || "Please try again.")}</p>
                </div>`;
            return;
        }

        if (!Array.isArray(jobs) || jobs.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">💼</div>
                    <h3>No jobs posted yet</h3>
                    <p>Use the form above to post your first job opening.</p>
                </div>`;
            return;
        }

        
container.innerHTML = jobs.map(job => `
    <div class="job-row" id="job-row-${job.job_id}">
        <div class="job-row-info">
            <h3>${escapeHtml(job.title)}</h3>
            <p>
                ${escapeHtml(job.company || "—")}
                · Posted ${formatDate(job.created_at)}
            </p>
        </div>

        <div class="job-row-meta">
            <span class="applicant-count">
                👥 ${job.applicant_count ?? 0}
                applicant${Number(job.applicant_count) !== 1 ? "s" : ""}
            </span>

            <button type="button"
                class="view-btn"
                data-job-id="${Number(job.job_id)}">
                View Candidates
            </button>
        </div>
    </div>
`).join("");

// Attach click handlers after rendering the job rows.
container.querySelectorAll(".view-btn").forEach(button => {
    button.addEventListener("click", () => {
        const jobId = Number(button.dataset.jobId);
        const job = jobs.find(item => Number(item.job_id) === jobId);

        if (job) {
            viewCandidates(
                job.job_id,
                job.title || "",
                job.company || ""
            );
        }
    });
});


    } catch (error) {
        console.error("Load jobs error:", error);

        container.innerHTML = `
            <div class="empty-state">
                <h3>Unable to connect to server</h3>
                <p>Check whether your Flask application is running.</p>
            </div>`;
    }
}

// =========================================================
// VIEW CANDIDATES FOR A JOB
// =========================================================

async function viewCandidates(jobId, title, company) {
    currentJobId = jobId;
    currentFilter = "all";
    allCandidates = [];

    document.querySelectorAll(".job-row").forEach(row => {
        row.classList.remove("selected");
    });

    const jobRow = document.getElementById(`job-row-${jobId}`);

    if (jobRow) {
        jobRow.classList.add("selected");
    }

    document.getElementById("selectedJobTitle").textContent = title;
    document.getElementById("selectedJobCompany").textContent = company;

    const panel = document.getElementById("candidatesPanel");
    panel.classList.remove("hidden");
    panel.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });

    document.querySelectorAll(".filter-tab").forEach(tab => {
        tab.classList.toggle(
            "active",
            tab.dataset.filter === "all"
        );
    });

    const container = document.getElementById("candidatesList");
    container.innerHTML = "<p>Loading candidates...</p>";

    try {
        const res = await fetch(
            `http://127.0.0.1:5000/api/recruiter/jobs/${jobId}/candidates`
        );

        const data = await res.json();

        if (!res.ok) {
            container.innerHTML = `
                <div class="no-candidates">
                    <h3>Unable to load candidates</h3>
                    <p>${escapeHtml(data.message || "Please try again.")}</p>
                </div>`;
            return;
        }

        allCandidates = Array.isArray(data) ? data : [];
        renderCandidates(allCandidates);

    } catch (error) {
        console.error("Load candidates error:", error);

        container.innerHTML = `
            <div class="no-candidates">
                <h3>Unable to connect to server</h3>
                <p>Check your Flask application.</p>
            </div>`;
    }
}

// =========================================================
// CLOSE CANDIDATES PANEL
// =========================================================

function closeCandidates() {
    document.getElementById("candidatesPanel").classList.add("hidden");

    document.querySelectorAll(".job-row").forEach(row => {
        row.classList.remove("selected");
    });

    currentJobId = null;
    currentFilter = "all";
    allCandidates = [];
}

// =========================================================
// RENDER CANDIDATES
// =========================================================

function renderCandidates(list) {
    const container = document.getElementById("candidatesList");

    if (!list || list.length === 0) {
        const message = currentFilter === "pending"
            ? "No pending candidates."
            : currentFilter === "approved"
                ? "No approved candidates."
                : currentFilter === "rejected"
                    ? "No rejected candidates."
                    : "No applications have been submitted for this job yet.";

        container.innerHTML = `
            <div class="no-candidates">
                <div>👥</div>
                <h3>No candidates found</h3>
                <p>${message}</p>
            </div>`;
        return;
    }

    container.innerHTML = list.map(candidate => {
        const skills = Array.isArray(candidate.skills)
            ? candidate.skills
            : [];

        const status = (
            candidate.status || "pending"
        ).toLowerCase();

        let actionButtons = "";

        if (status === "pending") {
            actionButtons = `
                <button class="approve-btn"
                    onclick="updateStatus(${candidate.match_id}, 'approved')">
                    ✓ Approve
                </button>

                <button class="reject-btn"
                    onclick="updateStatus(${candidate.match_id}, 'rejected')">
                    ✕ Reject
                </button>`;
        } else if (status === "approved") {
            actionButtons = `
                <span class="status-badge status-approved">
                    Approved
                </span>

                <button class="reject-btn"
                    onclick="updateStatus(${candidate.match_id}, 'rejected')">
                    Reject
                </button>`;
        } else if (status === "rejected") {
            actionButtons = `
                <span class="status-badge status-rejected">
                    Rejected
                </span>

                <button class="approve-btn"
                    onclick="updateStatus(${candidate.match_id}, 'approved')">
                    Approve
                </button>`;
        }

        return `
            <div class="candidate-row" id="candidate-${candidate.match_id}">
                <div class="candidate-avatar">
                    ${escapeHtml(
                        (candidate.candidate_name || "C")
                            .charAt(0).toUpperCase()
                    )}
                </div>

                <div class="candidate-info">
                    <h4>${escapeHtml(candidate.candidate_name || "Candidate")}</h4>

                    <p>
                        ${escapeHtml(candidate.candidate_email || "")}
                        · Resume: ${escapeHtml(candidate.filename || "N/A")}
                    </p>

                    <div class="candidate-skills">
                        ${skills.slice(0, 5).map(skill =>
                            `<span>${escapeHtml(skill)}</span>`
                        ).join("")}

                        ${skills.length > 5
                            ? `<span>+${skills.length - 5} more</span>`
                            : ""}
                    </div>
                </div>

                <div class="candidate-score-col">
                    <span class="c-score">
                        ${Number(candidate.match_score || 0).toFixed(2)}%
                    </span>
                    <span class="c-score-label">Match</span>
                </div>

                <div class="candidate-actions">
                    ${actionButtons}
                </div>
            </div>`;
    }).join("");
}

// =========================================================
// FILTER: ALL / PENDING / APPROVED / REJECTED
// =========================================================

function filterCandidates(filter, btn) {
    currentFilter = filter;

    document.querySelectorAll(".filter-tab").forEach(tab => {
        tab.classList.remove("active");
    });

    if (btn) {
        btn.classList.add("active");
    }

    const filtered = filter === "all"
        ? allCandidates
        : allCandidates.filter(candidate =>
            (candidate.status || "pending").toLowerCase() === filter
        );

    renderCandidates(filtered);
}

// =========================================================
// APPROVE / REJECT / CHANGE STATUS
// =========================================================

async function updateStatus(matchId, status) {
    if (!["pending", "approved", "rejected"].includes(status)) {
        alert("Invalid candidate status.");
        return;
    }

    const candidate = allCandidates.find(
        item => Number(item.match_id) === Number(matchId)
    );

    if (!candidate) {
        alert("Candidate not found. Refresh the candidate list.");
        return;
    }

    try {
        const res = await fetch(
            `http://127.0.0.1:5000/api/recruiter/matches/${matchId}/status`,
            {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ status })
            }
        );

        const data = await res.json();

        if (!res.ok) {
            alert(data.message || data.error || "Unable to update status.");
            return;
        }

        // Update local status.
        candidate.status = status;

        // Re-render using the currently selected section.
        // If the candidate changed sections, they disappear from the
        // old section and appear in the correct section when selected.
        const filtered = currentFilter === "all"
            ? allCandidates
            : allCandidates.filter(item =>
                (item.status || "pending").toLowerCase() === currentFilter
            );

        renderCandidates(filtered);

        // Refresh dashboard statistics and job applicant counts.
        await loadStats();
        await loadMyJobs();

        console.log(data.message || "Candidate status updated.");

    } catch (error) {
        console.error("Update status error:", error);
        alert("Unable to connect to the server.");
    }
}

// =========================================================
// POST JOB FORM
// =========================================================

document.getElementById("postJobForm").addEventListener("submit", async e => {
    e.preventDefault();

    const title = document.getElementById("jobTitle").value.trim();
    const company = document.getElementById("jobCompany").value.trim();
    const description = document.getElementById("jobDescription").value.trim();
    const messageElement = document.getElementById("jobMessage");

    messageElement.className = "r-message hidden";
    messageElement.textContent = "";

    if (!title || !company || !description) {
        messageElement.className = "r-message error";
        messageElement.textContent = "Please fill in all job fields.";
        return;
    }

    try {
        const res = await fetch("http://127.0.0.1:5000/api/jobs", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                recruiter_id: userId,
                title,
                company,
                description
            })
        });

        const data = await res.json();

        messageElement.classList.remove("hidden");

        if (res.ok) {
            messageElement.classList.add("success");
            messageElement.textContent =
                `✓ "${data.title || title}" posted successfully!`;

            document.getElementById("postJobForm").reset();

            await loadMyJobs();
            await loadStats();
        } else {
            messageElement.classList.add("error");
            messageElement.textContent =
                data.message || "Failed to post job.";
        }

    } catch (error) {
        console.error("Post job error:", error);

        messageElement.className = "r-message error";
        messageElement.textContent =
            "Unable to connect to the server.";
    }
});

// =========================================================
// HELPER FUNCTIONS
// =========================================================

function escapeHtml(value) {
    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function capitalize(value) {
    return value
        ? value.charAt(0).toUpperCase() + value.slice(1)
        : "";
}

function formatDate(value) {
    if (!value) return "";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "";
    }

    return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric"
    });
}

// =========================================================
// START
// =========================================================

init();
