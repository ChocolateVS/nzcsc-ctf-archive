<?php
// config.php — NOT displayed to the client (PHP is executed, never served as text).
// The secret password is fixed so the intended solve path reproduces exactly; the
// flag is injected at runtime via the FLAG environment variable and is never
// hard-coded here.

define('SECRET_PASSWORD', 'S3cr3tSalt_Yolo1237791283981727461079');

function get_flag() {
    $f = getenv('FLAG');
    if ($f === false || $f === '') {
        $f = 'NZCSC{placeholder_set_the_real_flag_in_flags.env}';
    }
    return $f;
}
