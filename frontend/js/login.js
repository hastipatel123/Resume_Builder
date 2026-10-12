const loginForm = document.getElementById("loginForm");


loginForm.addEventListener("submit", async function(event) {

    event.preventDefault();


    const email =
        document.getElementById("email").value;

    const password =
        document.getElementById("password").value;

    const role =
        document.getElementById("role").value;

    const message =
        document.getElementById("message");


    try {

        const response = await fetch(
            "http://127.0.0.1:5000/api/login",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    email: email,
                    password: password,
                    role: role
                })
            }
        );


        const data = await response.json();


        if (response.ok) {

            message.innerText = data.message;


            // Save logged-in user's ID
            localStorage.setItem(
                "user_id",
                data.user_id
            );


            // Save user's name and role
            localStorage.setItem(
                "user_name",
                data.name
            );

            localStorage.setItem(
                "user_role",
                data.role
            );


            // Redirect after successful login
            window.location.href = "dashboard.html";


        } else {

            message.innerText = data.message;

        }


    } catch (error) {

        console.error(error);

        message.innerText =
            "Unable to connect to the server.";

    }

});