const userId = localStorage.getItem("user_id");
const userName = localStorage.getItem("user_name");


// =========================
// LOGIN CHECK
// =========================

if (!userId) {
    window.location.href = "login.html";
}


// =========================
// USER INFORMATION
// =========================

if (userName) {
    document.getElementById("userName").textContent = userName;
    document.getElementById("userAvatar").textContent = userName.charAt(0).toUpperCase();
    const roleEl = document.getElementById("userRole");
    if (roleEl) roleEl.textContent = (localStorage.getItem("user_role") || "candidate").charAt(0).toUpperCase() + (localStorage.getItem("user_role") || "candidate").slice(1);
}


// =========================
// ELEMENTS
// =========================

const resumeFile =
    document.getElementById("resumeFile");

const selectedFile =
    document.getElementById("selectedFile");

const uploadBtn =
    document.getElementById("uploadBtn");

const dropArea =
    document.getElementById("dropArea");

const loading =
    document.getElementById("loading");

const errorMessage =
    document.getElementById("errorMessage");

const successMessage =
    document.getElementById("successMessage");

const resultsSection =
    document.getElementById("resultsSection");


// =========================
// FILE SELECT
// =========================

resumeFile.addEventListener("change", function () {

    if (resumeFile.files.length === 0) {

        selectedFile.textContent =
            "No file selected";

        uploadBtn.disabled = true;

        return;
    }


    const file = resumeFile.files[0];


    // Check PDF
    if (file.type !== "application/pdf") {

        showError("Please select a PDF file.");

        resumeFile.value = "";

        uploadBtn.disabled = true;

        return;
    }


    // File size
    const maxSize =
        10 * 1024 * 1024;


    if (file.size > maxSize) {

        showError(
            "File size must be less than 10 MB."
        );

        resumeFile.value = "";

        uploadBtn.disabled = true;

        return;
    }


    selectedFile.textContent =
        `Selected: ${file.name}`;

    uploadBtn.disabled = false;

    hideMessages();

});


// =========================
// DRAG & DROP
// =========================

dropArea.addEventListener("dragover", function (event) {

    event.preventDefault();

    dropArea.classList.add("dragover");

});


dropArea.addEventListener("dragleave", function () {

    dropArea.classList.remove("dragover");

});


dropArea.addEventListener("drop", function (event) {

    event.preventDefault();

    dropArea.classList.remove("dragover");

    const files = event.dataTransfer.files;

    if (files.length === 0) {
        return;
    }


    const file = files[0];


    if (file.type !== "application/pdf") {

        showError("Please upload a PDF file.");

        return;
    }


    // Put dropped file into input
    const dataTransfer = new DataTransfer();

    dataTransfer.items.add(file);

    resumeFile.files =
        dataTransfer.files;


    selectedFile.textContent =
        `Selected: ${file.name}`;

    uploadBtn.disabled = false;

    hideMessages();

});


// =========================
// UPLOAD
// =========================

uploadBtn.addEventListener("click", async function () {

    if (resumeFile.files.length === 0) {

        showError(
            "Please select a resume first."
        );

        return;
    }


    const file = resumeFile.files[0];


    const formData = new FormData();

    formData.append("resume", file);

    formData.append("user_id", userId);


    // UI
    uploadBtn.disabled = true;

    loading.classList.remove("hidden");

    resultsSection.classList.add("hidden");

    hideMessages();


   try {
    const response = await fetch(
        "http://127.0.0.1:5000/api/resume/upload",
        {
            method: "POST",
            body: formData
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.error ||
            data.message ||
            "Resume upload failed."
        );
    }

    // Display the newly uploaded resume analysis.
    displayResults(data);

    showSuccess("Resume uploaded and analyzed successfully.");

    console.log(
        "Resume uploaded successfully:",
        data.resume_id
    );

} catch (error) {
    console.error("Resume upload failed:", error);
    showError(error.message);
} finally {
    uploadBtn.disabled = false;
    loading.classList.add("hidden");
}

});


// =========================
// DISPLAY RESULTS
// =========================

function displayResults(data) {

    resultsSection.classList.remove("hidden");


    // Skills
    displayTags(
        "skillsContainer",
        data.skills || [],
        "skill-tag"
    );


    // Keywords
    displayTags(
        "keywordsContainer",
        data.keywords || [],
        "keyword-tag"
    );


    // Education
    document.getElementById("education").textContent =
        data.education ||
        "No education section detected.";


    // Experience
    document.getElementById("experience").textContent =
        data.experience ||
        "No experience section detected.";


    // Projects
    document.getElementById("projects").textContent =
        data.projects ||
        "No projects section detected.";


    // Job matches
    displayJobMatches(
        data.matches || []
    );


    // Scroll to results
    resultsSection.scrollIntoView({
        behavior: "smooth"
    });

}


// =========================
// DISPLAY TAGS
// =========================

function displayTags(
    elementId,
    values,
    className
) {

    const container =
        document.getElementById(elementId);


    if (!values || values.length === 0) {

        container.innerHTML =
            `<span class="empty-result">
                No data found
             </span>`;

        return;
    }


    container.innerHTML = "";


    values.forEach(value => {

        const tag =
            document.createElement("span");

        tag.className = className;

        tag.textContent = value;

        container.appendChild(tag);

    });

}


// =========================
// JOB MATCHES
// =========================

function displayJobMatches(matches) {

    const container =
        document.getElementById("jobMatches");


    if (!matches || matches.length === 0) {

        container.innerHTML = `

            <div class="no-matches">

                <div>🎯</div>

                <h3>
                    No job matches yet
                </h3>

                <p>
                    Add jobs from the Jobs page to
                    calculate resume matching scores.
                </p>

            </div>

        `;

        return;
    }


    container.innerHTML = "";


    matches.forEach(match => {

        const score =
            Number(match.match_score || 0);


        const row =
            document.createElement("div");

        row.className =
            "match-row";


        row.innerHTML = `

            <div class="match-information">

                <h3>
                    ${escapeHtml(match.title)}
                </h3>

                <p>
                    ${escapeHtml(
                        match.company || "Company"
                    )}
                </p>

            </div>


            <div class="score-area">

                <div class="score-text">

                    <span>
                        Match Score
                    </span>

                    <span>
                        ${score.toFixed(2)}%
                    </span>

                </div>


                <div class="score-bar">

                    <div
                        class="score-fill"
                        style="width: ${Math.min(score, 100)}%">
                    </div>

                </div>

            </div>

        `;


        container.appendChild(row);

    });

}

async function loadLatestResume() {
    if (!userId) {
        return;
    }

    try {
        const response = await fetch(
            `http://127.0.0.1:5000/api/resume/candidate/${userId}`,
            {
                method: "GET",
                cache: "no-store"
            }
        );

        if (response.status === 404) {
            // This candidate has not uploaded a resume yet.
            return;
        }

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.message || "Could not load the latest resume."
            );
        }

        // Load job matches separately because the latest-resume
        // endpoint returns resume analysis, not job matches.
        const jobsResponse = await fetch(
            `http://127.0.0.1:5000/api/jobs/candidate/${userId}`,
            {
                method: "GET",
                cache: "no-store"
            }
        );

        let matches = [];

        if (jobsResponse.ok) {
            const jobsData = await jobsResponse.json();
            matches = jobsData.jobs || [];
        }

        // Use your existing rendering functions.
        displayResults({
            ...data,
            matches: matches
        });

    } catch (error) {
        console.error("Loading latest resume failed:", error);
    }
}


// =========================
// MESSAGES
// =========================

function showError(message) {

    errorMessage.textContent =
        message;

    errorMessage.classList.remove(
        "hidden"
    );

    successMessage.classList.add(
        "hidden"
    );

}


function showSuccess(message) {

    successMessage.textContent =
        message;

    successMessage.classList.remove(
        "hidden"
    );

    errorMessage.classList.add(
        "hidden"
    );

}


function hideMessages() {

    errorMessage.classList.add(
        "hidden"
    );

    successMessage.classList.add(
        "hidden"
    );

}


// =========================
// SECURITY
// =========================

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


// =========================
// LOGOUT
// =========================

document.getElementById("logoutBtn")
    .addEventListener("click", function () {

        localStorage.removeItem("user_id");
        localStorage.removeItem("user_name");
        localStorage.removeItem("user_role");
        window.location.href = "login.html";

    });

// Load the latest saved resume when the page opens.
document.addEventListener("DOMContentLoaded", function () {
    loadLatestResume();
});