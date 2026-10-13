<?php
require __DIR__ . '/config.php';

$SECRET_PASSWORD = SECRET_PASSWORD;
$FLAG = get_flag();

$msg = "";

function hash_brown($input)
{
    $h = 0;
    for ($i = 0; $i < strlen($input); $i++) {
        $h += ord($input[$i]);
    }
    $hex = dechex($h);
    if (strlen($hex) % 2 !== 0) {
        $hex = "0" . $hex;
    }
    return $hex;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $salt = $_POST['salt'] ?? '';

    $input = $SECRET_PASSWORD . $salt;

    $md5  = md5($input);
    $md5_check  = substr($md5, 0, 10);
    $sha1 = sha1($input);
    $sha1_check = substr($sha1, 0, 10);
    $cust = hash_brown($input);

    if (($md5_check == $cust) && ($sha1_check == $cust))
    {
        $msg = "FLAG: " . $FLAG;
    }
    else if ($md5_check == $cust)
    {
        $msg = "HINT: " . $SECRET_PASSWORD;
    }
    else
    {
        $msg = "Wrong!";
    }
    $msg = $msg . "\nmd5 = " . $md5 . "\nsha1 = " . $sha1 . "\ncust = " . $cust;
}
?>

<!DOCTYPE html>
<html>
<head>
    <title>Salted Collision</title>
    <style>
        body { background:#0f0f0f; color:#eee; font-family:Arial; }
        input { padding:10px; margin:5px; width:260px; }
        button { padding:10px 20px; }
        .box { margin-top:120px; text-align:center; }
        .msg { color:#ff5555; }
    </style>
</head>
<body>

<div class="box">
    <h1>Salted Collision</h1>
    <p>Find a salt that passes all checks.</p>

    <form method="POST">
        <!-- <input name="pepper" placeholder="pepper"><br> -->
        <input name="salt" placeholder="salt"><br>
        <button>Login</button>
    </form>

    <pre class="msg"><?php echo $msg; ?></pre>

</div>
<div>
    <h2>Leaked Source Code</h2>
    <pre>
$FLAG = "NZCSC{FAKE_FLAG_FOR_TESTING}";

$msg = "";

function hash_brown($input)
{
    $h = 0;
    for ($i = 0; $i < strlen($input); $i++) {
        $h += ord($input[$i]);
    }
    $hex = dechex($h);
    if (strlen($hex) % 2 !== 0) {
        $hex = "0" . $hex;
    }
    return $hex;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $salt = $_POST['salt'] ?? '';

    $input = $SECRET_PASSWORD . $salt;

    $md5  = md5($input);
    $md5_check  = substr($md5, 0, 10);
    $sha1 = sha1($input);
    $sha1_check = substr($sha1, 0, 10);
    $cust = hash_brown($input);

    if (($md5_check == $cust) && ($sha1_check == $cust))
    {
        $msg = "FLAG: " . $FLAG;
    }
    else if ($md5_check == $cust)
    {
        $msg = "HINT: " . $SECRET_PASSWORD;
    }
    else
    {
        $msg = "Wrong!";
    }
    $msg = $msg . "\nmd5 = " . $md5 . "\nsha1 = " . $sha1 . "\ncust = " . $cust;
}
    </pre>
</div>

</body>
</html>
