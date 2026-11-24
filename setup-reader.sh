#!/bin/sh
set -eu

reader_password=${ACADEMY_MYSQL_READER_PASSWORD:-user}

case "$reader_password" in
    user) ;;
    *[!0-9a-fA-F]*)
        echo 'ACADEMY_MYSQL_READER_PASSWORD must be user or hexadecimal.' >&2
        exit 1
        ;;
esac

MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --protocol=socket -u root <<SQL
CREATE USER IF NOT EXISTS 'academy_reader'@'%' IDENTIFIED BY '$reader_password';
ALTER USER 'academy_reader'@'%' IDENTIFIED BY '$reader_password';
GRANT SELECT ON math_academy.* TO 'academy_reader'@'%';
SQL
