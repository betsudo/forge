# Deadline and process ownership

Expose --keygen-timeout-seconds as an integer from 1 to 86400, default 180.
Validate before compiler cleanup and validate the private hook configuration again.
Apply the deadline to each prepare invocation, including store/lease waiting; it
is not a whole-compile deadline. Profile queries retain the existing 180s limit.
Start each captured Forge command in its own POSIX session. On deadline or Python/keyboard
interruption kill that command's process group, reap it and drain its pipes before
reporting failure. This includes a spawned generation worker and prevents detached
late publication after a timed-out prepare. Normal exit statuses still fail closed. Abrupt hook termination (including default
SIGTERM/SIGKILL) is not a cleanup guarantee; it remains an explicit recovery case.
The compiler hook never writes its completed marker on failure and the actual
compiler cannot finalize its successful manifest. Retry remains explicit.
