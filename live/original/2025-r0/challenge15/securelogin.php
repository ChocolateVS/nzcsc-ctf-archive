
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Login Page</title>
    <style>
        body {
            font-family: sans-serif;
            background: #f2f2f2;
            padding: 50px;
        }
        .login-box {
            background: #fff;
            padding: 20px;
            width: 300px;
            margin: auto;
            border-radius: 4px;
            box-shadow: 0 0 5px rgba(0,0,0,0.3);
        }
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 8px;
            margin: 5px 0 10px 0;
            box-sizing: border-box;
        }
        input[type="submit"] {
            width: 100%;
            padding: 8px;
            background: #007BFF;
            color: #fff;
            border: none;
            cursor: pointer;
        }
        input[type="submit"]:hover {
            background: #0056b3;
        }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>Login for flag</h2>
        <form method="post" action="">
            <label>Username:</label>
            <input type="text" name="username" required>
            <label>Password:</label>
            <input type="password" name="password" required>
            <input type="submit" value="Login">
        </form>

            </div>

    <script>

        function f1() {
            let x = 0;
            for (let i = 0; i < 100; i++) {
                x += i * 2;
            }
            console.log("f 1:", x);
        }

        function f2() {
            let str = "";
            for (let i = 0; i < 50; i++) {
                str += "line " + i + " ";
            }
            console.log("f 2:", str);
        }

        f1();
        f2();


        for (let i = 0; i < 20; i++) {
            console.log("This is f line number:", i);
        }

        const fArray = [];
        for (let i = 0; i < 100; i++) {
            fArray.push(i * 3);
        }
        console.log("f array created.");

        function anotherf() {
            let total = 0;
            for (let i = 0; i < 200; i++) {
                total += Math.sqrt(i);
            }
            console.log("Another f sum:", total);
        }

        anotherf();

        // Even more f
        let fObj = {
            name: "f",
            value: 123,
            data: []
        };

        for (let i = 0; i < 50; i++) {
            fObj.data.push({ id: i, val: i * i });
        }

        console.log("admin");
        console.log("21wdni#niu7@e4");

        function d1() {
            for (let a = 0; a < 30; a++) {
                for (let b = 0; b < 30; b++) {
                    let temp = a * b;
                }
            }
            console.log("loop finished.");
        }

        d1();


        console.log("debug");
    </script>
</body>
</html>
