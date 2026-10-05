const registerForm = document.getElementById("registerForm");

registerForm.addEventListener("submit", async function(event) {

    event.preventDefault();

    const name = document.getElementById("name").value;
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    const message = document.getElementById("message");

    try {

        const response = await fetch(
            "http://127.0.0.1:5000/api/register",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    name: name,
                    email: email,
                    password: password
                })
            }
        );


        const data = await response.json();


        if (response.ok) {

            message.innerText = data.message;

            registerForm.reset();

        } else {

            message.innerText = data.message;
        }

    } catch (error) {

        console.error(error);

        message.innerText =
            "Unable to connect to the server.";
    }

});