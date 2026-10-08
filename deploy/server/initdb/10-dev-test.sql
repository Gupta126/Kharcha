-- Runs once when the Postgres volume is first created.
-- kharcha       : hosted stack (demo)
-- kharcha_dev   : dev runner used while Claude Code develops (make dev-api)
-- kharcha_test  : pytest (wiped by tests)
CREATE DATABASE kharcha_dev OWNER kharcha;
CREATE DATABASE kharcha_test OWNER kharcha;
