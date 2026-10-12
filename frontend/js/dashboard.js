const userId = localStorage.getItem("user_id");
const userName = localStorage.getItem("user_name");
const userRole = localStorage.getItem("user_role") || "candidate";


// If user is not logged in
if (!userId) {
    window.location.href = "login.html";
}

// Redirect recruiter to their own dashboard
if (userRole === "recruiter") {
    window.location.href = "recruiter_dashboard.html";
}


// Display user information
if (userName) {

    document.getElementById("userName").textContent = userName;

    document.getElementById("welcomeName").textContent = userName;

    document.getElementById("userAvatar").textContent =
        userName.charAt(0).toUpperCase();

    const roleLabel = document.getElementById("userRole");
    if (roleLabel) {
        roleLabel.textContent =
            userRole.charAt(0).toUpperCase() + userRole.slice(1);
    }
}


// Logout
document.getElementById("logoutBtn").addEventListener("click", function () {

    localStorage.removeItem("user_id");
    localStorage.removeItem("user_name");
    localStorage.removeItem("user_role");

    window.location.href = "login.html";
});


// Load dashboard information
async function loadDashboard() {

    try {

        const response = await fetch(
            `http://127.0.0.1:5000/api/dashboard/${userId}`
        );

        if (!response.ok) {
            throw new Error("Unable to load dashboard");
        }

        const data = await response.json();

        console.log("Dashboard:", data);


        // Statistics
        document.getElementById("resumeCount").textContent =
            data.resume_count || 0;

        document.getElementById("jobCount").textContent =
            data.job_count || 0;

        document.getElementById("matchCount").textContent =
            data.match_count || 0;

        document.getElementById("bestScore").textContent =
            `${data.best_score || 0}%`;


        // Latest resume
        if (data.latest_resume) {

            document.getElementById("latestResume").innerHTML = `

                <div class="resume-info">

                    <div class="resume-file-icon">
                        📄
                    </div>

                    <div class="resume-details">

                        <h3>
                            ${escapeHtml(data.latest_resume.filename)}
                        </h3>

                        <p>
                            Uploaded successfully
                        </p>

                    </div>

                </div>

            `;
        }


        // Top matches
        if (data.top_matches && data.top_matches.length > 0) {

            let html = "";

            data.top_matches.forEach(match => {

                html += `

                    <div class="match-item">

                        <div class="match-job">

                            <h3>
                                ${escapeHtml(match.title)}
                            </h3>

                            <p>
                                ${escapeHtml(match.company || "Company")}
                            </p>

                        </div>

                        <div class="match-score">
                            ${match.match_score}%
                        </div>

                    </div>

                `;
            });

            document.getElementById("topMatches").innerHTML = html;
        }

    } catch (error) {

        console.error(error);

    }

}


// Prevent HTML injection
function escapeHtml(value) {

    if (!value) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


loadDashboard();